"""Future outbound WebSocket reconnect supervisor primitives.

This module is intentionally not wired into the server yet. It documents and
tests the reconnect policy needed for a future outbound WSS coordinator mode.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class ReconnectPolicy:
    initial_delay_sec: float = 1.0
    max_delay_sec: float = 60.0
    multiplier: float = 1.8
    jitter_fraction: float = 0.2


class WebSocketReconnectSupervisor:
    def __init__(self, policy: ReconnectPolicy | None = None, *, seed: int = 13) -> None:
        self.policy = policy or ReconnectPolicy()
        self.attempt = 0
        self._random = random.Random(seed)

    def record_success(self) -> None:
        self.attempt = 0

    def record_failure(self) -> float:
        self.attempt += 1
        base = min(
            self.policy.max_delay_sec,
            self.policy.initial_delay_sec * (self.policy.multiplier ** max(0, self.attempt - 1)),
        )
        jitter = base * self.policy.jitter_fraction * self._random.random()
        return min(self.policy.max_delay_sec, base + jitter)
