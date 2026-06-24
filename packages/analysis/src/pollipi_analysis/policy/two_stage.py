"""Two-stage LOW/HIGH adaptive-interval controller (shared by simulation + Pi).

This is the discrete state machine the project actually wants: stay at a low,
power-saving rate most of the time, and only switch to a short high rate for a
bounded dwell when the mesh decision says it is worth capturing densely. It is
deliberately *not* a confirmed-insect detector — it answers "is it worth
capturing at HIGH right now?" and always falls back to LOW.

Semantics (matching the field intent ``LOW_RATE=30s`` / ``HIGH_RATE=5s`` /
``HIGH hold = 2 min``):

- A capture whose decision state is in ``trigger_states`` (default: only
  ``strong_visitation_candidate``) (re)arms HIGH mode for ``high_hold_sec``.
- While HIGH is armed (now < high_until), the next interval is ``high_rate_sec``.
- Otherwise the next interval is ``low_rate_sec`` and HIGH disarms.

The controller is pure and deterministic given the stream of
``(decision_state, now_sec)`` it is stepped with, so the simulation power model
and the Pi runtime produce identical timing from identical decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE, DecisionState

LOW = "LOW"
HIGH = "HIGH"
Mode = str


@dataclass(frozen=True)
class TwoStageConfig:
    low_rate_sec: float = 30.0
    high_rate_sec: float = 5.0
    high_hold_sec: float = 120.0
    #: Which decision states (re)arm HIGH. Only the strong candidate by default;
    #: uncertain/noise/quiet never trigger HIGH, which is what keeps power low.
    trigger_states: tuple[DecisionState, ...] = (STRONG_VISITATION_CANDIDATE,)

    def __post_init__(self) -> None:
        if not (0 < self.high_rate_sec <= self.low_rate_sec):
            raise ValueError("require 0 < high_rate_sec <= low_rate_sec")
        if self.high_hold_sec < 0:
            raise ValueError("high_hold_sec must be >= 0")


@dataclass(frozen=True)
class TwoStageStep:
    mode: Mode
    interval_sec: float
    high_remaining_sec: float
    triggered: bool
    reason: str


@dataclass
class TwoStageController:
    """Stateful LOW/HIGH controller. Step it once per analysed capture."""

    config: TwoStageConfig = field(default_factory=TwoStageConfig)
    _high_until: Optional[float] = None

    @property
    def mode(self) -> Mode:
        return HIGH if self._high_until is not None else LOW

    def step(self, decision_state: DecisionState, now_sec: float) -> TwoStageStep:
        """Return the interval to use for the NEXT capture given this decision.

        ``now_sec`` is the capture time on a monotonic clock (any consistent unit
        of seconds). A trigger state (re)arms HIGH; an expired hold falls back to
        LOW. The returned ``interval_sec`` is the gap until the next capture.
        """
        cfg = self.config
        triggered = decision_state in cfg.trigger_states
        if triggered:
            self._high_until = now_sec + cfg.high_hold_sec

        if self._high_until is not None and now_sec < self._high_until:
            remaining = self._high_until - now_sec
            reason = "high_triggered" if triggered else "high_hold"
            return TwoStageStep(HIGH, cfg.high_rate_sec, remaining, triggered, reason)

        # Hold expired (or never armed): disarm and return to LOW.
        self._high_until = None
        return TwoStageStep(LOW, cfg.low_rate_sec, 0.0, False, "low_rate")
