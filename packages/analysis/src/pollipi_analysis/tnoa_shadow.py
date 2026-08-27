"""Fail-closed TNOA shadow evidence for Raspberry Pi field probes.

Phase A deliberately records *raw* target, nuisance and observability evidence
without converting development-time numbers into field support thresholds.  The
runtime therefore emits an unresolved observation and ``observe_only`` until a
separate field calibration profile is frozen.

Important boundaries
--------------------
- PolliPi target evidence is ordinal and is not confirmed visitation.
- ``environmental_noise`` is never converted directly into nuisance truth.
- raw nuisance features are diagnostics, not calibrated nuisance support.
- image-quality diagnostics are not calibrated observability support.
- no coupled-response or target-absence channel is invented.
- this module cannot change capture timing; it only produces a shadow record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

import numpy as np

from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.target_evidence import to_target_evidence

SCHEMA_VERSION = "tnoa-shadow-1"
CALIBRATION_STATUS = "unavailable"
OBSERVATION_STATE = "U"
ACTION = "observe_only"


@dataclass(frozen=True, slots=True)
class TargetShadowEvidence:
    source_state: str
    ordinal_score: Optional[float]
    confirmed_visit: bool = False
    calibrated_support: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class NuisanceShadowEvidence:
    global_synchrony: Optional[float]
    estimated_global_shift: Optional[float]
    active_cell_proportion: Optional[float]
    largest_component_cells: Optional[int]
    spatial_concentration: Optional[float]
    calibrated_support: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class ObservabilityShadowEvidence:
    frame_available: bool
    frame_format: str
    luma_mean: Optional[float]
    luma_std: Optional[float]
    dark_fraction: Optional[float]
    bright_fraction: Optional[float]
    gradient_mean: Optional[float]
    expected_probe_interval_sec: Optional[float]
    actual_probe_interval_sec: Optional[float]
    probe_interval_error_sec: Optional[float]
    roi_support_available: bool = False
    calibrated_support: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class CoupledShadowEvidence:
    available: bool = False
    response_score: Optional[float] = None
    target_link_confidence: Optional[float] = None
    calibrated_support: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class AbsenceShadowEvidence:
    available: bool = False
    source: str = "unavailable"
    calibrated_support: Optional[bool] = None


@dataclass(frozen=True, slots=True)
class TNOAShadowRecord:
    target: TargetShadowEvidence
    nuisance: NuisanceShadowEvidence
    observability: ObservabilityShadowEvidence
    coupled: CoupledShadowEvidence = CoupledShadowEvidence()
    absence: AbsenceShadowEvidence = AbsenceShadowEvidence()
    schema_version: str = SCHEMA_VERSION
    calibration_status: str = CALIBRATION_STATUS
    observation_state: str = OBSERVATION_STATE
    u_reason: str = "field_calibration_pending"
    would_be_action: str = ACTION
    action_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def flat(self) -> dict[str, Any]:
        """Return a stable flat row for CSV logging on the Pi."""
        return {
            "schema_version": self.schema_version,
            "calibration_status": self.calibration_status,
            "observation_state": self.observation_state,
            "u_reason": self.u_reason,
            "would_be_action": self.would_be_action,
            "action_applied": self.action_applied,
            "target_source_state": self.target.source_state,
            "target_ordinal_score": self.target.ordinal_score,
            "target_confirmed_visit": self.target.confirmed_visit,
            "target_calibrated_support": self.target.calibrated_support,
            "nuisance_calibrated_support": self.nuisance.calibrated_support,
            "nuisance_global_synchrony": self.nuisance.global_synchrony,
            "nuisance_estimated_global_shift": self.nuisance.estimated_global_shift,
            "nuisance_active_cell_proportion": self.nuisance.active_cell_proportion,
            "nuisance_largest_component_cells": self.nuisance.largest_component_cells,
            "nuisance_spatial_concentration": self.nuisance.spatial_concentration,
            "observability_calibrated_support": self.observability.calibrated_support,
            "observability_frame_available": self.observability.frame_available,
            "observability_frame_format": self.observability.frame_format,
            "observability_luma_mean": self.observability.luma_mean,
            "observability_luma_std": self.observability.luma_std,
            "observability_dark_fraction": self.observability.dark_fraction,
            "observability_bright_fraction": self.observability.bright_fraction,
            "observability_gradient_mean": self.observability.gradient_mean,
            "observability_expected_probe_interval_sec": self.observability.expected_probe_interval_sec,
            "observability_actual_probe_interval_sec": self.observability.actual_probe_interval_sec,
            "observability_probe_interval_error_sec": self.observability.probe_interval_error_sec,
            "observability_roi_support_available": self.observability.roi_support_available,
            "coupled_available": self.coupled.available,
            "coupled_response_score": self.coupled.response_score,
            "coupled_target_link_confidence": self.coupled.target_link_confidence,
            "coupled_calibrated_support": self.coupled.calibrated_support,
            "absence_available": self.absence.available,
            "absence_source": self.absence.source,
            "absence_calibrated_support": self.absence.calibrated_support,
        }


def _luma_plane(frame: Any, frame_format: str) -> np.ndarray:
    arr = np.asarray(frame)
    if arr.size == 0:
        raise ValueError("empty frame")

    fmt = frame_format.upper()
    if fmt == "YUV420":
        if arr.ndim != 2:
            raise ValueError("YUV420 probe must be a 2-D array")
        y_rows = arr.shape[0] * 2 // 3
        if y_rows <= 0:
            raise ValueError("invalid YUV420 probe height")
        return np.asarray(arr[:y_rows], dtype=np.float32)

    if arr.ndim == 2:
        return np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        rgb = np.asarray(arr[..., :3], dtype=np.float32)
        return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    raise ValueError(f"unsupported frame shape for {frame_format}: {arr.shape}")


def _observability_raw(
    frame: Any,
    *,
    frame_format: str,
    expected_probe_interval_sec: Optional[float],
    actual_probe_interval_sec: Optional[float],
) -> ObservabilityShadowEvidence:
    if frame is None:
        return ObservabilityShadowEvidence(
            frame_available=False,
            frame_format=frame_format,
            luma_mean=None,
            luma_std=None,
            dark_fraction=None,
            bright_fraction=None,
            gradient_mean=None,
            expected_probe_interval_sec=expected_probe_interval_sec,
            actual_probe_interval_sec=actual_probe_interval_sec,
            probe_interval_error_sec=None,
        )

    y = _luma_plane(frame, frame_format)
    if y.shape[0] > 1:
        gy = float(np.mean(np.abs(np.diff(y, axis=0))))
    else:
        gy = 0.0
    if y.shape[1] > 1:
        gx = float(np.mean(np.abs(np.diff(y, axis=1))))
    else:
        gx = 0.0
    interval_error = None
    if expected_probe_interval_sec is not None and actual_probe_interval_sec is not None:
        interval_error = abs(float(actual_probe_interval_sec) - float(expected_probe_interval_sec))

    return ObservabilityShadowEvidence(
        frame_available=True,
        frame_format=frame_format,
        luma_mean=float(np.mean(y)),
        luma_std=float(np.std(y)),
        dark_fraction=float(np.mean(y <= 5.0)),
        bright_fraction=float(np.mean(y >= 250.0)),
        gradient_mean=gx + gy,
        expected_probe_interval_sec=expected_probe_interval_sec,
        actual_probe_interval_sec=actual_probe_interval_sec,
        probe_interval_error_sec=interval_error,
    )


def build_tnoa_shadow_record(
    decision: Optional[MeshDecision],
    frame: Any,
    *,
    expected_probe_interval_sec: Optional[float] = None,
    actual_probe_interval_sec: Optional[float] = None,
    frame_format: str = "YUV420",
) -> TNOAShadowRecord:
    """Build one Phase-A field record without licensing any field support call."""
    if decision is None:
        target = TargetShadowEvidence(
            source_state="waiting_for_reference_frame",
            ordinal_score=None,
        )
        nuisance = NuisanceShadowEvidence(None, None, None, None, None)
        reason = "reference_frame_pending"
    else:
        target_record = to_target_evidence(decision.state)
        target = TargetShadowEvidence(
            source_state=str(target_record.source_state),
            ordinal_score=float(target_record.score),
            confirmed_visit=False,
        )
        f = decision.features
        nuisance = NuisanceShadowEvidence(
            global_synchrony=float(f.global_synchrony),
            estimated_global_shift=float(f.estimated_global_shift),
            active_cell_proportion=float(f.active_cell_proportion),
            largest_component_cells=int(f.largest_component_cells),
            spatial_concentration=float(f.spatial_concentration),
        )
        reason = "field_calibration_pending"

    observability = _observability_raw(
        frame,
        frame_format=frame_format,
        expected_probe_interval_sec=expected_probe_interval_sec,
        actual_probe_interval_sec=actual_probe_interval_sec,
    )
    return TNOAShadowRecord(
        target=target,
        nuisance=nuisance,
        observability=observability,
        u_reason=reason,
    )
