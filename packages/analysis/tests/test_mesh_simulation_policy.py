from __future__ import annotations

from pollipi_analysis.mesh import ENVIRONMENTAL_NOISE, VISITATION_CANDIDATE, analyze_mesh_motion
from pollipi_analysis.policy import decide_next_interval
from pollipi_analysis.simulation import simulate_pair


def test_laptop_simulation_runs_mesh_scenarios() -> None:
    background, frame = simulate_pair("localized_trajectory")
    result = analyze_mesh_motion(frame, background, pixel_difference=25, cell_size=32)
    assert result["mesh_decision"] == VISITATION_CANDIDATE

    for scenario in ("broad_wind", "camera_shake", "shadow"):
        background, frame = simulate_pair(scenario)
        result = analyze_mesh_motion(frame, background, pixel_difference=20, cell_size=32)
        assert result["mesh_decision"] == ENVIRONMENTAL_NOISE


def test_policy_shortens_for_candidates_and_stretches_for_noise() -> None:
    candidate = decide_next_interval(
        baseline_interval_sec=60,
        min_interval_sec=10,
        max_interval_sec=120,
        current_interval_sec=60,
        candidate_rate=0.8,
        visit_likeness=0.7,
        noise_likeness=0.0,
    )
    noise = decide_next_interval(
        baseline_interval_sec=60,
        min_interval_sec=10,
        max_interval_sec=120,
        current_interval_sec=60,
        candidate_rate=0.2,
        visit_likeness=0.0,
        noise_likeness=0.9,
    )

    assert candidate.next_interval_sec < 60
    assert noise.next_interval_sec >= candidate.next_interval_sec
