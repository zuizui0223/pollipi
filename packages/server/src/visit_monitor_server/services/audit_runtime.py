"""Shadow-only probability audit helpers for PolliPi probe streams.

The hash sampler intentionally matches ``v3.audit_sampling`` so a frozen seed,
opportunity ID and stratum probabilities produce the same inclusion decision in
both repositories.  This module does not change capture timing or classify truth.

``AuditWindowCoordinator`` is an in-memory coordinator for centred odd-length probe
windows.  It stores opaque primary/reference objects, emits a complete window only
after the required future probes exist, preserves overlapping audit centres, and
reports included centres that remain incomplete at run edges.
"""
from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from typing import Generic, Hashable, TypeVar

P = TypeVar("P")
R = TypeVar("R")


@dataclass(frozen=True)
class AuditDraw:
    opportunity_id: str
    selected: bool
    included: bool
    inclusion_probability: float
    stratum: str
    uniform_draw: float


@dataclass(frozen=True)
class AuditProbeSample(Generic[P, R]):
    opportunity_id: str
    probe_timestamp: str
    primary: P
    reference: R
    selected: bool
    audit_included: bool
    inclusion_probability: float


@dataclass(frozen=True)
class CompletedAuditWindow(Generic[P, R]):
    centre_opportunity_id: str
    samples: tuple[AuditProbeSample[P, R], ...]


def _validate_probability(value: float, *, name: str) -> float:
    probability = float(value)
    if not math.isfinite(probability) or probability <= 0.0 or probability > 1.0:
        raise ValueError(f"{name} must satisfy 0 < p <= 1")
    return probability


def deterministic_uniform(opportunity_id: str, *, seed: str) -> float:
    """Match ``v3.audit_sampling.deterministic_uniform`` exactly."""

    if not opportunity_id:
        raise ValueError("opportunity_id must be non-empty")
    if not seed:
        raise ValueError("seed must be non-empty")
    payload = f"{seed}\x1f{opportunity_id}".encode("utf-8")
    integer = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)
    return integer / 2**64


def audit_draw(
    opportunity_id: str,
    *,
    selected: bool,
    seed: str,
    q_selected: float,
    q_omitted: float,
) -> AuditDraw:
    """Return one policy-independent/reweighted audit draw.

    Equal ``q_selected`` and ``q_omitted`` yield inclusion independent of the
    operational selection stratum. Unequal rates remain valid only because both are
    strictly positive and the chosen probability is retained with the draw.
    """

    q1 = _validate_probability(q_selected, name="q_selected")
    q0 = _validate_probability(q_omitted, name="q_omitted")
    probability = q1 if selected else q0
    uniform = deterministic_uniform(opportunity_id, seed=seed)
    return AuditDraw(
        opportunity_id=opportunity_id,
        selected=bool(selected),
        included=uniform < probability,
        inclusion_probability=probability,
        stratum="selected" if selected else "omitted",
        uniform_draw=uniform,
    )


class AuditWindowCoordinator(Generic[P, R]):
    """Emit centred complete windows without altering the probe stream.

    The coordinator accepts every probe in temporal order. Once ``window_size``
    probes are available, the middle sample is the only newly eligible centre. If
    that centre's independent audit draw is included, the whole window is emitted.
    Included centres near the run boundaries remain listed as incomplete rather
    than being silently deleted.
    """

    def __init__(self, window_size: int = 9) -> None:
        if isinstance(window_size, bool) or not isinstance(window_size, int):
            raise ValueError("window_size must be an odd integer >= 3")
        if window_size < 3 or window_size % 2 != 1:
            raise ValueError("window_size must be an odd integer >= 3")
        self.window_size = window_size
        self.half_window = window_size // 2
        self._buffer: deque[AuditProbeSample[P, R]] = deque(maxlen=window_size)
        self._seen_ids: set[str] = set()
        self._included_ids: set[str] = set()
        self._completed_ids: set[str] = set()

    def add(self, sample: AuditProbeSample[P, R]) -> CompletedAuditWindow[P, R] | None:
        if not sample.opportunity_id:
            raise ValueError("opportunity_id must be non-empty")
        if sample.opportunity_id in self._seen_ids:
            raise ValueError(f"duplicate opportunity_id: {sample.opportunity_id}")
        if not math.isfinite(float(sample.inclusion_probability)) or not (
            0.0 < float(sample.inclusion_probability) <= 1.0
        ):
            raise ValueError("inclusion_probability must satisfy 0 < p <= 1")

        self._seen_ids.add(sample.opportunity_id)
        if sample.audit_included:
            self._included_ids.add(sample.opportunity_id)
        self._buffer.append(sample)

        if len(self._buffer) < self.window_size:
            return None

        rows = tuple(self._buffer)
        centre = rows[self.half_window]
        if not centre.audit_included:
            return None
        if centre.opportunity_id in self._completed_ids:
            raise AssertionError("audit centre emitted more than once")
        self._completed_ids.add(centre.opportunity_id)
        return CompletedAuditWindow(
            centre_opportunity_id=centre.opportunity_id,
            samples=rows,
        )

    @property
    def incomplete_included_centres(self) -> tuple[str, ...]:
        return tuple(sorted(self._included_ids - self._completed_ids))

    @property
    def completed_centres(self) -> tuple[str, ...]:
        return tuple(sorted(self._completed_ids))
