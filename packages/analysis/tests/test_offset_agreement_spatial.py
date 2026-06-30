"""Spatial ``offset_agreement`` (classifier integrity).

``offset_agreement`` is now a *spatial* co-location metric between the primary
and half-cell-offset meshes (score-weighted active-cell centroid distance over
~2 cells), not the old activity-*proportion* difference. These tests pin the
property the old metric lacked: equal-magnitude activity at *different* image
locations must score low, while a single compact target scores high — including
a target straddling a mesh-cell boundary.
"""
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.features.compute import _spatial_offset_agreement
from pollipi_analysis.pipeline import ClassifierConfig, analyze
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE
from pollipi_analysis.simulation.synthetic import simulate_pair

CELL = 32


def _cell(coord, center, score=1.0):
    return {"coord": coord, "center": center, "score": score}


def test_colocated_activity_scores_high() -> None:
    # Both meshes centred on the same spot -> full agreement.
    primary = [_cell((0, 0), (80.0, 80.0))]
    offset = [_cell((0, 0), (80.0, 80.0))]
    agree = _spatial_offset_agreement(primary, {(0, 0)}, offset, {(0, 0)}, cell_size=CELL)
    assert agree == pytest.approx(1.0)


def test_single_target_half_cell_offset_stays_above_strong_gate() -> None:
    # A real compact target lands in one primary cell and the half-shifted offset
    # cell ~half a cell away. That residual displacement must stay well above the
    # strong gate's 0.45 floor, or every clean target would be rejected.
    primary = [_cell((0, 0), (80.0, 80.0))]
    offset = [_cell((0, 0), (80.0 + CELL / 2, 80.0 + CELL / 2))]
    agree = _spatial_offset_agreement(primary, {(0, 0)}, offset, {(0, 0)}, cell_size=CELL)
    assert agree >= ClassifierConfig().strong_offset_agreement
    assert agree >= 0.6


def test_equal_magnitude_but_displaced_activity_scores_low() -> None:
    # SAME active-cell count / score in both meshes, but at opposite corners of
    # the frame. The old proportion metric scored this ~1.0; spatially it is a
    # disagreement and must score low.
    primary = [_cell((0, 0), (40.0, 40.0))]
    offset = [_cell((5, 6), (220.0, 200.0))]
    agree = _spatial_offset_agreement(primary, {(0, 0)}, offset, {(5, 6)}, cell_size=CELL)
    assert agree < 0.2


def test_one_mesh_silent_means_no_agreement() -> None:
    primary = [_cell((0, 0), (80.0, 80.0))]
    agree = _spatial_offset_agreement(primary, {(0, 0)}, [], set(), cell_size=CELL)
    assert agree == 0.0


def test_compact_target_has_high_offset_agreement_end_to_end() -> None:
    background, frame = simulate_pair("localized_trajectory", seed=7)
    decision = analyze(frame, background)
    assert decision.state == STRONG_VISITATION_CANDIDATE
    assert decision.features.offset_agreement >= ClassifierConfig().strong_offset_agreement


def test_boundary_crossing_target_is_not_unfairly_dropped() -> None:
    # A target straddling a mesh-cell boundary is exactly what the offset mesh is
    # for: both meshes localise it to the same place, so spatial agreement stays
    # high and the strong candidate is not dropped.
    background, frame = simulate_pair("boundary_crossing", seed=7)
    decision = analyze(frame, background)
    assert decision.state == STRONG_VISITATION_CANDIDATE
    assert decision.features.offset_agreement >= ClassifierConfig().strong_offset_agreement
