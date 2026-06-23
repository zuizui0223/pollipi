"""Shared centroid-track helper used by BOTH the PC simulation and the Pi runtime.

The single most important Phase 1 guarantee is that the Pi and the development
simulation compute the *same* feature vector from the *same* sequence of frames.
Per-frame-pair features already share :func:`pollipi_analysis.pipeline.analyze`.
The trajectory features (``path_efficiency`` / ``mean_step`` / ``reversal_rate``)
need a short window of centroids, so they were previously computed only inside
the shadow runner — which meant the Pi never populated them and therefore ran on
a *different* feature space from the simulation.

This module hoists that windowed computation into one place. The shadow runner
(``pollipi_analysis.shadow``) and the Pi capture loop both drive a :class:`Tracker`,
so a given frame sequence yields byte-for-byte identical features and decisions
regardless of where it runs. It is pure and stdlib + numpy only, so importing it
on the Pi pulls in no simulation dependencies.

The ``max`` / ``q90`` / ``q95`` upper-tail aggregation features are already
emitted identically by :func:`pollipi_analysis.features.compute.compute_features`
on both sides; they remain shadow-logged only (the active classifier does not
read them yet) until real-image shadow A/B validates them.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from pollipi_analysis.pipeline import PipelineConfig, analyze
from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.states import ENVIRONMENTAL_NOISE, STRONG_VISITATION_CANDIDATE

#: Default number of recent centroids retained for trajectory features.
DEFAULT_TRACK_WINDOW = 6

#: A directed traverse keeps net/path near 1; oscillating sway drops well below.
TRACK_PATH_EFFICIENCY_FLOOR = 0.45


def trajectory_features(
    centroids: Sequence[Optional[tuple[float, float]]],
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return ``(path_efficiency, mean_step, reversal_rate)`` over the track window.

    - ``path_efficiency``: net / total path length — ~1.0 for a directed traverse,
      ~0 for back-and-forth sway.
    - ``mean_step``: average centroid displacement between consecutive frames.
    - ``reversal_rate``: fraction of consecutive step-vector pairs that reverse
      direction (negative dot product) — high for oscillation.

    These are logged in shadow mode only; they do not drive the active decision
    except via :func:`apply_track_evidence`, which can only *downgrade* a strong
    candidate revealed to be oscillation.
    """
    pts = [p for p in centroids if p is not None]
    if len(pts) < 2:
        return None, None, None
    vectors = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    steps = [math.hypot(vx, vy) for vx, vy in vectors]
    mean_step = sum(steps) / len(steps)
    total = sum(steps)
    if total <= 1e-6:
        path_eff = 0.0
    else:
        net = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        path_eff = float(net / total)
    rev_den = 0
    rev = 0
    for a, b in zip(vectors, vectors[1:]):
        if math.hypot(*a) > 1e-8 and math.hypot(*b) > 1e-8:
            rev_den += 1
            if (a[0] * b[0] + a[1] * b[1]) < 0:
                rev += 1
    reversal_rate = (rev / rev_den) if rev_den else 0.0
    return path_eff, float(mean_step), float(reversal_rate)


def apply_track_evidence(decision: MeshDecision, path_efficiency: float, window_len: int) -> MeshDecision:
    """Downgrade a strong candidate that the track reveals to be oscillation.

    A single frame pair cannot tell a directed visitor from a swaying leaf; only
    several captures of low path efficiency can. Once the track window has enough
    points, a strong candidate with low path efficiency is reclassified as
    oscillation-driven environmental noise. This is the one place trajectory
    evidence affects the decision, and it only ever *reduces* HIGH-rate triggers.
    """
    if (
        decision.state == STRONG_VISITATION_CANDIDATE
        and window_len >= 3
        and path_efficiency < TRACK_PATH_EFFICIENCY_FLOOR
    ):
        return dataclasses.replace(
            decision, state=ENVIRONMENTAL_NOISE, reason="low_path_efficiency_oscillation"
        )
    return decision


def centroid_xy(decision: MeshDecision) -> Optional[tuple[float, float]]:
    f = decision.features
    if f.centroid_x is None or f.centroid_y is None:
        return None
    return (f.centroid_x, f.centroid_y)


def with_trajectory(
    decision: MeshDecision,
    path_efficiency: Optional[float],
    mean_step: Optional[float],
    reversal_rate: Optional[float],
    track_frames: int,
) -> MeshDecision:
    features = dataclasses.replace(
        decision.features,
        path_efficiency=path_efficiency,
        mean_step=mean_step,
        reversal_rate=reversal_rate,
        track_frames=track_frames,
    )
    return dataclasses.replace(decision, features=features)


@dataclass
class Tracker:
    """Stateful driver that turns a stream of frame pairs into trajectory-aware decisions.

    Drive it one analysed frame at a time with :meth:`observe`. It maintains the
    centroid ring buffer and the previous-frame active cells / centroid needed for
    persistence and displacement, then attaches the windowed trajectory features
    and applies the oscillation downgrade. Both the simulation shadow runner and
    the Pi capture loop use this so they stay on an identical feature space.
    """

    track_window: int = DEFAULT_TRACK_WINDOW
    config: Optional[PipelineConfig] = None
    previous_active: Optional[set[tuple[int, int]]] = None
    previous_centroid: Optional[tuple[float, float]] = None
    _centroids: list[tuple[float, float]] = field(default_factory=list)

    def observe(self, frame, background, *, config: Optional[PipelineConfig] = None) -> MeshDecision:
        """Analyse one frame against its background and return a trajectory-aware decision."""
        cfg = config or self.config
        decision = analyze(
            frame,
            background,
            config=cfg,
            previous_active_cells=self.previous_active,
            previous_centroid=self.previous_centroid,
        )

        centroid = centroid_xy(decision)
        if centroid is not None:
            self._centroids.append(centroid)
            self._centroids[:] = self._centroids[-self.track_window:]
        path_eff, mean_step, reversal_rate = trajectory_features(self._centroids)
        decision = with_trajectory(decision, path_eff, mean_step, reversal_rate, len(self._centroids))
        if path_eff is not None:
            decision = apply_track_evidence(decision, path_eff, len(self._centroids))

        self.previous_active = set(decision.active_cells)
        self.previous_centroid = centroid
        return decision

    @property
    def track_frames(self) -> int:
        return len(self._centroids)
