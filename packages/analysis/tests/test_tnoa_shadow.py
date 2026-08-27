from __future__ import annotations

import numpy as np

from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.features import MeshFeatures
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    STRONG_VISITATION_CANDIDATE,
)
from pollipi_analysis.tnoa_shadow import build_tnoa_shadow_record


def _features(**overrides) -> MeshFeatures:
    base = dict(
        active_cell_proportion=0.08,
        largest_component_cells=3,
        concentration=0.6,
        spatial_concentration=0.8,
        offset_active_cell_proportion=0.07,
        offset_agreement=0.7,
        persistence=0.5,
        centroid_x=12.0,
        centroid_y=10.0,
        centroid_displacement=1.0,
        path_efficiency=0.8,
        active_set_jaccard=0.4,
        global_synchrony=0.12,
        estimated_global_shift=0.3,
        cell_size=16,
    )
    base.update(overrides)
    return MeshFeatures(**base)


def _yuv420(value: int = 100) -> np.ndarray:
    # 4x6 is a valid tiny YUV420-style storage shape: top 4 rows are luminance.
    arr = np.zeros((6, 4), dtype=np.uint8)
    arr[:4, :] = value
    return arr


def test_phase_a_never_promotes_uncalibrated_support() -> None:
    decision = MeshDecision(
        state=STRONG_VISITATION_CANDIDATE,
        reason="localized_concentrated_offset_agreement",
        features=_features(),
    )
    record = build_tnoa_shadow_record(
        decision,
        _yuv420(),
        expected_probe_interval_sec=5.0,
        actual_probe_interval_sec=5.25,
    )

    assert record.target.ordinal_score == 1.0
    assert record.target.confirmed_visit is False
    assert record.target.calibrated_support is None
    assert record.nuisance.calibrated_support is None
    assert record.observability.calibrated_support is None
    assert record.coupled.available is False
    assert record.absence.available is False
    assert record.observation_state == "U"
    assert record.u_reason == "field_calibration_pending"
    assert record.would_be_action == "observe_only"
    assert record.action_applied is False


def test_environmental_noise_state_is_not_nuisance_truth() -> None:
    decision = MeshDecision(
        state=ENVIRONMENTAL_NOISE,
        reason="broad_global_synchrony",
        features=_features(global_synchrony=0.9, estimated_global_shift=4.0),
    )
    record = build_tnoa_shadow_record(decision, _yuv420())

    # The PolliPi state maps only to zero direct target evidence. N remains an
    # uncalibrated positive-evidence channel carrying raw diagnostics.
    assert record.target.ordinal_score == 0.0
    assert record.nuisance.global_synchrony == 0.9
    assert record.nuisance.estimated_global_shift == 4.0
    assert record.nuisance.calibrated_support is None
    assert record.observation_state == "U"


def test_observability_metrics_are_raw_not_support() -> None:
    frame = _yuv420(100)
    frame[0, 0] = 0
    frame[0, 1] = 255
    record = build_tnoa_shadow_record(
        None,
        frame,
        expected_probe_interval_sec=5.0,
        actual_probe_interval_sec=6.5,
    )

    o = record.observability
    assert o.frame_available is True
    assert o.luma_mean is not None
    assert o.luma_std is not None
    assert o.gradient_mean is not None
    assert o.dark_fraction == 1 / 16
    assert o.bright_fraction == 1 / 16
    assert o.probe_interval_error_sec == 1.5
    assert o.roi_support_available is False
    assert o.calibrated_support is None
    assert record.u_reason == "reference_frame_pending"


def test_flat_record_has_stable_shadow_contract() -> None:
    record = build_tnoa_shadow_record(None, _yuv420())
    row = record.flat()
    assert row["schema_version"] == "tnoa-shadow-1"
    assert row["calibration_status"] == "unavailable"
    assert row["observation_state"] == "U"
    assert row["would_be_action"] == "observe_only"
    assert row["absence_available"] is False
