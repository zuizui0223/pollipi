#!/usr/bin/env python3
"""Validate a V3 fixed-interval field shadow collection before any scoring."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pollipi_analysis.field_v3_shadow import validate_collection


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("frame_ledger", type=Path)
    p.add_argument("--require-truth-ready", action="store_true")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = validate_collection(
        args.manifest,
        args.frame_ledger,
        require_truth_ready=args.require_truth_ready,
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if result["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
