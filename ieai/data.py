"""Explicit input contracts. Missing observations are never silently forward filled."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import numpy as np
import pandas as pd


class DataError(ValueError):
    pass


SCHEMAS = {
    "prices.csv": ["date", "symbol", "close", "total_return_close", "volume",
                   "value_traded_try", "is_tradable"],
    "eligibility.csv": ["symbol", "available_at", "effective_from", "effective_to",
                        "eligible", "rule_set", "source_url"],
    "shares.csv": ["symbol", "available_at", "shares_outstanding", "source_url"],
    "financials.csv": ["symbol", "available_at", "period_end", "total_assets",
                       "interest_bearing_debt", "interest_bearing_assets", "total_revenue",
                       "noncompliant_revenue", "activity_pass", "other_criteria_pass", "source_url"],
    "benchmarks.csv": ["date", "benchmark", "level", "kind", "currency"],
    "factors.csv": ["date", "market_excess", "smb", "hml", "rmw", "cma", "rf"],
    "cpi.csv": ["date", "cpi"],
}
REQUIRED = {"prices.csv", "eligibility.csv", "shares.csv", "manifest.json"}
DATE_FIELDS = {"date", "available_at", "effective_from", "effective_to", "period_end"}
BOOL_FIELDS = {"eligible", "is_tradable", "activity_pass", "other_criteria_pass"}
STRING_FIELDS = {"symbol", "rule_set", "source_url", "benchmark", "kind", "currency"}


def _bool(series, field):
    mapping = {"true": True, "false": False, "1": True, "0": False}
    values = series.astype(str).str.lower().str.strip().map(mapping)
    if values.isna().any():
        raise DataError(f"{field} must contain true/false or 1/0")
    return values.astype(bool)


def validate_frame(name, frame):
    absent = set(SCHEMAS[name]) - set(frame)
    if absent:
        raise DataError(f"{name}: missing columns {sorted(absent)}")
    if frame.empty:
        raise DataError(f"{name}: no observations")
    frame = frame.copy()
    for field in SCHEMAS[name]:
        if field in DATE_FIELDS:
            frame[field] = pd.to_datetime(frame[field], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
            if frame[field].isna().any():
                raise DataError(f"{name}: invalid {field}")
        elif field in BOOL_FIELDS:
            frame[field] = _bool(frame[field], field)
        elif field in STRING_FIELDS:
            if frame[field].isna().any() or frame[field].astype(str).str.strip().eq("").any():
                raise DataError(f"{name}: empty {field}")
            frame[field] = frame[field].astype(str).str.strip()
            if field == "source_url" and not frame[field].str.match(r"^https?://").all():
                raise DataError(f"{name}: source_url must identify an HTTP(S) source")
        else:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
            if not np.isfinite(frame[field]).all():
                raise DataError(f"{name}: nonfinite {field}")
    keys = {
        "prices.csv": ["date", "symbol"], "eligibility.csv": ["symbol", "available_at", "effective_from"],
        "shares.csv": ["symbol", "available_at"], "financials.csv": ["symbol", "available_at"],
        "benchmarks.csv": ["date", "benchmark"], "factors.csv": ["date"], "cpi.csv": ["date"],
    }[name]
    if frame.duplicated(keys).any():
        raise DataError(f"{name}: ambiguous duplicate {keys}")
    if name == "prices.csv":
        if (frame[["close", "total_return_close"]] <= 0).any().any():
            raise DataError("Prices must be positive; explicit terminal/delisting treatment is required")
        if (frame[["volume", "value_traded_try"]] < 0).any().any():
            raise DataError("Negative volume/value")
        if frame.date.max() > pd.Timestamp.now(tz="UTC").tz_localize(None).normalize():
            raise DataError("Future price observations are prohibited")
    if name == "eligibility.csv" and (frame.effective_to < frame.effective_from).any():
        raise DataError("Invalid eligibility interval")
    if name == "shares.csv" and (frame.shares_outstanding <= 0).any():
        raise DataError("Shares outstanding must be positive")
    if name == "financials.csv":
        if (frame.period_end > frame.available_at).any():
            raise DataError("Financial report availability precedes its period end")
        numeric = [c for c in SCHEMAS[name] if c not in DATE_FIELDS | BOOL_FIELDS | STRING_FIELDS]
        if (frame[numeric] < 0).any().any() or (frame.total_assets <= 0).any() or (frame.total_revenue <= 0).any():
            raise DataError("Financial denominators must be positive and amounts nonnegative")
    if name == "benchmarks.csv":
        if (frame.level <= 0).any() or not frame.kind.isin(["price", "total_return"]).all():
            raise DataError("Invalid benchmark level/kind")
        if not frame.currency.eq("TRY").all():
            raise DataError("Benchmarks must use the same TRY currency as the portfolio")
        if frame.groupby("benchmark").kind.nunique().max() != 1:
            raise DataError("Benchmark kind changes within a series")
    if name == "cpi.csv" and (frame.cpi <= 0).any():
        raise DataError("CPI must be positive")
    return frame.sort_values(keys).reset_index(drop=True)


@dataclass
class Dataset:
    frames: dict
    manifest: dict
    hashes: dict

    @classmethod
    def from_bytes(cls, files):
        missing = REQUIRED - set(files)
        if missing:
            raise DataError(f"Missing required input files: {sorted(missing)}")
        try:
            manifest = json.loads(files["manifest.json"].decode("utf-8-sig"))
        except (ValueError, UnicodeError) as exc:
            raise DataError("Invalid manifest.json") from exc
        if not isinstance(manifest, dict):
            raise DataError("manifest.json must be an object")
        if manifest.get("dataset_kind") not in {"real", "synthetic"}:
            raise DataError("manifest.dataset_kind must explicitly be real or synthetic")
        if manifest.get("audit_status") not in {"reviewed", "unreviewed"}:
            raise DataError("manifest.audit_status must be reviewed or unreviewed")
        for field in ("dataset_id", "currency", "universe", "sources", "price_convention"):
            if not manifest.get(field):
                raise DataError(f"Missing provenance field: {field}")
        if manifest["currency"] != "TRY":
            raise DataError("Only a consistently denominated TRY dataset is supported")
        if not isinstance(manifest["sources"], list):
            raise DataError("manifest.sources must be a list")
        frames, hashes = {}, {}
        for name, raw in files.items():
            if name not in SCHEMAS and name != "manifest.json":
                continue
            if len(raw) > 40 * 1024 * 1024:
                raise DataError("Input size limit exceeded")
            hashes[name] = sha256(raw).hexdigest()
            if name in SCHEMAS:
                try:
                    parsed = pd.read_csv(BytesIO(raw))
                    if parsed.empty and name not in REQUIRED:
                        continue
                    frames[name] = validate_frame(name, parsed)
                except (pd.errors.ParserError, UnicodeError) as exc:
                    raise DataError(f"Unreadable {name}") from exc
        for name, expected in manifest.get("sha256", {}).items():
            if hashes.get(name) != expected:
                raise DataError(f"Hash mismatch: {name}")
        return cls(frames, manifest, hashes)

    @classmethod
    def from_directory(cls, path):
        path = Path(path)
        files = {p.name: p.read_bytes() for p in path.iterdir()
                 if p.is_file() and p.name in set(SCHEMAS) | {"manifest.json"}}
        return cls.from_bytes(files)

    @classmethod
    def from_zip(cls, raw):
        if len(raw) > 40 * 1024 * 1024:
            raise DataError("ZIP upload exceeds 40 MiB")
        try:
            archive = ZipFile(BytesIO(raw))
        except BadZipFile as exc:
            raise DataError("Invalid ZIP archive") from exc
        with archive:
            entries = archive.infolist()
            if len(entries) > 20 or sum(e.file_size for e in entries) > 40 * 1024 * 1024:
                raise DataError("Archive expansion limit exceeded")
            if len({e.filename for e in entries}) != len(entries):
                raise DataError("Duplicate archive entries")
            if any("/" in e.filename or "\\" in e.filename for e in entries):
                raise DataError("ZIP files must be at the archive root; paths are prohibited")
            return cls.from_bytes({e.filename: archive.read(e) for e in entries})

    def get(self, name):
        return self.frames.get(name, pd.DataFrame())

    def require_research_inputs(self, profile):
        if profile == "research_30" and self.get("financials.csv").empty:
            raise DataError("research_30 requires historical financials.csv; eligibility is not inferred from prices")
        if self.manifest["dataset_kind"] == "real":
            for name in self.frames:
                if not any(isinstance(x, dict) and x.get("file") == name
                           and str(x.get("url", "")).startswith(("https://", "http://"))
                           and x.get("provider") and x.get("retrieved_at") for x in self.manifest["sources"]):
                    raise DataError(f"Missing per-file provenance for {name}")
