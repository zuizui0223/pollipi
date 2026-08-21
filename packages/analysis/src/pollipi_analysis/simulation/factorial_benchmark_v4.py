"""Run the held-out factorial V4 pixels through PolliPi's unchanged front end."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.simulation.factorial_world_v4 import build_registry, render_condition, suite_fingerprint

SCHEMA = "pollipi-insepi-factorial-v4"


@dataclass(frozen=True, slots=True)
class PolliPiFactorialResult:
    schema: str
    condition_id: str
    split: str
    true_visit: bool
    disturbance_family: str
    pollipi_state: str
    pollipi_reason: str
    global_synchrony: float
    active_cell_proportion: float
    estimated_global_shift: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def disturbance_family(condition) -> str:
    active = [
        name for name in ("wind", "shake", "shadow", "occlusion", "blur", "clutter", "lens")
        if getattr(condition, name) > 0
    ]
    return "+".join(active) if active else "clean"


def run_factorial_v4(split: str | None = None) -> list[PolliPiFactorialResult]:
    rows: list[PolliPiFactorialResult] = []
    for condition in build_registry():
        if split is not None and condition.split != split:
            continue
        background, frame = render_condition(condition)
        decision = analyze(frame, background)
        features = decision.features
        rows.append(PolliPiFactorialResult(
            schema=SCHEMA,
            condition_id=condition.condition_id,
            split=condition.split,
            true_visit=condition.true_visit,
            disturbance_family=disturbance_family(condition),
            pollipi_state=str(decision.state),
            pollipi_reason=decision.reason,
            global_synchrony=features.global_synchrony,
            active_cell_proportion=features.active_cell_proportion,
            estimated_global_shift=features.estimated_global_shift,
        ))
    return rows


def write_factorial_trace_jsonl(path: str | Path, *, source_commit: str | None = None) -> Path:
    """Write the portable V4 trace consumed by sibling benchmark tooling.

    The trace contains PolliPi outputs and benchmark provenance only. It contains
    no InsePi logic and therefore preserves the independent-observer boundary.
    """

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    provenance = {
        "record_type": "provenance",
        "schema": SCHEMA,
        "world_fingerprint": suite_fingerprint(),
        "source_commit": source_commit,
    }
    with output.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(provenance, sort_keys=True) + "\n")
        for row in run_factorial_v4():
            payload = row.to_dict()
            payload["record_type"] = "result"
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return output


def summarize_factorial_v4(rows: list[PolliPiFactorialResult]) -> dict[str, object]:
    by_split_state = Counter((row.split, row.pollipi_state) for row in rows)
    test_visits = [row for row in rows if row.split == "test" and row.true_visit]
    recovered = sum(row.pollipi_state in {"strong_visitation_candidate", "uncertain_local_activity"} for row in test_visits)
    return {
        "n": len(rows),
        "by_split_state": {f"{split}:{state}": count for (split, state), count in sorted(by_split_state.items())},
        "test_visit_candidate_recall": recovered / len(test_visits) if test_visits else 0.0,
    }
