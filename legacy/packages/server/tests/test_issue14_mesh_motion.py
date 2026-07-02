from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from visit_monitor_server.services.mesh_motion import (  # noqa: E402
    ENVIRONMENTAL_NOISE,
    VISITATION_CANDIDATE,
    analyze_mesh_motion,
)
from visit_monitor_server.services.mesh_simulator import simulate_pair  # noqa: E402
from visit_monitor_server.services.motion import detect_motion  # noqa: E402


def test_localized_trajectory_is_candidate():
    background, frame = simulate_pair("localized_trajectory")

    result = analyze_mesh_motion(frame, background, pixel_difference=25, cell_size=32)

    assert result["mesh_decision"] == VISITATION_CANDIDATE
    assert result["mesh_active_cell_proportion"] < 0.25
    assert result["mesh_concentration"] >= 0.35


def test_boundary_crossing_still_agrees_with_offset_mesh():
    background = np.full((160, 160), 90, dtype=np.float32)
    frame = background.copy()
    frame[72:90, 63:80] = 170

    result = analyze_mesh_motion(frame, background, pixel_difference=25, cell_size=32)

    assert result["mesh_decision"] == VISITATION_CANDIDATE
    assert result["mesh_offset_agreement"] >= 0.45


def test_broad_wind_and_shadow_are_environmental_noise():
    for scenario in ("broad_wind", "shadow"):
        background, frame = simulate_pair(scenario)
        result = analyze_mesh_motion(frame, background, pixel_difference=20, cell_size=32)
        assert result["mesh_decision"] == ENVIRONMENTAL_NOISE


def test_camera_shake_is_environmental_noise():
    background, frame = simulate_pair("camera_shake")

    result = analyze_mesh_motion(frame, background, pixel_difference=10, cell_size=32)

    assert result["mesh_decision"] == ENVIRONMENTAL_NOISE
    assert result["mesh_reason"] in {"broad_common_mode_motion", "diffuse_or_low_confidence_motion"}


def test_oscillation_overlap_can_be_suppressed_as_noise():
    background, frame = simulate_pair("oscillation")
    first = analyze_mesh_motion(frame, background, pixel_difference=20, cell_size=32)

    second = analyze_mesh_motion(
        frame,
        background,
        pixel_difference=20,
        cell_size=32,
        previous_active_cells=first["mesh_active_cells"],
    )

    assert second["mesh_decision"] == ENVIRONMENTAL_NOISE
    assert second["mesh_return_to_origin_score"] >= 0.6


def test_detect_motion_exposes_mesh_metadata_for_full_frame():
    background, frame = simulate_pair("localized_trajectory")
    yuv = np.zeros((240, 256), dtype=np.float32)
    yuv[:192, :256] = frame

    metrics, detected, _new_background = detect_motion(
        yuv,
        background,
        pixel_difference=25,
        motion_ratio=0.001,
        monitor_size=(256, 192),
    )

    assert detected is True
    assert metrics["mesh_decision"] == VISITATION_CANDIDATE
    assert "localized_overlapping_mesh_motion" in metrics["candidate_reasons"]
