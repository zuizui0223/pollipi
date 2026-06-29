"""Video-HIGH mode: strong local activity fires one clip event, then MID, with cooldown.

A clip is never a confirmed visit; environmental noise must never fire one.
"""
from __future__ import annotations

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

PROBE = 5.0


def _video_controller() -> ThreeStageController:
    return ThreeStageController(
        ThreeStageConfig(
            low_interval_sec=30.0,
            mid_interval_sec=10.0,
            high_mode="video",
            video_duration_sec=30.0,
            video_fps=30,
            video_cooldown_sec=45.0,
        )
    )


def _run(controller, states_with_times):
    return [controller.step(s, now) for s, now in states_with_times]


def test_mid_interval_is_10s_in_video_mode() -> None:
    c = _video_controller()
    out = c.step(UNCERTAIN_LOCAL_ACTIVITY, 0.0)
    assert out.mode == MID and out.interval_sec == 10.0
    assert not out.trigger_video


def test_noise_never_triggers_video() -> None:
    c = _video_controller()
    outs = _run(
        c,
        [(ENVIRONMENTAL_NOISE, t * PROBE) for t in range(6)]
        + [(NO_ACTIVITY, 6 * PROBE)],
    )
    assert all(not o.trigger_video for o in outs)
    assert all(o.mode == LOW for o in outs)


def test_two_local_with_strong_fires_one_clip_then_returns_to_mid() -> None:
    c = _video_controller()
    # LOW -> MID (uncertain), then a strong on the next probe = 2 consecutive incl strong.
    o0 = c.step(UNCERTAIN_LOCAL_ACTIVITY, 0.0)
    o1 = c.step(STRONG_VISITATION_CANDIDATE, PROBE)
    assert not o0.trigger_video and o0.mode == MID
    assert o1.trigger_video is True
    assert o1.mode == HIGH  # firing probe reports HIGH for the log
    assert o1.reason == "video_trigger_two_local_with_strong"
    # After the clip the controller is back in MID (next quiet-ish probe shows MID/LOW).
    o2 = c.step(UNCERTAIN_LOCAL_ACTIVITY, PROBE + 30.0)
    assert o2.mode == MID and not o2.trigger_video


def test_uncertain_only_never_fires_without_strong() -> None:
    c = _video_controller()
    outs = _run(c, [(UNCERTAIN_LOCAL_ACTIVITY, t * PROBE) for t in range(5)])
    assert all(not o.trigger_video for o in outs)
    assert all(o.mode == MID for o in outs)  # holds in MID, never escalates to a clip


def test_cooldown_blocks_second_clip_then_allows_after_window() -> None:
    c = _video_controller()
    c.step(UNCERTAIN_LOCAL_ACTIVITY, 0.0)
    fire = c.step(STRONG_VISITATION_CANDIDATE, PROBE)
    assert fire.trigger_video
    # cooldown_until = PROBE + 30 (clip) + 45 (cooldown) = 80.0
    # Sustained strong inside the cooldown window: suppressed, no second clip.
    suppressed = [
        c.step(STRONG_VISITATION_CANDIDATE, t)
        for t in (40.0, 60.0, 75.0)
    ]
    assert all(not o.trigger_video for o in suppressed)
    assert all(o.cooldown_active for o in suppressed)
    assert any("cooldown" in o.reason for o in suppressed)
    # Quiet resets the streak, then a fresh 2-consecutive-with-strong after the
    # cooldown window (ends at 80.0) fires a second clip.
    c.step(NO_ACTIVITY, 85.0)
    c.step(UNCERTAIN_LOCAL_ACTIVITY, 90.0)
    again = c.step(STRONG_VISITATION_CANDIDATE, 95.0)
    assert again.trigger_video is True  # firing here proves the cooldown had cleared


def test_cooldown_remaining_decreases() -> None:
    c = _video_controller()
    c.step(UNCERTAIN_LOCAL_ACTIVITY, 0.0)
    fire = c.step(STRONG_VISITATION_CANDIDATE, PROBE)  # cooldown_until = 80.0
    assert fire.trigger_video
    a = c.step(NO_ACTIVITY, 50.0)
    b = c.step(NO_ACTIVITY, 70.0)
    assert a.cooldown_remaining_sec > b.cooldown_remaining_sec > 0.0


def test_interval_mode_unchanged_default() -> None:
    # Default config (interval mode) still bursts to HIGH/5s, no video fields set.
    c = ThreeStageController()
    c.step(UNCERTAIN_LOCAL_ACTIVITY, 0.0)
    out = c.step(STRONG_VISITATION_CANDIDATE, PROBE)
    assert out.mode == HIGH and out.interval_sec == 5.0
    assert out.trigger_video is False
