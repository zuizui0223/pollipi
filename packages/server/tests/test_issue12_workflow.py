from __future__ import annotations

import pytest


def test_mesh_pipeline_uses_three_state_output_without_claiming_visit() -> None:
    np = pytest.importorskip("numpy")

    from pollipi_analysis.pipeline import analyze
    from pollipi_analysis.schemas.states import (
        ENVIRONMENTAL_NOISE,
        NO_ACTIVITY,
        STRONG_VISITATION_CANDIDATE,
        UNCERTAIN_LOCAL_ACTIVITY,
    )

    background = np.zeros((96, 96), dtype=np.uint8)
    frame = background.copy()
    frame[36:42, 36:42] = 255

    decision = analyze(frame, background)
    assert decision.state in {
        ENVIRONMENTAL_NOISE,
        NO_ACTIVITY,
        STRONG_VISITATION_CANDIDATE,
        UNCERTAIN_LOCAL_ACTIVITY,
    }
    assert isinstance(decision.reason, str)
    assert decision.reason
    assert decision.state != "confirmed_visit"


def test_mesh_pipeline_rejects_broad_global_change() -> None:
    np = pytest.importorskip("numpy")

    from pollipi_analysis.pipeline import analyze
    from pollipi_analysis.schemas.states import ENVIRONMENTAL_NOISE

    background = np.zeros((96, 96), dtype=np.uint8)
    frame = np.full((96, 96), 255, dtype=np.uint8)

    decision = analyze(frame, background)
    assert decision.state == ENVIRONMENTAL_NOISE
    assert decision.reason in {
        "broad_global_synchrony",
        "broad_active_cell_proportion",
        "large_diffuse_connected_component",
    }
