"""The Mode-③ runtime bridge connects R5 sequences -> analyze -> video controller.

These assert the *connection* behaves: a clean target escalates to a video clip
and pure environmental noise never fires one, plus the search/JSON plumbing.
"""
from __future__ import annotations

import json

import numpy as np

from pollipi_analysis.pipeline import PipelineConfig
from pollipi_analysis.policy.artifact import load_policy
from pollipi_analysis.simulation import runtime_bridge as rb
from pollipi_analysis.simulation.r5_scenarios import N_FRAMES, SCENARIOS, generate_sequence


def test_r5_scenarios_reused_without_r6() -> None:
    # The R5 stimulus set is reused (incl. the listed names); nothing R6 here.
    for name in ("wind", "local_sway", "shadow", "camera_shake", "target_clean",
                 "target_edge", "target_low_snr", "target_wind", "target_shadow"):
        assert name in SCENARIOS
    assert "rolling" not in " ".join(dir(rb)).lower()


def test_to_pi_luma_rescales_to_camera_scale() -> None:
    frame = generate_sequence("target_clean", 1)[0]
    luma = rb.to_pi_luma(frame)
    assert luma.shape == (rb.LUMA_H, rb.LUMA_W)
    assert luma.min() >= 0.0 and luma.max() <= 255.0
    assert luma.max() > 1.0  # genuinely on the 0-255 scale, not [0,1]


def test_decision_states_has_one_per_pair() -> None:
    states = rb.decision_states(generate_sequence("target_clean", 1), PipelineConfig())
    assert len(states) == N_FRAMES - 1


def test_clean_target_fires_video_noise_does_not() -> None:
    cfg = PipelineConfig()
    target = rb.run_sequence("target_clean", "target", 1, cfg, rb.default_video_config())
    shake = rb.run_sequence("camera_shake", "noise", 1, cfg, rb.default_video_config())
    assert target.produced_strong and target.fired_video
    assert not shake.fired_video and not shake.reached_mid_or_video


def test_evaluate_config_metrics_are_rates() -> None:
    m = rb.evaluate_config(PipelineConfig(), n_reps=2)
    for key in (
        "noise_no_video_rate",
        "target_mid_or_video_rate",
        "strong_to_video_rate",
        "false_video_trigger_rate",
    ):
        assert 0.0 <= m[key] <= 1.0
    # Default config must reject noise: no false video triggers on the noise set.
    assert m["false_video_trigger_rate"] == 0.0
    assert m["noise_no_video_rate"] == 1.0


def test_search_is_deterministic_and_picks_a_config() -> None:
    grid = rb.SearchGrid(
        pixel_difference=(25, 30),
        active_cell_threshold=(0.08,),
        strong_spatial_concentration=(0.70,),
        shake_shift_px=(2.5,),
    )
    a = rb.search(grid, n_reps=2, seed=11)
    b = rb.search(grid, n_reps=2, seed=11)
    assert a[1] == b[1]  # same seed -> identical best metrics
    assert isinstance(a[0], PipelineConfig)
    assert len(a[2]) == 2  # one row per grid config


def test_generate_policy_writes_loadable_simulation_informed_json(tmp_path) -> None:
    grid = rb.SearchGrid(
        pixel_difference=(25,),
        active_cell_threshold=(0.08,),
        strong_spatial_concentration=(0.70,),
        shake_shift_px=(2.5,),
    )
    out = tmp_path / "simulation_informed_policy.json"
    path, config, metrics = rb.generate_policy(out, seed=7, n_reps=2, grid=grid)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["validation_status"] == "simulation_informed"
    assert data["policy_name"] and data["policy_version"]
    for key in ("seed", "generated_at", "notes"):
        assert key in data["metadata"]
    assert data["metadata"]["seed"] == 7
    assert data["feature"] and data["classifier"]

    # Round-trips into a real PipelineConfig the Pi runtime would load.
    loaded_config, meta = load_policy(path)
    assert loaded_config.features == config.features
    assert loaded_config.classifier == config.classifier
    assert meta.validation_status == "simulation_informed"
