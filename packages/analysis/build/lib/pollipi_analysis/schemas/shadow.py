"""Shadow-mode logging contract.

Shadow mode observes the live fixed-interval timelapse and records what the
adaptive policy *would* have done, without changing capture timing and without
saving a per-motion full-resolution image. Each scheduled capture appends one
:class:`ShadowDecisionRecord` to a CSV/JSONL log.

Stability guarantees encoded by this contract:

- ``applied`` is always ``False`` in shadow mode (the interval is never changed).
- ``current_interval_sec`` is the real, unchanged scheduled interval.
- ``would_be_next_interval_sec`` is advisory only.
- There is no image path field: shadow mode must not persist motion frames.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.states import DecisionState

SHADOW_LOG_VERSION = "shadow-1"

# Stable CSV column order. Append-only: never reorder or remove columns without
# bumping SHADOW_LOG_VERSION, so historical shadow logs stay parseable.
SHADOW_LOG_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "device_id",
    "frame_index",
    "captured_at",
    "current_interval_sec",
    "would_be_next_interval_sec",
    "applied",
    "decision_state",
    "reason",
    "activity_score",
    "active_cell_proportion",
    "offset_active_cell_proportion",
    "offset_agreement",
    "largest_component_cells",
    "concentration",
    "spatial_concentration",
    "persistence",
    "centroid_x",
    "centroid_y",
    "centroid_displacement",
    "path_efficiency",
    "direction_reversal",
    "global_synchrony",
    "estimated_global_shift",
    "cell_size",
    "mesh_layout",
)


@dataclass(frozen=True)
class ShadowDecisionRecord:
    frame_index: int
    captured_at: str
    current_interval_sec: float
    would_be_next_interval_sec: float
    decision: MeshDecision
    activity_score: float
    device_id: str = ""
    # Shadow mode never changes timing, so this is always False here. The field
    # exists so the same record type can describe a future live-adaptive run.
    applied: bool = False
    schema_version: str = SHADOW_LOG_VERSION
    extra: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        """Flat dict keyed by :data:`SHADOW_LOG_COLUMNS` for CSV writing."""
        f = self.decision.features
        row: dict[str, Any] = {
            "schema_version": self.schema_version,
            "device_id": self.device_id,
            "frame_index": self.frame_index,
            "captured_at": self.captured_at,
            "current_interval_sec": self.current_interval_sec,
            "would_be_next_interval_sec": self.would_be_next_interval_sec,
            "applied": self.applied,
            "decision_state": self.decision.state,
            "reason": self.decision.reason,
            "activity_score": self.activity_score,
            "active_cell_proportion": f.active_cell_proportion,
            "offset_active_cell_proportion": f.offset_active_cell_proportion,
            "offset_agreement": f.offset_agreement,
            "largest_component_cells": f.largest_component_cells,
            "concentration": f.concentration,
            "spatial_concentration": f.spatial_concentration,
            "persistence": f.persistence,
            "centroid_x": f.centroid_x,
            "centroid_y": f.centroid_y,
            "centroid_displacement": f.centroid_displacement,
            "path_efficiency": f.path_efficiency,
            "direction_reversal": f.direction_reversal,
            "global_synchrony": f.global_synchrony,
            "estimated_global_shift": f.estimated_global_shift,
            "cell_size": f.cell_size,
            "mesh_layout": f.mesh_layout,
        }
        return row

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("decision", None)
        data["decision"] = self.decision.flat()
        return data


def state_of(record: ShadowDecisionRecord) -> DecisionState:
    return record.decision.state
