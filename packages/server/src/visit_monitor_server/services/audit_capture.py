"""Default-off shadow audit capture for PolliPi probe streams.

This module turns the pure audit primitives in ``audit_runtime`` into a storage
surface without changing capture timing or semantic decisions.  It is enabled only
when ``POLLIPI_AUDIT_ENABLED`` is true and all required pre-collection settings are
explicitly supplied.

The saved primary is the lossless Y plane from the existing low-resolution YUV420
probe.  The saved reference is a predeclared target-free crop from that same Y
plane.  Biological truth and physical nuisance truth are deliberately not inferred
here; they are joined later from independent sources.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from visit_monitor_server.services.audit_runtime import (
    AuditProbeSample,
    AuditWindowCoordinator,
    CompletedAuditWindow,
    audit_draw,
)

AUDIT_SUBDIR = "probability_audit"
AUDIT_DRAW_SCHEMA = "pollipi-audit-draw-v1"
AUDIT_WINDOW_SCHEMA = "pollipi-audit-window-v1"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set when POLLIPI_AUDIT_ENABLED=true")
    return value


def _required_probability(name: str) -> float:
    raw = _required_env(name)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not np.isfinite(value) or not (0.0 < value <= 1.0):
        raise ValueError(f"{name} must satisfy 0 < p <= 1")
    return value


def _parse_window_size() -> int:
    raw = os.getenv("POLLIPI_AUDIT_WINDOW_PROBES", "9").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("POLLIPI_AUDIT_WINDOW_PROBES must be an integer") from exc
    if value < 3 or value % 2 != 1:
        raise ValueError("POLLIPI_AUDIT_WINDOW_PROBES must be an odd integer >= 3")
    return value


def _parse_reference_roi() -> tuple[float, float, float, float]:
    raw = _required_env("POLLIPI_AUDIT_REFERENCE_ROI")
    pieces = [piece.strip() for piece in raw.split(",")]
    if len(pieces) != 4:
        raise ValueError(
            "POLLIPI_AUDIT_REFERENCE_ROI must be normalized x0,y0,x1,y1"
        )
    try:
        x0, y0, x1, y1 = (float(piece) for piece in pieces)
    except ValueError as exc:
        raise ValueError("POLLIPI_AUDIT_REFERENCE_ROI values must be numeric") from exc
    values = (x0, y0, x1, y1)
    if not all(np.isfinite(value) for value in values):
        raise ValueError("POLLIPI_AUDIT_REFERENCE_ROI values must be finite")
    if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
        raise ValueError(
            "POLLIPI_AUDIT_REFERENCE_ROI must satisfy 0<=x0<x1<=1 and 0<=y0<y1<=1"
        )
    return values


def _y_plane(frame: Any) -> np.ndarray:
    arr = np.asarray(frame)
    if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("audit probe frame must be a 2-D YUV420 array")
    y_rows = arr.shape[0] * 2 // 3
    if y_rows <= 0 or y_rows > arr.shape[0]:
        raise ValueError("audit probe frame has invalid YUV420 geometry")
    return np.clip(arr[:y_rows], 0, 255).astype("uint8", copy=True)


def _reference_crop(
    primary: np.ndarray, roi: tuple[float, float, float, float]
) -> np.ndarray:
    height, width = primary.shape
    x0, y0, x1, y1 = roi
    left = min(width - 1, max(0, int(np.floor(x0 * width))))
    top = min(height - 1, max(0, int(np.floor(y0 * height))))
    right = min(width, max(left + 1, int(np.ceil(x1 * width))))
    bottom = min(height, max(top + 1, int(np.ceil(y1 * height))))
    crop = primary[top:bottom, left:right]
    if crop.size == 0:
        raise ValueError("POLLIPI_AUDIT_REFERENCE_ROI produced an empty crop")
    return crop.copy()


@dataclass(frozen=True)
class AuditCaptureConfig:
    enabled: bool
    seed: str | None = None
    q_selected: float | None = None
    q_omitted: float | None = None
    window_size: int = 9
    reference_roi: tuple[float, float, float, float] | None = None

    @classmethod
    def from_environment(cls) -> "AuditCaptureConfig":
        enabled = _env_bool("POLLIPI_AUDIT_ENABLED", False)
        if not enabled:
            return cls(enabled=False)
        return cls(
            enabled=True,
            seed=_required_env("POLLIPI_AUDIT_SEED"),
            q_selected=_required_probability("POLLIPI_AUDIT_Q_SELECTED"),
            q_omitted=_required_probability("POLLIPI_AUDIT_Q_OMITTED"),
            window_size=_parse_window_size(),
            reference_roi=_parse_reference_roi(),
        )


class AuditCaptureManager:
    """Store probability-sampled centred probe windows in shadow mode."""

    def __init__(
        self,
        *,
        image_dir: Path,
        run_id: str,
        device_id: str,
        config: AuditCaptureConfig,
    ) -> None:
        self.image_dir = Path(image_dir)
        self.run_id = str(run_id)
        self.device_id = str(device_id)
        self.config = config
        self._coordinator: AuditWindowCoordinator[np.ndarray, np.ndarray] | None = None
        self._root: Path | None = None
        self._draw_log: Path | None = None
        self._draw_count = 0
        self._window_count = 0
        self._finalized = False

        if not config.enabled:
            return
        if not self.run_id or not self.device_id:
            raise ValueError("run_id and device_id must be non-empty for audit capture")
        if config.seed is None or config.q_selected is None or config.q_omitted is None:
            raise ValueError("enabled audit capture requires seed and probabilities")
        if config.reference_roi is None:
            raise ValueError("enabled audit capture requires a reference ROI")

        self._coordinator = AuditWindowCoordinator(window_size=config.window_size)
        self._root = self.image_dir / AUDIT_SUBDIR / self.run_id
        self._root.mkdir(parents=True, exist_ok=True)
        self._draw_log = self._root / "audit_draws.csv"
        with self._draw_log.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(
                [
                    "schema_version",
                    "opportunity_id",
                    "probe_timestamp",
                    "selected",
                    "audit_included",
                    "inclusion_probability",
                    "stratum",
                    "uniform_draw",
                ]
            )
        (self._root / "config.json").write_text(
            json.dumps(
                {
                    "schema": "pollipi-audit-config-v1",
                    "run_id": self.run_id,
                    "device_id": self.device_id,
                    "seed": config.seed,
                    "q_selected": config.q_selected,
                    "q_omitted": config.q_omitted,
                    "window_size": config.window_size,
                    "reference_roi_normalized": list(config.reference_roi),
                    "selection_rule": "would_be_nonlow",
                    "live_capture_effect": "none",
                    "biological_truth_source": None,
                    "physical_truth_source": None,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled)

    @property
    def root(self) -> Path | None:
        return self._root

    @staticmethod
    def opportunity_id(device_id: str, run_id: str, probe_timestamp: str) -> str:
        if not device_id or not run_id or not probe_timestamp:
            raise ValueError("device_id, run_id and probe_timestamp are required")
        return f"{device_id}|{run_id}|{probe_timestamp}"

    def add_probe(
        self,
        *,
        frame: Any,
        probe_timestamp: str,
        selected: bool,
    ) -> CompletedAuditWindow[np.ndarray, np.ndarray] | None:
        if not self.enabled:
            return None
        if self._finalized:
            raise RuntimeError("audit capture manager is already finalized")
        assert self._coordinator is not None
        assert self._draw_log is not None
        assert self.config.seed is not None
        assert self.config.q_selected is not None
        assert self.config.q_omitted is not None
        assert self.config.reference_roi is not None

        opportunity_id = self.opportunity_id(
            self.device_id, self.run_id, probe_timestamp
        )
        draw = audit_draw(
            opportunity_id,
            selected=selected,
            seed=self.config.seed,
            q_selected=self.config.q_selected,
            q_omitted=self.config.q_omitted,
        )
        primary = _y_plane(frame)
        reference = _reference_crop(primary, self.config.reference_roi)
        sample = AuditProbeSample(
            opportunity_id=opportunity_id,
            probe_timestamp=probe_timestamp,
            primary=primary,
            reference=reference,
            selected=selected,
            audit_included=draw.included,
            inclusion_probability=draw.inclusion_probability,
        )
        with self._draw_log.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(
                [
                    AUDIT_DRAW_SCHEMA,
                    opportunity_id,
                    probe_timestamp,
                    bool(selected),
                    draw.included,
                    f"{draw.inclusion_probability:.17g}",
                    draw.stratum,
                    f"{draw.uniform_draw:.17g}",
                ]
            )
        self._draw_count += 1

        completed = self._coordinator.add(sample)
        if completed is not None:
            self._write_window(completed)
        return completed

    def _write_window(
        self, completed: CompletedAuditWindow[np.ndarray, np.ndarray]
    ) -> None:
        assert self._root is not None
        centre = completed.centre_opportunity_id
        safe_centre = centre.replace("|", "__").replace(":", "-").replace("+", "p")
        window_dir = self._root / "windows" / safe_centre
        window_dir.mkdir(parents=True, exist_ok=False)
        rows: list[dict[str, object]] = []
        for index, sample in enumerate(completed.samples):
            primary_name = f"{index:02d}_primary.npy"
            reference_name = f"{index:02d}_reference.npy"
            np.save(window_dir / primary_name, sample.primary, allow_pickle=False)
            np.save(window_dir / reference_name, sample.reference, allow_pickle=False)
            rows.append(
                {
                    "index": index,
                    "opportunity_id": sample.opportunity_id,
                    "probe_timestamp": sample.probe_timestamp,
                    "selected": sample.selected,
                    "audit_included": sample.audit_included,
                    "inclusion_probability": sample.inclusion_probability,
                    "primary_file": primary_name,
                    "reference_file": reference_name,
                }
            )
        (window_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": AUDIT_WINDOW_SCHEMA,
                    "centre_opportunity_id": centre,
                    "window_size": len(completed.samples),
                    "samples": rows,
                    "truth_state": None,
                    "physical_truth_state": None,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self._window_count += 1

    def finalize(self) -> None:
        if not self.enabled or self._finalized:
            return
        assert self._coordinator is not None
        assert self._root is not None
        (self._root / "run_summary.json").write_text(
            json.dumps(
                {
                    "schema": "pollipi-audit-run-summary-v1",
                    "run_id": self.run_id,
                    "draw_count": self._draw_count,
                    "completed_window_count": self._window_count,
                    "completed_centres": list(self._coordinator.completed_centres),
                    "incomplete_included_centres": list(
                        self._coordinator.incomplete_included_centres
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self._finalized = True
