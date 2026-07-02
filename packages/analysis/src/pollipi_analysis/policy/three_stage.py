"""Probe-only three-stage adaptive shadow controller (Issue #27).

A pure, hardware-independent state machine that maps a stream of mesh decision
states (one per low-resolution probe) to a *would-be* capture mode — LOW / MID /
HIGH — without ever changing real capture timing. It is the shared logic run by
both the Pi runtime and the simulation, so they produce identical transitions for
the same decision sequence.

Modes / intervals:
- LOW  = 30 s (quiet / environmental noise)
- MID  = 15 s (one local candidate)
- HIGH =  5 s (confirmed strong visitation candidate)

Transition rules:
- LOW  -> MID : one local candidate (uncertain OR strong)
- MID  -> HIGH: two consecutive local candidates with at least one being strong
- MID  -> LOW : quiet or environmental-noise probe
- HIGH -> LOW : three consecutive quiet/noise probes
- HIGH -> LOW : hard cap 120 s after entry (later strong candidates do NOT extend it)

This controller never enables live adaptive capture; the caller logs the would-be
mode in shadow mode only. A mesh state is never a confirmed pollinator visit.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    DecisionState,
)

LOW = "LOW"
MID = "MID"
HIGH = "HIGH"
Mode = str

# Mode ordering for capture-on-escalation: the instant activity raises the mode,
# a still is grabbed immediately (see ThreeStageController.step / force_capture).
_MODE_RANK = {LOW: 0, MID: 1, HIGH: 2}

_LOCAL_CANDIDATES = frozenset({UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE})
_QUIET = frozenset({NO_ACTIVITY, ENVIRONMENTAL_NOISE})


@dataclass(frozen=True)
class ThreeStageConfig:
    low_interval_sec: float = 30.0
    mid_interval_sec: float = 15.0
    high_interval_sec: float = 5.0
    high_hard_cap_sec: float = 120.0
    high_exit_quiet_probes: int = 3
    # HIGH behaviour: "interval" (default, the original 5 s burst-of-stills mode) or
    # "video" (fire one high-info video clip, then fall back to MID, with cooldown).
    high_mode: str = "interval"
    video_duration_sec: float = 30.0
    video_fps: int = 30
    video_cooldown_sec: float = 45.0
    # A target in wind produces isolated candidate frames separated by ~2
    # environmental_noise probes; tolerate this many intervening non-candidate
    # probes within a run before the two-candidate video streak resets. 2 recovers
    # wind/wind-shadow visit clips (target video 30->43 of 56) with zero added false
    # video — the trigger still requires a STRONG frame, which noise never produces.
    video_gap_tolerance: int = 2
    # classify=True (default): mesh states are graded; environmental_noise is treated
    # as quiet (mode ③ / the classified stills policy). classify=False (mode ②): any
    # motion at all — wind, shadow, insect alike — escalates to the fast interval;
    # there is no HIGH and no video. Two levels only: low_interval <-> mid_interval.
    classify: bool = True


@dataclass
class ThreeStageState:
    mode: Mode = LOW
    local_candidate_streak: int = 0
    streak_has_strong: bool = False
    quiet_streak: int = 0
    high_entered_at: Optional[float] = None
    # video mode: intervening non-candidate probes tolerated within a candidate run.
    gap_streak: int = 0
    # video mode: re-trigger is blocked until this time (now + clip + cooldown).
    cooldown_until: float = 0.0


@dataclass(frozen=True)
class ThreeStageOutput:
    mode: Mode
    interval_sec: float
    reason: str
    local_candidate_streak: int
    quiet_streak: int
    high_elapsed_sec: float
    high_remaining_sec: float
    entered_high: bool
    exited_high: bool
    # video mode only (interval mode leaves these at their defaults):
    trigger_video: bool = False
    cooldown_active: bool = False
    cooldown_remaining_sec: float = 0.0
    # capture-on-escalation: True on the probe where the mode first rises (activity
    # detected). The scheduler grabs a still immediately instead of waiting out the
    # interval, so a short visit's entry frame is never missed.
    force_capture: bool = False


class ThreeStageController:
    """Stateful three-stage controller. Feed one probe decision at a time."""

    def __init__(self, config: Optional[ThreeStageConfig] = None) -> None:
        self.config = config or ThreeStageConfig()
        self.state = ThreeStageState()

    def _to_low(self) -> None:
        self.state.mode = LOW
        self.state.local_candidate_streak = 0
        self.state.streak_has_strong = False
        self.state.quiet_streak = 0
        self.state.gap_streak = 0
        self.state.high_entered_at = None

    def _interval_for(self, mode: Mode) -> float:
        cfg = self.config
        return {LOW: cfg.low_interval_sec, MID: cfg.mid_interval_sec, HIGH: cfg.high_interval_sec}[mode]

    def step(self, decision_state: DecisionState, now_sec: float) -> ThreeStageOutput:
        prev_mode = self.state.mode
        if not self.config.classify:
            out = self._step_any_motion(decision_state, now_sec)
        elif self.config.high_mode == "video":
            out = self._step_video(decision_state, now_sec)
        else:
            out = self._step_interval(decision_state, now_sec)
        # Capture-on-escalation: the moment activity raises the mode (LOW->MID or
        # ->HIGH), grab a still immediately rather than waiting out the interval, so
        # a short visit's entry is never missed. Not on a video-trigger probe (the
        # clip is that probe's record). Shared by the Pi runtime and the simulation.
        if (
            not out.force_capture
            and not out.trigger_video
            and _MODE_RANK.get(out.mode, 0) > _MODE_RANK.get(prev_mode, 0)
        ):
            out = replace(out, force_capture=True)
        return out

    def _step_any_motion(self, decision_state: DecisionState, now_sec: float) -> ThreeStageOutput:
        """Mode ②: any motion (noise included) -> fast interval; settle back when quiet.

        No grading, no HIGH, no video. Two levels only: MID = mid_interval_sec (fast)
        while anything moves, LOW = low_interval_sec (normal) once it has been quiet
        for high_exit_quiet_probes in a row.
        """
        cfg = self.config
        st = self.state
        is_motion = decision_state != NO_ACTIVITY  # wind/shadow count as motion here

        if is_motion:
            st.mode = MID
            st.quiet_streak = 0
            reason = "any_motion_fast"
        else:
            st.quiet_streak += 1
            if st.mode == MID and st.quiet_streak >= cfg.high_exit_quiet_probes:
                st.mode = LOW
                reason = "any_motion_settle_to_low"
            elif st.mode == MID:
                reason = f"any_motion_hold_fast_quiet_{st.quiet_streak}"
            else:
                reason = "any_motion_low"

        return ThreeStageOutput(
            mode=st.mode,
            interval_sec=self._interval_for(st.mode),
            reason=reason,
            local_candidate_streak=0,
            quiet_streak=st.quiet_streak,
            high_elapsed_sec=0.0,
            high_remaining_sec=0.0,
            entered_high=False,
            exited_high=False,
        )

    def _step_video(self, decision_state: DecisionState, now_sec: float) -> ThreeStageOutput:
        """Video HIGH: mode is only LOW/MID; HIGH is an instantaneous clip event.

        On the firing probe the output reports mode=HIGH and trigger_video=True; the
        caller records one clip then resumes. A cooldown (clip + video_cooldown_sec)
        blocks re-triggering. environmental_noise / no_activity never trigger a clip.
        """
        cfg = self.config
        st = self.state
        is_local = decision_state in _LOCAL_CANDIDATES
        is_strong = decision_state == STRONG_VISITATION_CANDIDATE
        trigger_video = False

        if st.mode == MID:
            if not is_local:
                st.gap_streak += 1
                if st.gap_streak > cfg.video_gap_tolerance:
                    self._to_low()
                    reason = "mid_to_low_quiet_or_noise"
                else:
                    # Hold MID across a brief disturbance gap so a wind-buffeted
                    # target's isolated candidate frames can still reach the trigger.
                    reason = f"mid_hold_gap_{st.gap_streak}"
            else:
                st.gap_streak = 0
                st.local_candidate_streak += 1
                st.streak_has_strong = st.streak_has_strong or is_strong
                st.quiet_streak = 0
                if st.local_candidate_streak >= 2 and st.streak_has_strong:
                    if now_sec < st.cooldown_until:
                        remaining = st.cooldown_until - now_sec
                        reason = f"video_suppressed_cooldown_{remaining:.0f}s"
                    else:
                        trigger_video = True
                        st.cooldown_until = now_sec + cfg.video_duration_sec + cfg.video_cooldown_sec
                        # Stay in MID after the clip; clear the streak so the next probe
                        # does not immediately re-arm before fresh evidence.
                        st.local_candidate_streak = 0
                        st.streak_has_strong = False
                        reason = "video_trigger_two_local_with_strong"
                else:
                    reason = f"mid_hold_local_streak_{st.local_candidate_streak}"
        else:  # LOW
            if is_local:
                st.mode = MID
                st.local_candidate_streak = 1
                st.streak_has_strong = is_strong
                st.quiet_streak = 0
                reason = "low_to_mid_local_candidate"
            else:
                st.quiet_streak += 1
                st.local_candidate_streak = 0
                st.streak_has_strong = False
                reason = "low_hold_quiet"

        # Report HIGH only on the firing probe; otherwise the post-transition LOW/MID.
        out_mode = HIGH if trigger_video else st.mode
        cooldown_active = now_sec < st.cooldown_until
        cooldown_remaining = max(0.0, st.cooldown_until - now_sec)
        return ThreeStageOutput(
            mode=out_mode,
            interval_sec=self._interval_for(st.mode),
            reason=reason,
            local_candidate_streak=st.local_candidate_streak,
            quiet_streak=st.quiet_streak,
            high_elapsed_sec=0.0,
            high_remaining_sec=0.0,
            entered_high=trigger_video,
            exited_high=False,
            trigger_video=trigger_video,
            cooldown_active=cooldown_active,
            cooldown_remaining_sec=cooldown_remaining,
        )

    def _step_interval(self, decision_state: DecisionState, now_sec: float) -> ThreeStageOutput:
        cfg = self.config
        st = self.state
        is_local = decision_state in _LOCAL_CANDIDATES
        is_strong = decision_state == STRONG_VISITATION_CANDIDATE
        entered_high = False
        exited_high = False

        if st.mode == HIGH:
            elapsed = now_sec - (st.high_entered_at if st.high_entered_at is not None else now_sec)
            if elapsed >= cfg.high_hard_cap_sec:
                self._to_low()
                exited_high = True
                reason = "high_hard_cap_120s"
            elif not is_local:
                st.quiet_streak += 1
                st.local_candidate_streak = 0
                st.streak_has_strong = False
                if st.quiet_streak >= cfg.high_exit_quiet_probes:
                    self._to_low()
                    exited_high = True
                    reason = "high_three_quiet_probes"
                else:
                    reason = f"high_hold_quiet_{st.quiet_streak}"
            else:
                # Strong/uncertain keeps us in HIGH but does NOT extend the cap.
                st.quiet_streak = 0
                reason = "high_hold_local"
        elif st.mode == MID:
            if not is_local:
                self._to_low()
                reason = "mid_to_low_quiet_or_noise"
            else:
                st.local_candidate_streak += 1
                st.streak_has_strong = st.streak_has_strong or is_strong
                st.quiet_streak = 0
                if st.local_candidate_streak >= 2 and st.streak_has_strong:
                    st.mode = HIGH
                    st.high_entered_at = now_sec
                    entered_high = True
                    reason = "mid_to_high_two_local_with_strong"
                else:
                    reason = f"mid_hold_local_streak_{st.local_candidate_streak}"
        else:  # LOW
            if is_local:
                st.mode = MID
                st.local_candidate_streak = 1
                st.streak_has_strong = is_strong
                st.quiet_streak = 0
                reason = "low_to_mid_local_candidate"
            else:
                st.quiet_streak += 1
                st.local_candidate_streak = 0
                st.streak_has_strong = False
                reason = "low_hold_quiet"

        if st.mode == HIGH and st.high_entered_at is not None:
            high_elapsed = now_sec - st.high_entered_at
            high_remaining = max(0.0, cfg.high_hard_cap_sec - high_elapsed)
        else:
            high_elapsed = 0.0
            high_remaining = 0.0

        return ThreeStageOutput(
            mode=st.mode,
            interval_sec=self._interval_for(st.mode),
            reason=reason,
            local_candidate_streak=st.local_candidate_streak,
            quiet_streak=st.quiet_streak,
            high_elapsed_sec=high_elapsed,
            high_remaining_sec=high_remaining,
            entered_high=entered_high,
            exited_high=exited_high,
        )
