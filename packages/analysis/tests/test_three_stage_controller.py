"""Issue #27: the eight required scenarios for the three-stage probe controller."""
from __future__ import annotations

from pollipi_analysis.policy.three_stage import (
    HIGH,
    LOW,
    MID,
    ThreeStageController,
)
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)

PROBE = 5.0  # low-resolution probe interval (seconds)


def _run(states):
    """Feed a list of decision states at 5 s probe spacing; return mode trace."""
    c = ThreeStageController()
    trace = []
    for i, s in enumerate(states):
        out = c.step(s, now_sec=i * PROBE)
        trace.append(out)
    return trace


def test_quiet_and_noise_stay_low_at_30s() -> None:
    trace = _run([NO_ACTIVITY, ENVIRONMENTAL_NOISE, NO_ACTIVITY, ENVIRONMENTAL_NOISE])
    assert all(o.mode == LOW and o.interval_sec == 30.0 for o in trace)


def test_one_uncertain_triggers_mid_at_15s() -> None:
    out = _run([NO_ACTIVITY, UNCERTAIN_LOCAL_ACTIVITY])[-1]
    assert out.mode == MID and out.interval_sec == 15.0
    assert out.reason == "low_to_mid_local_candidate"


def test_uncertain_then_uncertain_stays_mid_never_high_alone() -> None:
    trace = _run([UNCERTAIN_LOCAL_ACTIVITY, UNCERTAIN_LOCAL_ACTIVITY, UNCERTAIN_LOCAL_ACTIVITY])
    assert [o.mode for o in trace] == [MID, MID, MID]


def test_uncertain_then_strong_enters_high_at_5s() -> None:
    trace = _run([UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE])
    assert trace[-1].mode == HIGH and trace[-1].interval_sec == 5.0
    assert trace[-1].entered_high is True


def test_strong_then_strong_enters_high() -> None:
    trace = _run([STRONG_VISITATION_CANDIDATE, STRONG_VISITATION_CANDIDATE])
    assert trace[-1].mode == HIGH and trace[-1].interval_sec == 5.0


def test_three_consecutive_quiet_returns_high_to_low() -> None:
    states = [
        UNCERTAIN_LOCAL_ACTIVITY,        # LOW -> MID
        STRONG_VISITATION_CANDIDATE,     # MID -> HIGH
        NO_ACTIVITY,                     # HIGH quiet 1
        ENVIRONMENTAL_NOISE,             # HIGH quiet 2
        NO_ACTIVITY,                     # HIGH quiet 3 -> LOW
    ]
    trace = _run(states)
    assert trace[1].mode == HIGH
    assert trace[-1].mode == LOW
    assert trace[-1].exited_high is True
    assert trace[-1].reason == "high_three_quiet_probes"


def test_repeated_strong_never_extends_120s_hard_cap() -> None:
    # Enter HIGH then feed strong probes forever; must exit at the 120 s cap.
    states = [UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE] + [STRONG_VISITATION_CANDIDATE] * 40
    c = ThreeStageController()
    entered_at = None
    exit_time = None
    for i, s in enumerate(states):
        out = c.step(s, now_sec=i * PROBE)
        if out.entered_high:
            entered_at = i * PROBE
        if out.exited_high:
            exit_time = i * PROBE
            break
    assert entered_at is not None and exit_time is not None
    assert exit_time - entered_at == 120.0  # hard cap, not extended by strongs
    assert out.reason == "high_hard_cap_120s"


def test_probe_only_adds_low_res_decisions_without_extra_high_res_saves() -> None:
    # 30 s of probing at 5 s = 6 probes (low-res decisions), while high-res saves
    # remain fixed at one per 30 s. The controller produces a decision per probe
    # and never asks to save a high-res frame.
    states = [NO_ACTIVITY] * 6
    trace = _run(states)
    assert len(trace) == 6  # six low-res probe decisions in one 30 s window
    # High-res cadence is the caller's fixed 30 s clock; the controller exposes
    # only the would-be interval and never forces a save.
    assert all(o.mode == LOW for o in trace)


def test_pi_and_simulation_share_identical_transitions() -> None:
    # Two independent controllers (one would be the Pi, one the simulator) must
    # produce identical mode traces for the same decision + time sequence.
    seq = [
        NO_ACTIVITY, UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE,
        STRONG_VISITATION_CANDIDATE, ENVIRONMENTAL_NOISE, NO_ACTIVITY,
        NO_ACTIVITY, UNCERTAIN_LOCAL_ACTIVITY,
    ]
    pi, sim = ThreeStageController(), ThreeStageController()
    pi_trace = [pi.step(s, now_sec=i * PROBE).mode for i, s in enumerate(seq)]
    sim_trace = [sim.step(s, now_sec=i * PROBE).mode for i, s in enumerate(seq)]
    assert pi_trace == sim_trace


# --- capture-on-escalation (force_capture) -----------------------------------

def test_force_capture_fires_on_mode_escalation_only() -> None:
    c = ThreeStageController()
    # LOW -> LOW (quiet): no escalation, no forced capture.
    assert c.step(NO_ACTIVITY, 0.0).force_capture is False
    # LOW -> MID (local candidate): escalation -> forced capture.
    up = c.step(UNCERTAIN_LOCAL_ACTIVITY, PROBE)
    assert up.mode == MID and up.force_capture is True
    # MID hold (still local): no further escalation.
    assert c.step(UNCERTAIN_LOCAL_ACTIVITY, 2 * PROBE).force_capture is False
    # MID -> HIGH (two local incl. strong): escalation -> forced capture.
    hi = c.step(STRONG_VISITATION_CANDIDATE, 3 * PROBE)
    assert hi.mode == HIGH and hi.force_capture is True
    # HIGH hold: no escalation.
    assert c.step(STRONG_VISITATION_CANDIDATE, 4 * PROBE).force_capture is False


def test_force_capture_not_set_on_a_video_trigger_probe() -> None:
    from pollipi_analysis.policy.three_stage import ThreeStageConfig
    c = ThreeStageController(ThreeStageConfig(high_mode="video"))
    c.step(UNCERTAIN_LOCAL_ACTIVITY, 0.0)          # LOW -> MID (forces a still)
    out = c.step(STRONG_VISITATION_CANDIDATE, PROBE)  # two local incl. strong -> clip
    assert out.trigger_video is True
    assert out.force_capture is False              # the clip is the record, not a still
