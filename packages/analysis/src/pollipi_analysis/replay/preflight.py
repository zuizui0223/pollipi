"""Fail-closed preflight and provenance freeze for PolliPi field-validation inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from pollipi_analysis.policy.three_stage import ThreeStageConfig
from pollipi_analysis.replay.compare import load_visits, read_run_start
from pollipi_analysis.schemas.states import ALL_DECISION_STATES

SCHEMA = "pollipi-field-input-preflight-v1"
INDEPENDENT_TRUTH_SOURCES = frozenset({
    "continuous_reference_video",
    "high_frequency_reference_video",
    "controlled_event_schedule",
    "independent_sensor",
})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.strip())


def _resolve(base: Path, raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else (base / path).resolve()


def _optional_float(row: dict[str, str], key: str, default: float) -> float:
    raw = (row.get(key) or "").strip()
    return float(raw) if raw else default


@dataclass(frozen=True)
class RunInputAudit:
    run_id: str
    probe_log: str
    probe_sha256: str
    visits_csv: str
    visits_sha256: str
    probe_rows: int
    visit_events: int
    duration_sec: float
    median_probe_gap_sec: Optional[float]
    max_probe_gap_sec: Optional[float]
    low_interval_sec: float
    mid_interval_sec: float
    high_interval_sec: float
    warnings: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "probe_log": self.probe_log,
            "probe_sha256": self.probe_sha256,
            "visits_csv": self.visits_csv,
            "visits_sha256": self.visits_sha256,
            "probe_rows": self.probe_rows,
            "visit_events": self.visit_events,
            "duration_sec": round(self.duration_sec, 6),
            "median_probe_gap_sec": (
                round(self.median_probe_gap_sec, 6)
                if self.median_probe_gap_sec is not None
                else None
            ),
            "max_probe_gap_sec": (
                round(self.max_probe_gap_sec, 6)
                if self.max_probe_gap_sec is not None
                else None
            ),
            "low_interval_sec": self.low_interval_sec,
            "mid_interval_sec": self.mid_interval_sec,
            "high_interval_sec": self.high_interval_sec,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FieldInputPreflight:
    manifest: str
    manifest_sha256: str
    runs: tuple[RunInputAudit, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    input_fingerprint: str

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "ok": self.ok,
            "manifest": self.manifest,
            "manifest_sha256": self.manifest_sha256,
            "run_count": len(self.runs),
            "total_probe_rows": sum(run.probe_rows for run in self.runs),
            "total_visit_events": sum(run.visit_events for run in self.runs),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "input_fingerprint": self.input_fingerprint,
            "runs": [run.as_dict() for run in self.runs],
        }


def _audit_probe_log(path: Path, run_id: str) -> tuple[list[datetime], tuple[str, ...]]:
    warnings: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"probe_timestamp", "decision_state"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{run_id}: probe log missing required columns: "
                + ", ".join(sorted(missing))
            )
        stamps: list[datetime] = []
        awareness: set[bool] = set()
        for line_no, row in enumerate(reader, start=2):
            raw_ts = (row.get("probe_timestamp") or "").strip()
            state = (row.get("decision_state") or "").strip()
            if not raw_ts:
                raise ValueError(f"{run_id}: empty probe_timestamp at line {line_no}")
            try:
                stamp = _parse_time(raw_ts)
            except ValueError as exc:
                raise ValueError(
                    f"{run_id}: invalid probe_timestamp at line {line_no}: {raw_ts!r}"
                ) from exc
            if state not in ALL_DECISION_STATES:
                raise ValueError(
                    f"{run_id}: invalid decision_state at line {line_no}: {state!r}"
                )
            awareness.add(stamp.tzinfo is not None and stamp.utcoffset() is not None)
            stamps.append(stamp)

    if len(stamps) < 2:
        raise ValueError(f"{run_id}: at least two probe rows are required")
    if len(awareness) > 1:
        raise ValueError(f"{run_id}: probe timestamps mix timezone-aware and naive values")
    if awareness == {False}:
        warnings.append("probe timestamps are timezone-naive")

    for previous, current in zip(stamps, stamps[1:]):
        if current <= previous:
            relation = "duplicate" if current == previous else "out-of-order"
            raise ValueError(
                f"{run_id}: {relation} probe timestamps: "
                f"{previous.isoformat()} then {current.isoformat()}"
            )
    return stamps, tuple(warnings)


def _audit_visits(
    path: Path,
    run_id: str,
    run_start: datetime,
    duration_sec: float,
) -> tuple[list[tuple[float, float]], tuple[str, ...]]:
    warnings: list[str] = []
    event_ids: list[str] = []
    truth_sources: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"event_id", "start", "end", "truth_source"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{run_id}: visits CSV missing required columns: "
                + ", ".join(sorted(missing))
            )
        for line_no, row in enumerate(reader, start=2):
            event_id = (row.get("event_id") or "").strip()
            truth_source = (row.get("truth_source") or "").strip()
            if not event_id:
                raise ValueError(f"{run_id}: empty event_id at visits line {line_no}")
            if truth_source not in INDEPENDENT_TRUTH_SOURCES:
                allowed = ", ".join(sorted(INDEPENDENT_TRUTH_SOURCES))
                raise ValueError(
                    f"{run_id}: invalid/non-independent truth_source at visits line "
                    f"{line_no}: {truth_source!r}; allowed: {allowed}"
                )
            event_ids.append(event_id)
            truth_sources.append(truth_source)
    if len(set(event_ids)) != len(event_ids):
        raise ValueError(f"{run_id}: duplicate event_id in visits CSV")

    try:
        visits = load_visits(path, run_start)
    except Exception as exc:
        raise ValueError(f"{run_id}: cannot parse visits CSV: {exc}") from exc

    for index, (start, end) in enumerate(visits, start=1):
        if end < start:
            raise ValueError(
                f"{run_id}: visit {index} has end < start ({start} > {end})"
            )
        if start < 0 or end > duration_sec:
            raise ValueError(
                f"{run_id}: visit {index} [{start}, {end}] lies outside "
                f"the probe opportunity range [0, {duration_sec}]"
            )

    ordered = sorted(visits)
    overlap_count = 0
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] <= previous[1]:
            overlap_count += 1
    if overlap_count:
        warnings.append(
            f"{overlap_count} overlapping/concurrent visit-window pair(s); "
            "one still may capture more than one event"
        )
    if not visits:
        warnings.append("run contains zero annotated visit events")
    return visits, tuple(warnings)


def preflight_field_inputs(
    manifest_path: Union[str, Path],
    *,
    default_config: Optional[ThreeStageConfig] = None,
) -> FieldInputPreflight:
    """Validate and fingerprint all files used by the field-validation analysis."""
    manifest = Path(manifest_path).resolve()
    if not manifest.is_file():
        raise FileNotFoundError(manifest)

    default = default_config or ThreeStageConfig()
    base = manifest.parent
    errors: list[str] = []
    global_warnings: list[str] = []
    audits: list[RunInputAudit] = []
    seen: set[str] = set()

    with manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"run_id", "probe_log", "visits_csv"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            errors.append(
                "manifest missing required columns: " + ", ".join(sorted(missing))
            )
            rows: list[dict[str, str]] = []
        else:
            rows = list(reader)

    if not rows and not errors:
        errors.append("manifest contains no runs")

    for row_number, row in enumerate(rows, start=2):
        run_id = (row.get("run_id") or "").strip()
        if not run_id:
            errors.append(f"manifest row {row_number}: run_id is empty")
            continue
        if run_id in seen:
            errors.append(f"duplicate run_id in manifest: {run_id}")
            continue
        seen.add(run_id)

        probe_raw = (row.get("probe_log") or "").strip()
        visits_raw = (row.get("visits_csv") or "").strip()
        if not probe_raw or not visits_raw:
            errors.append(
                f"{run_id}: probe_log and visits_csv paths must both be non-empty"
            )
            continue
        probe_path = _resolve(base, probe_raw)
        visits_path = _resolve(base, visits_raw)
        if not probe_path.is_file():
            errors.append(f"{run_id}: probe log not found: {probe_path}")
            continue
        if not visits_path.is_file():
            errors.append(f"{run_id}: visits CSV not found: {visits_path}")
            continue

        try:
            low = _optional_float(row, "low_interval_sec", default.low_interval_sec)
            mid = _optional_float(row, "mid_interval_sec", default.mid_interval_sec)
            high = _optional_float(row, "high_interval_sec", default.high_interval_sec)
        except ValueError as exc:
            errors.append(f"{run_id}: invalid interval value: {exc}")
            continue
        if not (low > 0 and mid > 0 and high > 0):
            errors.append(f"{run_id}: all intervals must be > 0")
            continue
        if not (high <= mid < low):
            errors.append(
                f"{run_id}: expected high <= mid < low, got "
                f"high={high}, mid={mid}, low={low}"
            )
            continue

        try:
            stamps, probe_warnings = _audit_probe_log(probe_path, run_id)
            run_start = stamps[0]
            duration_sec = (stamps[-1] - stamps[0]).total_seconds()
            visits, visit_warnings = _audit_visits(
                visits_path, run_id, run_start, duration_sec
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue

        gaps = [
            (current - previous).total_seconds()
            for previous, current in zip(stamps, stamps[1:])
        ]
        median_gap = statistics.median(gaps) if gaps else None
        max_gap = max(gaps) if gaps else None
        run_warnings = list(probe_warnings) + list(visit_warnings)
        if median_gap and max_gap and max_gap > median_gap * 2.5:
            run_warnings.append(
                f"large probe gap detected: max={max_gap:.3f}s, "
                f"median={median_gap:.3f}s"
            )

        audits.append(
            RunInputAudit(
                run_id=run_id,
                probe_log=str(probe_path),
                probe_sha256=_sha256(probe_path),
                visits_csv=str(visits_path),
                visits_sha256=_sha256(visits_path),
                probe_rows=len(stamps),
                visit_events=len(visits),
                duration_sec=duration_sec,
                median_probe_gap_sec=median_gap,
                max_probe_gap_sec=max_gap,
                low_interval_sec=low,
                mid_interval_sec=mid,
                high_interval_sec=high,
                warnings=tuple(run_warnings),
            )
        )

    audits.sort(key=lambda run: run.run_id)
    total_visits = sum(run.visit_events for run in audits)
    if audits and total_visits == 0:
        errors.append("all validated runs contain zero annotated visits")

    for run in audits:
        for warning in run.warnings:
            global_warnings.append(f"{run.run_id}: {warning}")

    fingerprint_payload = {
        "schema": SCHEMA,
        "manifest_sha256": _sha256(manifest),
        "runs": [
            {
                "run_id": run.run_id,
                "probe_sha256": run.probe_sha256,
                "visits_sha256": run.visits_sha256,
                "probe_rows": run.probe_rows,
                "visit_events": run.visit_events,
                "low": run.low_interval_sec,
                "mid": run.mid_interval_sec,
                "high": run.high_interval_sec,
            }
            for run in audits
        ],
    }
    canonical = json.dumps(
        fingerprint_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    fingerprint = hashlib.sha256(canonical).hexdigest()

    return FieldInputPreflight(
        manifest=str(manifest),
        manifest_sha256=_sha256(manifest),
        runs=tuple(audits),
        errors=tuple(errors),
        warnings=tuple(global_warnings),
        input_fingerprint=fingerprint,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and fingerprint PolliPi field-validation inputs."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="write pollipi-field-input-preflight-v1 JSON",
    )
    args = parser.parse_args(argv)

    result = preflight_field_inputs(args.manifest)
    payload = result.as_dict()
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(
            f"preflight ok={result.ok} runs={len(result.runs)} "
            f"visits={sum(run.visit_events for run in result.runs)}"
        )
        print(f"input_fingerprint={result.input_fingerprint}")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
