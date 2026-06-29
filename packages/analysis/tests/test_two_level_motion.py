"""Mode (2): no-classification motion reaction. ANY motion -> fast interval; no video.

The distinguishing property from the classified policy: environmental_noise (wind /
shadow / camera shake) DOES escalate here, because this mode does not grade motion.
"""
from __future__ import annotations

from pollipi_analysis.policy.three_stage import (
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

PROBE = 5.0


def _motion_controller() -> ThreeStageController:
    return ThreeStageController(
        ThreeStageConfig(
            classify=False,
            low_interval_sec=30.0,
            mid_interval_sec=10.0,
            high_exit_quiet_probes=3,
        )
    )


def test_quiet_stays_normal_at_30s() -> None:
    c = _motion_controller()
    out = c.step(NO_ACTIVITY, 0.0)
    assert out.mode == LOW and out.interval_sec == 30.0
    assert not out.trigger_video


def test_environmental_noise_escalates_unlike_classified_mode() -> None:
    c = _motion_controller()
    out = c.step(ENVIRONMENTAL_NOISE, 0.0)
    assert out.mode == MID and out.interval_sec == 10.0
    assert out.reason == "any_motion_fast"


def test_any_motion_kind_escalates() -> None:
    for state in (ENVIRONMENTAL_NOISE, UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE):
        c = _motion_controller()
        out = c.step(state, 0.0)
        assert out.mode == MID and out.interval_sec == 10.0


def test_never_triggers_video() -> None:
    c = _motion_controller()
    outs = [
        c.step(s, i * PROBE)
        for i, s in enumerate(
            [STRONG_VISITATION_CANDIDATE, STRONG_VISITATION_CANDIDATE, STRONG_VISITATION_CANDIDATE]
        )
    ]
    assert all(not o.trigger_video for o in outs)


def test_settles_back_to_normal_after_quiet_streak() -> None:
    c = _motion_controller()
    c.step(ENVIRONMENTAL_NOISE, 0.0)  # -> MID (fast)
    # Two quiet probes hold fast; the third settles back to LOW.
    a = c.step(NO_ACTIVITY, PROBE)
    b = c.step(NO_ACTIVITY, 2 * PROBE)
    settle = c.step(NO_ACTIVITY, 3 * PROBE)
    assert a.mode == MID and b.mode == MID
    assert settle.mode == LOW and settle.interval_sec == 30.0
    assert settle.reason == "any_motion_settle_to_low"
