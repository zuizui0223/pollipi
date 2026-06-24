from __future__ import annotations

import json
from pathlib import Path

from pollipi_analysis.policy import (
    DEFAULT_POLICY_PROFILE_ID,
    PolicyProfile,
    create_policy_controller,
    get_policy_profile,
)


def test_json_policy_profiles_are_versioned_and_allowed() -> None:
    root = Path(__file__).resolve().parents[1] / "policy_profiles"
    profiles = [PolicyProfile.from_mapping(json.loads(path.read_text(encoding="utf-8"))) for path in root.glob("*.json")]

    assert {profile.profile_id for profile in profiles} >= {
        "three_stage_default_v1",
        "three_stage_sensitive_v1",
    }
    assert all(profile.kind == "three_stage" for profile in profiles)


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
