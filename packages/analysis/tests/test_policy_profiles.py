from __future__ import annotations

import json
from pathlib import Path

import pytest

from pollipi_analysis.policy import (
    DEFAULT_POLICY_PROFILE_ID,
    PolicyProfile,
    create_policy_controller,
    get_policy_profile,
    list_policy_profiles,
)


def test_json_policy_profiles_are_versioned_and_allowed() -> None:
    root = Path(__file__).resolve().parents[1] / "policy_profiles"
    profiles = [PolicyProfile.from_mapping(json.loads(path.read_text(encoding="utf-8"))) for path in root.glob("*.json")]

    assert {profile.profile_id for profile in profiles} >= {
        "three_stage_default_v1",
        "three_stage_sensitive_v1",
    }
    assert all(profile.kind == "three_stage" for profile in profiles)
    # D1: existing (non-canary) profiles stay live_allowed=false; only an explicitly
    # named canary profile may set it true (and even then it is one of three gates).
    by_id = {p.profile_id: p for p in profiles}
    assert by_id["three_stage_default_v1"].live_allowed is False
    assert by_id["three_stage_sensitive_v1"].live_allowed is False
    assert all(
        "canary" in p.profile_id for p in profiles if p.live_allowed is True
    )


def _profile_payload(profile_id: str, simulation_run_id: str | None = None) -> dict:
    return {
        "schema": "pollipi-policy-profile-1",
        "profile_id": profile_id,
        "simulation_run_id": simulation_run_id or f"run-{profile_id}",
        "source_commit": f"analysis-{profile_id}",
        "kind": "three_stage",
        "live_allowed": False,
        "description": "test profile",
        "parameters": {
            "low_interval_sec": 30.0,
            "mid_interval_sec": 15.0,
            "high_interval_sec": 5.0,
            "high_hard_cap_sec": 120.0,
            "high_exit_quiet_probes": 3,
        },
    }


def _write_profile(directory: Path, name: str, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def test_adding_one_json_profile_makes_it_available(monkeypatch, tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    _write_profile(profile_dir, "default.json", _profile_payload(DEFAULT_POLICY_PROFILE_ID))
    _write_profile(profile_dir, "new.json", _profile_payload("three_stage_new_run_v1"))
    monkeypatch.setenv("POLLIPI_POLICY_PROFILE_DIR", str(profile_dir))

    assert {profile.profile_id for profile in list_policy_profiles()} == {
        DEFAULT_POLICY_PROFILE_ID,
        "three_stage_new_run_v1",
    }


def test_live_allowed_true_profile_is_accepted(monkeypatch, tmp_path: Path) -> None:
    # live_allowed=true is permitted at the profile layer; it is one of three gates
    # and never enables live timing on its own (see capture_loop.live_adaptive_active).
    profile_dir = tmp_path / "profiles"
    _write_profile(profile_dir, "default.json", _profile_payload(DEFAULT_POLICY_PROFILE_ID))
    payload = _profile_payload("three_stage_canary_v1", "run-canary")
    payload["live_allowed"] = True
    _write_profile(profile_dir, "canary.json", payload)
    monkeypatch.setenv("POLLIPI_POLICY_PROFILE_DIR", str(profile_dir))

    profiles = {p.profile_id: p for p in list_policy_profiles()}
    assert profiles["three_stage_canary_v1"].live_allowed is True


def test_live_allowed_non_bool_is_rejected(monkeypatch, tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    payload = _profile_payload(DEFAULT_POLICY_PROFILE_ID)
    payload["live_allowed"] = "yes"
    _write_profile(profile_dir, "default.json", payload)
    monkeypatch.setenv("POLLIPI_POLICY_PROFILE_DIR", str(profile_dir))

    with pytest.raises(ValueError, match="live_allowed must be a bool"):
        list_policy_profiles()


def test_duplicate_profile_id_is_rejected(monkeypatch, tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    _write_profile(profile_dir, "a.json", _profile_payload(DEFAULT_POLICY_PROFILE_ID))
    _write_profile(profile_dir, "b.json", _profile_payload(DEFAULT_POLICY_PROFILE_ID, "another-run"))
    monkeypatch.setenv("POLLIPI_POLICY_PROFILE_DIR", str(profile_dir))

    with pytest.raises(ValueError, match="duplicate policy profile_id"):
        list_policy_profiles()


def test_kind_required_parameter_validation(monkeypatch, tmp_path: Path) -> None:
    profile_dir = tmp_path / "profiles"
    payload = _profile_payload(DEFAULT_POLICY_PROFILE_ID)
    payload["parameters"].pop("high_interval_sec")
    _write_profile(profile_dir, "default.json", payload)
    monkeypatch.setenv("POLLIPI_POLICY_PROFILE_DIR", str(profile_dir))

    with pytest.raises(ValueError, match="missing parameters: high_interval_sec"):
        list_policy_profiles()


def test_policy_profile_factory_is_deterministic_for_pc_pi_parity() -> None:
    profile = get_policy_profile(DEFAULT_POLICY_PROFILE_ID)
    pc_controller = create_policy_controller(profile)
    pi_controller = create_policy_controller(profile)

    decisions = [
        "no_activity",
        "uncertain_local_activity",
        "strong_visitation_candidate",
        "strong_visitation_candidate",
        "environmental_noise",
        "no_activity",
        "no_activity",
    ]
    timestamps = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]

    pc_outputs = [pc_controller.step(state, now) for state, now in zip(decisions, timestamps)]
    pi_outputs = [pi_controller.step(state, now) for state, now in zip(decisions, timestamps)]

    assert [
        (out.mode, out.interval_sec, out.reason, out.local_candidate_streak, out.quiet_streak)
        for out in pc_outputs
    ] == [
        (out.mode, out.interval_sec, out.reason, out.local_candidate_streak, out.quiet_streak)
        for out in pi_outputs
    ]
