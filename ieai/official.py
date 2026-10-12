"""Low-volume, archived acquisition from advertised BIST/KAP public sources.

An index change list is not a constituent snapshot. Extracted change candidates
are never promoted to eligibility or marked reviewed by the downloader.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
import gzip
import json
from pathlib import Path
import re
import struct
import time
import unicodedata
from urllib.parse import urlencode, urlparse, urljoin
from urllib.request import Request, HTTPRedirectHandler, build_opener
from zipfile import ZipFile, ZIP_DEFLATED
import numpy as np
import pandas as pd
from .data import DataError, validate_frame


HOSTS = {"borsaistanbul.com", "www.borsaistanbul.com", "kap.org.tr", "www.kap.org.tr"}
MAX_RESPONSE = 16 * 1024 * 1024
INDEX_SPECS = {
    "XK100": ("BIST_PARTICIPATION_100_PRICE", "price"),
    "XK100_CFCNTLTL": ("BIST_PARTICIPATION_100", "total_return"),
    "XU100": ("BIST_100_PRICE", "price"),
    "XU100_CFNNTLTL": ("BIST_100", "total_return"),
}
ARCHIVE_URL = "https://www.borsaistanbul.com/endeksler/endeks-duyurulari"


def approved_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port:
        raise DataError("Only explicit public HTTPS sources on BIST/KAP are allowed")
    return url


class _PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        approved_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SourceArchive:
    def __init__(self, directory, delay=1.0):
        self.directory = Path(directory)
        (self.directory / "raw").mkdir(parents=True, exist_ok=True)
        self.delay = max(0.0, float(delay))
        self.last_request = 0.0
        self.records = []
        self.opener = build_opener(_PublicRedirect())

    def fetch(self, source_id, url):
        approved_url(url)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", source_id):
            raise DataError("Unsafe source identifier")
        remaining = self.delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)
        self.last_request = time.monotonic()
        request = Request(url, headers={"User-Agent": "IEAI academic research: low-volume public-source verification",
                                        "Accept-Encoding": "identity"})
        record = {"source_id": source_id, "url": url,
                  "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            with self.opener.open(request, timeout=30) as response:
                approved_url(response.url)
                raw = response.read(MAX_RESPONSE + 1)
                record.update(final_url=response.url, content_type=response.headers.get("Content-Type", ""),
                              http_status=response.status)
            if len(raw) > MAX_RESPONSE:
                raise DataError("Public source response exceeds size limit")
            record.update(sha256=sha256(raw).hexdigest(), byte_count=len(raw), status="downloaded",
                          raw_file=f"raw/{source_id}.bin")
            (self.directory / record["raw_file"]).write_bytes(raw)
            self.records.append(record)
            # Hash and preserve the bytes received, separately from decoded derivatives.
            if raw[:2] == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=BytesIO(raw)) as archive:
                    decoded = archive.read(MAX_RESPONSE + 1)
                if len(decoded) > MAX_RESPONSE:
                    raise DataError("Expanded source exceeds size limit")
                return decoded
            return raw
        except Exception as exc:
            if record not in self.records:
                record.update(status="failed", error=str(exc)[:500])
                self.records.append(record)
            raise


def index_url(code):
    if code not in {*INDEX_SPECS, "BISTTLREF"}:
        raise DataError("Unrecognized, unverified index code")
    return "https://www.borsaistanbul.com/graphic.php?" + urlencode({"veriTuru": "endeks-graphic", "indexCode": code})


def parse_index(payload, code):
    if not isinstance(payload, dict) or payload.get("status") != "success" or not isinstance(payload.get("data"), list):
        raise DataError("Official index response is not a successful data array")
    frame = pd.DataFrame(payload["data"])
    if frame.empty or not {"indexName", "clval", "hisTs"} <= set(frame):
        raise DataError("Official index response has no closing observations")
    if not frame.indexName.eq(code).all():
        raise DataError("Returned index identity does not match the requested code")
    dates = pd.to_datetime(frame.hisTs, format="%Y-%m-%d", errors="coerce")
    levels = pd.to_numeric(frame.clval, errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or not np.isfinite(levels).all() or (levels <= 0).any():
        raise DataError("Invalid or ambiguous official index observations")
    if dates.max() > pd.Timestamp.now(tz="UTC").tz_localize(None).normalize():
        raise DataError("Future official index observations")
    return pd.DataFrame({"date": dates, "level": levels}).sort_values("date").reset_index(drop=True)


def market_controls(market, cash_proxy, start, end):
    """Close-to-close TRY controls; TLREF is an explicitly disclosed RF proxy.

    BISTTLREF's dated observation capitalizes that date's rate through the next
    business date. Shift its equity-session ratio one interval to align the
    realized accrual with the equity return's END date. Verify against the BIST
    return calculator. Never divide an annual quote by 252 or fill absent data.
    """
    frame = market.sort_values("date").copy()
    proxy = cash_proxy.set_index("date").level.reindex(frame.date)
    frame["market_return"] = frame.level.pct_change(fill_method=None)
    frame["rf"] = proxy.to_numpy()
    frame["rf"] = frame.rf.pct_change(fill_method=None).shift(1)
    frame = frame[frame.date.between(pd.Timestamp(start), pd.Timestamp(end))]
    if frame.empty or not np.isfinite(frame[["market_return", "rf"]]).all().all():
        raise DataError("Incomplete market/RF proxy coverage, including preceding close")
    frame["market_excess"] = frame.market_return - frame.rf
    return frame[["date", "market_excess", "rf"]].reset_index(drop=True)


def cash_reference_checks(market, cash_proxy, client):
    checks = []
    for start, end in [("2021-09-30", "2021-10-01"), ("2021-10-01", "2021-10-04")]:
        url = "https://www.borsaistanbul.com/bist-tlrefk.php?" + urlencode({"op": "calculateType1", "type": "tlref",
                    "starting_date": start, "ending_date": end})
        response = json.loads(client.fetch("cash_reference_check_" + end.replace("-", ""), url))
        if response.get("status") != "success" or "periodReturn" not in response.get("data", {}):
            raise DataError("Official cash-reference calendar verification unavailable")
        computed = market_controls(market, cash_proxy, end, end).rf.iloc[0]
        expected = float(response["data"]["periodReturn"]) / 100
        if not np.isfinite(expected) or abs(computed - expected) > 5.1e-7:
            raise DataError("Cash-reference date convention disagrees with official BIST calculator")
        checks.append({"start": start, "end": end, "computed_decimal_return": float(computed),
                       "official_decimal_return": expected, "absolute_tolerance": 5.1e-7,
                       "period_days": response["data"]["periodDayCount"], "status": "matched"})
    return checks


class _Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.row = None; self.anchor = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = {"text": "", "links": []}
        if tag == "a" and self.row is not None:
            self.anchor = {"url": dict(attrs).get("href", ""), "title": ""}

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            if self.row is not None:
                self.row["links"].append(self.anchor)
            self.anchor = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row); self.row = None

    def handle_data(self, value):
        if self.row is not None:
            self.row["text"] += " " + value
        if self.anchor is not None:
            self.anchor["title"] += value


def participation_notices(html, start, end):
    parser = _Rows(); parser.feed(html)
    records = []
    for row in parser.rows:
        text = " ".join(row["text"].split())
        match = re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", text)
        links = [a for a in row["links"] if a["title"].strip()]
        if not match or not links or "katılım" not in text.casefold():
            continue
        date = datetime.strptime(match[0], "%d.%m.%Y").date().isoformat()
        if not start <= date <= end:
            continue
        url = urljoin(ARCHIVE_URL, links[0]["url"]).replace("http://", "https://", 1)
        approved_url(url)
        records.append({"published_date": date, "title": links[0]["title"].strip(),
                        "url": url, "category": text, "review_status": "unreviewed",
                        "scope_note": "May concern a different participation index; inspect the actual decision"})
    if not records:
        raise DataError("No participation notices found; source structure may have changed")
    return pd.DataFrame(records).drop_duplicates(["published_date", "url"]).sort_values(["published_date", "url"])


def unwrap_pdf(raw):
    if raw.startswith(b"%PDF-"):
        return raw
    # Some advertised KAP download responses contain a serialized Java byte[].
    # Decode this specific envelope, never deserialize executable Java objects.
    prefix = bytes.fromhex("aced0005757200025b42acf317f8060854e00200007870")
    if raw.startswith(prefix) and len(raw) >= 27:
        size = struct.unpack(">I", raw[23:27])[0]
        if size == len(raw) - 27 and raw[27:].startswith(b"%PDF-"):
            return raw[27:]
    raise DataError("Attachment is not a PDF or a recognized bounded byte-array envelope")


def pdf_text(raw):
    from pypdf import PdfReader
    document = PdfReader(BytesIO(unwrap_pdf(raw)), strict=True)
    if len(document.pages) > 100:
        raise DataError("Attachment page limit exceeded")
    text = "\n".join(page.extract_text(extraction_mode="layout") or "" for page in document.pages)
    if not text.strip():
        raise DataError("Image-only PDF requires reviewed OCR; no inferred text")
    return text


def _ascii(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.replace("ı", "i")) if not unicodedata.combining(c)).upper()


def period_matches(text, start, end):
    normalized = re.sub(r"[^A-Z0-9]", "", _ascii(text))
    for value in (start, end):
        date = pd.Timestamp(value)
        variants = [date.strftime("%d%m%Y"), date.strftime("%B").upper() + str(date.day) + str(date.year)]
        if not any(v in normalized for v in variants):
            return False
    return True


def change_candidates(text, source, sessions):
    if not period_matches(text, source["period_start"], source["period_end"]):
        raise DataError("Attachment period mismatch: possibly a mutable historical link; quarantined")
    lines = text.splitlines(); active = False; boundaries = None; inferred_columns = False; entries = []
    effective = sessions[sessions >= pd.Timestamp(source["period_start"])].min()
    if pd.isna(effective):
        raise DataError("No official equity session for the change effective date")
    for line in lines:
        upper = _ascii(line)
        if re.search(r"BIST (?:KATILIM|PARTICIPATION) 100 (?:ENDEKSI|INDEX)", upper):
            active = True; boundaries = None; inferred_columns = False; continue
        if active and re.search(r"BIST (?:KATILIM|PARTICIPATION) (?:30|50|TUM|ALL|SUSTAINABILITY|DIVIDEND)", upper):
            active = False
        if not active:
            continue
        included = re.search(r"STOCKS TO BE INCLUDED|ALINACAK PAYLAR", upper)
        excluded = re.search(r"STOCKS TO BE EXCLUDED|CIKARILACAK PAYLAR", upper)
        reserve = re.search(r"SUBSTITUTE STOCKS|YEDEK PAYLAR", upper)
        if included and excluded and reserve:
            boundaries = (excluded.start() - 3, reserve.start() - 3); continue
        if boundaries is None:
            continue
        matches = list(re.finditer(r"\b(\d{1,3})\s+([A-Z][A-Z0-9]{2,5})\b", upper))
        # PDF headers are sometimes shifted relative to the actual data columns.
        # Infer separators from an observed three-column data row, then verify
        # contiguous ordinals. Headers alone must not classify shifted removals.
        if len(matches) == 3 and not inferred_columns:
            starts = [m.start() for m in matches]
            if min(np.diff(starts)) < 12:
                raise DataError("Ambiguous change-table column layout")
            boundaries = ((starts[0]+starts[1])/2, (starts[1]+starts[2])/2)
            inferred_columns = True
        for match in matches:
            position = match.start()
            kind = "add" if position < boundaries[0] else "remove" if position < boundaries[1] else "reserve"
            entries.append({"source_id": source["source_id"], "index_code": "XK100", "event_kind": kind,
                            "ordinal": int(match[1]), "symbol": match[2] + ".IS",
                            "published_at": source["published_date"],
                            "available_at": (pd.Timestamp(source["published_date"]) + pd.Timedelta(days=1)).date().isoformat(),
                            "effective_from": effective.date().isoformat(),
                            "period_end": source["period_end"], "source_url": source["announcement_url"],
                            "review_status": "unreviewed"})
    frame = pd.DataFrame(entries)
    if frame.empty:
        raise DataError("No safely recognized Participation 100 change table")
    if frame.duplicated(["event_kind", "ordinal"]).any():
        raise DataError("Ambiguous duplicate change-table ordinals")
    for kind, group in frame.groupby("event_kind"):
        if sorted(group.ordinal) != list(range(1, len(group) + 1)):
            raise DataError(f"Incomplete {kind} change-table sequence")
    if len(frame[frame.event_kind == "add"]) != len(frame[frame.event_kind == "remove"]):
        raise DataError("Unequal periodic additions/removals require source review")
    return frame


def acquire_official(start, end, directory, catalog, client=None, progress=None):
    if not "2021-10-01" <= start < end <= pd.Timestamp.now(tz="UTC").date().isoformat():
        raise DataError("Supply an ordered, past Participation 100 study period")
    folder = Path(directory)
    if folder.exists() and any(p.is_file() for p in folder.rglob("*")):
        raise DataError("Use an empty acquisition directory so stale outputs cannot survive a failed download")
    folder.mkdir(parents=True, exist_ok=True)
    client = client or SourceArchive(folder)
    series, benchmark_frames, failures, docs, candidates = {}, [], [], [], []
    controls = pd.DataFrame(); cash_checks = []
    def log(message):
        if progress:
            progress(message)
    for code in [*INDEX_SPECS, "BISTTLREF"]:
        try:
            log("fetching_official_index:" + code)
            series[code] = parse_index(json.loads(client.fetch(code, index_url(code))), code)
            if code in INDEX_SPECS:
                name, kind = INDEX_SPECS[code]
                frame = series[code][series[code].date.between(start, end)].copy()
                frame["benchmark"], frame["kind"], frame["currency"] = name, kind, "TRY"
                benchmark_frames.append(frame[["date", "benchmark", "level", "kind", "currency"]])
        except Exception as exc:
            failures.append({"source_id": code, "error": str(exc)[:500]})
    if benchmark_frames:
        benchmarks = validate_frame("benchmarks.csv", pd.concat(benchmark_frames, ignore_index=True))
        benchmarks.to_csv(folder / "benchmarks.csv", index=False, date_format="%Y-%m-%d")
    else:
        benchmarks = pd.DataFrame()
    sessions = pd.DatetimeIndex(series.get("XK100", pd.DataFrame({"date": []})).date)
    sessions = sessions[(sessions >= pd.Timestamp(start)) & (sessions <= pd.Timestamp(end))]
    if {"XU100_CFNNTLTL", "BISTTLREF"} <= set(series):
        try:
            controls = market_controls(series["XU100_CFNNTLTL"], series["BISTTLREF"], start, end)
            cash_checks = cash_reference_checks(series["XU100_CFNNTLTL"], series["BISTTLREF"], client)
            controls.to_csv(folder / "market_factors.csv", index=False, date_format="%Y-%m-%d")
        except Exception as exc:
            controls = pd.DataFrame()
            failures.append({"source_id": "market_factors", "error": str(exc)[:500]})
    else:
        controls = pd.DataFrame()
    try:
        notices = participation_notices(client.fetch("index_notices", ARCHIVE_URL).decode("utf-8"), start, end)
        notices.to_csv(folder / "membership_notice_inventory.csv", index=False)
    except Exception as exc:
        failures.append({"source_id": "index_notices", "error": str(exc)[:500]})
        notices = pd.DataFrame()
    for source in catalog.get("membership_documents", []):
        record = dict(source)
        try:
            log("archiving_membership_document:" + source["source_id"])
            raw = client.fetch(source["source_id"], source["url"])
            text = pdf_text(raw)
            if len(text) > 500000:
                raise DataError("Extracted attachment text limit exceeded")
            (folder / (source["source_id"] + ".txt")).write_text(text, encoding="utf-8")
            frame = change_candidates(text, source, sessions)
            candidates.append(frame)
            record.update(status="change_candidates_require_review", candidate_rows=len(frame),
                          period_verified=True, decoded_pdf_sha256=sha256(unwrap_pdf(raw)).hexdigest())
        except Exception as exc:
            record.update(status="quarantined", error=str(exc)[:500])
        docs.append(record)
    if candidates:
        pd.concat(candidates, ignore_index=True).to_csv(folder / "membership_change_candidates.csv", index=False)
    summaries = {}
    for code, frame in series.items():
        window = frame[frame.date.between(start, end)]
        summaries[code] = {"rows": len(window), "first": None if window.empty else window.date.min().date().isoformat(),
                           "last": None if window.empty else window.date.max().date().isoformat()}
    benchmark_ready = len(sessions) > 0 and all(code in series and
        set(series[code].loc[series[code].date.between(start, end), "date"]) == set(sessions)
        for code in INDEX_SPECS)
    now = datetime.now(timezone.utc).isoformat()
    generated = ["benchmarks.csv", "market_factors.csv", "membership_notice_inventory.csv", "membership_change_candidates.csv"]
    report = {
        "status": "REAL_OFFICIAL_SOURCES_ACQUIRED_RESEARCH_DATASET_INCOMPLETE", "retrieved_at": now,
        "study_start": start, "study_end": end, "index_coverage": summaries,
        "total_return_benchmarks_aligned": benchmark_ready,
        "market_controls": {"rows": len(controls), "market": "XU100_CFNNTLTL", "rf_proxy": "BISTTLREF",
                            "frequency": "equity_close_to_close", "units": "decimal_returns", "currency": "TRY",
                            "date_convention": "BISTTLREF dated accrual shifted one equity interval to realized end date",
                            "independent_calendar_spot_checks": cash_checks,
                            "status": "acquired_proxy_requires_methodological_review" if len(controls) else "missing"},
        "membership_notice_count": len(notices), "membership_documents": docs,
        "blocking_gaps": ["Reviewed complete initial XK100 membership snapshot with publication date",
                          "Reviewed exceptional changes, renames, exclusions and continuity coverage",
                          "Historical financials, KAFIF/activity attestations and original publication timestamps",
                          "Historical issued shares and effective capital events compatible with price/volume units",
                          "Turkish SMB/HML/RMW/CMA or audited broad-market inputs to construct them"],
        "research_dataset_complete": False, "research_hypotheses_confirmed": False,
        "sha256": {name: sha256((folder/name).read_bytes()).hexdigest() for name in generated if (folder/name).exists()},
        "sources": client.records, "retrieval_failures": failures,
        "notes": ["XK100 and XKTUM are different indices; no substitution",
                  "Only matching historical document periods yield change candidates",
                  "Reserve stocks are not actual members; no opening list is invented",
                  "BISTTLREF is an econometric cash-rate proxy, not a portfolio allocation or a guarantee",
                  "Market-only controls do not supply or certify local FF3/FF5 factors",
                  "Public KAP mass-data requests require the subscribed dissemination service; no mass corporate crawl",
                  "Availability uses publication day plus one conservatively; original timestamps require review"]}
    (folder / "acquisition_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix != ".zip" and p.name != "SHA256SUMS.txt")
    sums = "".join(f"{sha256(p.read_bytes()).hexdigest()}  {p.relative_to(folder).as_posix()}\n" for p in files)
    (folder / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    with ZipFile(folder / "official-source-package.zip", "w", ZIP_DEFLATED) as archive:
        for path in [*files, folder / "SHA256SUMS.txt"]:
            archive.write(path, path.relative_to(folder).as_posix())
    return report
