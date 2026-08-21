"""V2 contradiction trace from rendered pixels through the real PolliPi front end."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from pollipi_analysis.pipeline import analyze
from pollipi_analysis.simulation.portable_visual_v2 import SCENARIO_IDS, render_pair

VISUAL_SCHEMA = "pollipi-insepi-visual-contradiction-v2"


@dataclass(frozen=True, slots=True)
class PolliPiVisualResult:
    schema: str
    scenario_id: str
    true_visit: bool
    pollipi_state: str
    pollipi_reason: str
    active_cell_proportion: float
    concentration: float
    spatial_concentration: float
    global_synchrony: float
    estimated_global_shift: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_visual_contradiction_v2() -> list[PolliPiVisualResult]:
    rows: list[PolliPiVisualResult] = []
    for scenario_id in SCENARIO_IDS:
        background, frame, truth = render_pair(scenario_id)
        decision = analyze(frame, background)
        f = decision.features
        rows.append(PolliPiVisualResult(
            schema=VISUAL_SCHEMA,
            scenario_id=scenario_id,
            true_visit=truth,
            pollipi_state=str(decision.state),
            pollipi_reason=decision.reason,
            active_cell_proportion=f.active_cell_proportion,
            concentration=f.concentration,
            spatial_concentration=f.spatial_concentration,
            global_synchrony=f.global_synchrony,
            estimated_global_shift=f.estimated_global_shift,
        ))
    return rows


def write_visual_trace_jsonl(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in run_visual_contradiction_v2():
            handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")
    return output
