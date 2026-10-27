"""Download historical sources with immutable receipts, outside reference data."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.versioned_acquisition import fetch_versioned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["power", "inpe"], required=True)
    parser.add_argument("--output", type=Path, default=ROOT / ".venv/acquisition-receipts")
    parser.add_argument("--grid-id")
    parser.add_argument("--year", type=int)
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--expected-raw-sha256")
    parser.add_argument("--expected-processed-sha256")
    args = parser.parse_args()
    _, record = fetch_versioned(args.provider, args.output, grid_id=args.grid_id, year=args.year,
        start=args.start, end=args.end, expected_raw_sha256=args.expected_raw_sha256,
        expected_processed_sha256=args.expected_processed_sha256)
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
