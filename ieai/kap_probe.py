"""One-request, unauthenticated DEVELOPMENT environment probe for MKK KAP VYK.

Deliberately no production support, secrets, pagination, bulk collection, or
conversion to empirical research inputs. Run only with authorized access.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEV_URL = "https://apigwdev.mkk.com.tr/api/vyk/members"
MAX_BYTES = 12 * 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never follow redirects to unknown hosts, or send credentials onward.
        return None


def probe_members(output_directory, *, opener=None, max_bytes=MAX_BYTES):
    """Issue at most one read-only request; no retry, no token, no auth header."""
    if max_bytes < 1 or max_bytes > MAX_BYTES:
        raise ValueError("Invalid response byte limit")
    output = Path(output_directory)
    if output.exists():
        raise ValueError("Output directory already exists; choose a new path")
    request = Request(DEV_URL, headers={
        "Accept": "application/json",
        "User-Agent": "IEAI-Sharia-Radar academic development connectivity check/0.1",
    }, method="GET")
    client = opener if opener is not None else build_opener(NoRedirects())
    try:
        with client.open(request, timeout=20) as response:
            # A custom opener is tested independently; real redirects are blocked.
            if response.geturl() != DEV_URL:
                raise ValueError("Unexpected response URL")
            if response.status != 200:
                raise ValueError("Unsuccessful development endpoint status")
            content_type = response.headers.get("Content-Type", "").lower()
            if "json" not in content_type:
                raise ValueError("Expected JSON; no research data accepted")
            raw = response.read(max_bytes + 1)
    except HTTPError as exc:
        # Do not echo error bodies, tokens, raw headers or redirects to logs.
        raise ValueError(f"Development endpoint returned HTTP {exc.code}") from None
    except URLError:
        raise ValueError("Development endpoint unreachable") from None
    if len(raw) > max_bytes:
        raise ValueError("Development response exceeds maximum size")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Development response is not valid JSON") from None
    if not isinstance(payload, (list, dict)):
        raise ValueError("Development response has unexpected top-level shape")
    digest = sha256(raw).hexdigest()
    manifest = {
        "status": "DEV_CONNECTIVITY_ONLY",
        "source_environment": "development",
        "source_url": DEV_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "response_sha256": digest,
        "response_bytes": len(raw),
        "research_dataset_complete": False,
        "source_review_status": "unreviewed",
        "allowed_for_empirical_research": False,
        "note": "Development data; not historical or certified production KAP data",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "members-dev.json").write_bytes(raw)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="KAP VYK one-request development-only probe")
    parser.add_argument("--output", required=True, help="NEW local output directory (do not commit)")
    args = parser.parse_args(argv)
    try:
        report = probe_members(args.output)
    except (ValueError, OSError) as exc:
        print(f"Connectivity probe not successful: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
