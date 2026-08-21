"""Run the commit-derived V5 pixels through PolliPi's frozen front end."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.simulation.locked_world_v5 import (
    build_registry,
    render_condition,
    seed_material,
    suite_fingerprint,
)

SCHEMA = "pollipi-insepi-locked-v5"


@dataclass(frozen=True, slots=True)
class PolliPiLockedV5Result:
    schema: str
    condition_id: str
    prevalence_regime: str
    true_visit: bool
    disturbance_family: str
    pollipi_state: str
    pollipi_reason: str
    global_synchrony: float
    active_cell_proportion: float
    estimated_global_shift: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_locked_v5(
    pollipi_commit_sha: str,
    insepi_commit_sha: str,
) -> list[PolliPiLockedV5Result]:
    rows: list[PolliPiLockedV5Result] = []
    for condition in build_registry(pollipi_commit_sha, insepi_commit_sha):
        background, frame = render_condition(condition)
        decision = analyze(frame, background)
        rows.append(PolliPiLockedV5Result(
            schema=SCHEMA,
            condition_id=condition.condition_id,
            prevalence_regime=condition.prevalence_regime,
            true_visit=condition.true_visit,
            disturbance_family=condition.disturbance_family,
            pollipi_state=str(decision.state),
            pollipi_reason=decision.reason,
            global_synchrony=decision.features.global_synchrony,
            active_cell_proportion=decision.features.active_cell_proportion,
            estimated_global_shift=decision.features.estimated_global_shift,
        ))
    return rows


def _checkout_state() -> tuple[str, bool]:
    """Return the source HEAD and tracked-file cleanliness for provenance."""

    start = Path(__file__).resolve()
    root = next((parent for parent in start.parents if (parent / ".git").exists()), None)
    if root is None:
        raise RuntimeError("locked V5 trace generation requires a PolliPi Git checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().lower()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return head, not status


def _require_frozen_checkout(pollipi_commit_sha: str) -> None:
    head, tracked_clean = _checkout_state()
    if head != pollipi_commit_sha.strip().lower():
        raise RuntimeError("PolliPi locked V5 source commit does not match checkout HEAD")
    if not tracked_clean:
        raise RuntimeError("PolliPi locked V5 checkout has uncommitted tracked changes")


def write_locked_trace_jsonl(
    path: str | Path,
    *,
    pollipi_commit_sha: str,
    insepi_commit_sha: str,
) -> Path:
    _require_frozen_checkout(pollipi_commit_sha)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    results = run_locked_v5(pollipi_commit_sha, insepi_commit_sha)
    provenance = {
        "record_type": "provenance",
        "schema": SCHEMA,
        "pollipi_source_commit": pollipi_commit_sha,
        "insepi_source_commit": insepi_commit_sha,
        "seed_material_sha256": hashlib.sha256(
            seed_material(pollipi_commit_sha, insepi_commit_sha)
        ).hexdigest(),
        "world_fingerprint": suite_fingerprint(pollipi_commit_sha, insepi_commit_sha),
    }
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(provenance, sort_keys=True) + "\n")
        for row in results:
            payload = row.to_dict()
            payload["record_type"] = "result"
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the one-shot PolliPi V5 trace")
    parser.add_argument("output", type=Path)
    parser.add_argument("--pollipi-commit", required=True)
    parser.add_argument("--insepi-commit", required=True)
    args = parser.parse_args()
    write_locked_trace_jsonl(
        args.output,
        pollipi_commit_sha=args.pollipi_commit,
        insepi_commit_sha=args.insepi_commit,
    )


if __name__ == "__main__":
    main()
