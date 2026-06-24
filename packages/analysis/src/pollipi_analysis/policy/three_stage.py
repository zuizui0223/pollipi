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

from dataclasses import dataclass, field
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

_LOCAL_CANDIDATES = frozenset({UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE})
_QUIET = frozenset({NO_ACTIVITY, ENVIRONMENTAL_NOISE})


@dataclass(frozen=True)
class ThreeStageConfig:
    low_interval_sec: float = 30.0
    mid_interval_sec: float = 15.0
    high_interval_sec: float = 5.0
    high_hard_cap_sec: float = 120.0
    high_exit_quiet_probes: int = 3


@dataclass
class ThreeStageState:
    mode: Mode = LOW
    local_candidate_streak: int = 0
    streak_has_strong: bool = False
    quiet_streak: int = 0
    high_entered_at: Optional[float] = None


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
        self.state.high_entered_at = None

    def _interval_for(self, mode: Mode) -> float:
        cfg = self.config
        return {LOW: cfg.low_interval_sec, MID: cfg.mid_interval_sec, HIGH: cfg.high_interval_sec}[mode]

    def step(self, decision_state: DecisionState, now_sec: float) -> ThreeStageOutput:
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
