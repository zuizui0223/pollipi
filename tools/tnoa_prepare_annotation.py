#!/usr/bin/env python3
"""Prepare or validate blinded TNOA field-truth annotation CSVs."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pollipi_analysis.tnoa_annotation_sheet import (
    ANNOTATION_COLUMNS,
    build_blank_annotation_rows,
    parse_completed_annotation,
)


def prepare(
    source: Path,
    output: Path,
    *,
    site_id: str = "",
    flower_id: str = "",
    plant_species: str = "",
    focal_scene_id: str = "",
    recording_block: str = "",
    reference_source_id: str = "",
) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    prepared = build_blank_annotation_rows(rows)
    for row in prepared:
        if site_id:
            row["site_id"] = site_id
        if flower_id:
            row["flower_id"] = flower_id
        if plant_species:
            row["plant_species"] = plant_species
        if focal_scene_id:
            row["focal_scene_id"] = focal_scene_id
        if recording_block:
            row["recording_block"] = recording_block
        if reference_source_id:
            row["reference_source_id"] = reference_source_id
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANNOTATION_COLUMNS)
        writer.writeheader()
        writer.writerows(prepared)
    print(f"Prepared {len(prepared)} blinded annotation rows: {output}")


def validate(source: Path) -> None:
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    records = [parse_completed_annotation(row) for row in rows]
    groups = {record.split_group for record in records}
    unresolved = sum(not record.resolved_biological_truth for record in records)
    print(
        f"Validated {len(records)} independent-truth rows across {len(groups)} split groups; "
        f"biological truth unresolved={unresolved}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("source_tnoa_csv", type=Path)
    p_prepare.add_argument("output_csv", type=Path)
    p_prepare.add_argument("--site-id", default="")
    p_prepare.add_argument("--flower-id", default="")
    p_prepare.add_argument("--plant-species", default="")
    p_prepare.add_argument("--focal-scene-id", default="")
    p_prepare.add_argument("--recording-block", default="")
    p_prepare.add_argument("--reference-source-id", default="")
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("annotation_csv", type=Path)
    args = ap.parse_args()
    if args.command == "prepare":
        prepare(
            args.source_tnoa_csv,
            args.output_csv,
            site_id=args.site_id,
            flower_id=args.flower_id,
            plant_species=args.plant_species,
            focal_scene_id=args.focal_scene_id,
            recording_block=args.recording_block,
            reference_source_id=args.reference_source_id,
        )
    else:
        validate(args.annotation_csv)


if __name__ == "__main__":
    main()
