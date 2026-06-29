"""The server loads a simulation_informed policy and Mode-③ maps states correctly.

Covers the requested chain end-to-end at the runtime boundary:
  no_activity / environmental_noise -> normal (LOW) interval
  uncertain                          -> fast (MID) interval
  uncertain -> strong                -> video clip
"""
from __future__ import annotations

import importlib
import sys

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig
from pollipi_analysis.policy.artifact import PolicyMeta, write_policy
from pollipi_analysis.policy.three_stage import (
    HIGH,
    LOW,
    MID,
    ThreeStageConfig,
    ThreeStageController,
)
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)


def _clear() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _write_sim_policy(path) -> None:
    # A simulation_informed policy of the shape runtime_bridge.generate_policy emits.
    config = PipelineConfig(
        features=FeatureConfig(pixel_difference=25, active_cell_threshold=0.06),
        classifier=ClassifierConfig(strong_spatial_concentration=0.6, shake_shift_px=2.5),
    )
    write_policy(
        path,
        config,
        PolicyMeta(
            policy_name="simulation_informed_mode3_video",
            policy_version="1",
            validation_status="simulation_informed",
            seed=20260623,
            generated_at="2026-06-29T00:00:00+00:00",
            notes="test fixture",
        ),
    )


def test_server_loads_simulation_informed_policy(monkeypatch, tmp_path) -> None:
    policy = tmp_path / "simulation_informed_policy.json"
    _write_sim_policy(policy)
    monkeypatch.setenv("POLLIPI_POLICY_PATH", str(policy))
    _clear()
    policy_runtime = importlib.import_module("visit_monitor_server.services.policy_runtime")

    config, meta = policy_runtime.get_active_policy()
    assert meta.policy_name == "simulation_informed_mode3_video"
    assert meta.validation_status == "simulation_informed"
    assert meta.seed == 20260623
    # The numeric thresholds from the JSON are what the runtime will classify with.
    assert config.features.pixel_difference == 25
    assert config.features.active_cell_threshold == 0.06
    assert config.classifier.strong_spatial_concentration == 0.6


def test_server_falls_back_to_baseline_without_policy(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("POLLIPI_POLICY_PATH", str(tmp_path / "absent.json"))
    _clear()
    policy_runtime = importlib.import_module("visit_monitor_server.services.policy_runtime")
    _config, meta = policy_runtime.get_active_policy()
    assert meta.policy_name == "baseline_rule"
    assert meta.validation_status == "synthetic_only"


def _chain(states):
    cfg = ThreeStageConfig(high_mode="video", classify=True, low_interval_sec=30, mid_interval_sec=10)
    controller = ThreeStageController(cfg)
    return [controller.step(s, i * 5.0) for i, s in enumerate(states)]


def test_no_and_noise_stay_normal_interval() -> None:
    for state in (NO_ACTIVITY, ENVIRONMENTAL_NOISE):
        out = _chain([state])[0]
        assert out.mode == LOW and out.interval_sec == 30 and not out.trigger_video


def test_uncertain_enters_fast_interval() -> None:
    out = _chain([UNCERTAIN_LOCAL_ACTIVITY])[0]
    assert out.mode == MID and out.interval_sec == 10 and not out.trigger_video


def test_uncertain_then_strong_triggers_video() -> None:
    outs = _chain([UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE])
    assert outs[0].mode == MID and not outs[0].trigger_video
    assert outs[1].mode == HIGH and outs[1].trigger_video is True
