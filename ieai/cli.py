import argparse
import json
import sys
from .config import Protocol
from .data import Dataset, DataError


def main(argv=None):
    parser = argparse.ArgumentParser(description="IEAI daily master's research engine")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--dataset", required=True)
    run.add_argument("--protocol", default="config/protocol.json")
    run.add_argument("--output", required=True)
    run.add_argument("--allow-synthetic", action="store_true", help="Software tests only, never empirical evidence")
    validate = commands.add_parser("validate")
    validate.add_argument("--dataset", required=True)
    validate.add_argument("--protocol", default="config/protocol.json")
    fetch = commands.add_parser("fetch-market")
    fetch.add_argument("--symbols", default="THYAO.IS,BIMAS.IS,TUPRS.IS,ASELS.IS,EREGL.IS")
    fetch.add_argument("--start", default="2021-01-01")
    fetch.add_argument("--end", default="2025-12-31")
    fetch.add_argument("--output", required=True)
    official = commands.add_parser("fetch-official", help="Archive public BIST series and membership change candidates")
    official.add_argument("--start", default="2021-10-01")
    official.add_argument("--end", default="2025-12-31")
    official.add_argument("--catalog", default="config/official_sources.json")
    official.add_argument("--output", required=True)
    intake = commands.add_parser("compile-intake", help="Compile reviewed source ledgers without inventing missing fields")
    intake.add_argument("--source", required=True)
    intake.add_argument("--output", required=True)
    audit = commands.add_parser("audit-coverage", help="Audit actual input coverage and declared source-review evidence")
    audit.add_argument("--dataset", required=True)
    audit.add_argument("--protocol", default="config/protocol.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch-official":
            from pathlib import Path
            from .official import acquire_official
            report = acquire_official(args.start, args.end, args.output,
                json.loads(Path(args.catalog).read_text(encoding="utf-8")), progress=lambda s: print(s, flush=True))
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["total_return_benchmarks_aligned"] else 2
        if args.command == "compile-intake":
            from .intake import compile_intake
            report = compile_intake(args.source, args.output)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if not report["gaps"] else 2
        if args.command == "fetch-market":
            from .yahoo import fetch_snapshot
            report = fetch_snapshot(args.symbols.split(","), args.start, args.end, args.output)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["sha256"] else 2
        from pathlib import Path
        protocol = Protocol.from_json(Path(args.protocol).read_text(encoding="utf-8"))
        if args.command == "audit-coverage":
            from .coverage import audit_coverage
            report = audit_coverage(args.dataset, protocol)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["coverage_complete_for_declared_scope"] else 2
        data = Dataset.from_directory(args.dataset)
        data.require_research_inputs(protocol.screening_profile)
        if args.command == "validate":
            print(json.dumps({"status": "schema_valid_not_source_authenticated", "dataset_id": data.manifest["dataset_id"],
                              "dataset_kind": data.manifest["dataset_kind"], "input_sha256": data.hashes}, indent=2))
            return 0
        from .experiment import run_experiment, write_results
        result = run_experiment(data, protocol, allow_synthetic=args.allow_synthetic,
                                progress=lambda stage: print(stage, flush=True))
        write_results(result, args.output)
        print(result["report"]["research_claim_status"])
        return 0
    except (DataError, ValueError, OSError, ImportError) as exc:
        print(f"Research run blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
