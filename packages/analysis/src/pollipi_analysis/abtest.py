"""Shadow-mode A/B comparison of two mesh policies (Issue #21, Phase E).

Runs two policy configurations over the SAME sequence of (real or synthetic)
scheduled frames and reports how their shadow decisions differ — without ever
changing capture timing. This is the safe way to compare a candidate
``simulation_informed`` policy against the running ``baseline_rule`` policy on
real Pi imagery before adopting it.

Pure: it only replays frames through :func:`run_shadow_mode`. Decode real JPEGs
to numpy arrays on a dev machine before calling this; the Pi never runs it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from pollipi_analysis.pipeline import PipelineConfig
from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.schemas.states import STRONG_VISITATION_CANDIDATE
from pollipi_analysis.shadow import run_shadow_mode


@dataclass(frozen=True)
class ABComparison:
    n_frames: int
    agreement_rate: float
    a_strong: int
    b_strong: int
    # Frames where B would shorten the interval but A would not (B is more
    # aggressive -> more captures/power/review). The key field for adoption.
    b_more_aggressive: int
    a_more_aggressive: int
    disagreements: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_frames": self.n_frames,
            "agreement_rate": self.agreement_rate,
            "a_strong": self.a_strong,
            "b_strong": self.b_strong,
            "b_more_aggressive": self.b_more_aggressive,
            "a_more_aggressive": self.a_more_aggressive,
            "disagreements": self.disagreements,
        }


def compare_policies(
    frames: Iterable,
    *,
    bounds: IntervalBounds,
    config_a: PipelineConfig,
    config_b: PipelineConfig,
    policy_a_name: str = "A",
    policy_b_name: str = "B",
    device_id: str = "",
) -> ABComparison:
    """Replay ``frames`` under both policies and summarise the differences."""
    recs_a = run_shadow_mode(
        frames, bounds=bounds, config=config_a, device_id=device_id, policy_name=policy_a_name
    )
    recs_b = run_shadow_mode(
        frames, bounds=bounds, config=config_b, device_id=device_id, policy_name=policy_b_name
    )

    n = min(len(recs_a), len(recs_b))
    agree = 0
    a_strong = b_strong = b_more = a_more = 0
    disagreements: list[dict[str, Any]] = []
    for ra, rb in zip(recs_a[:n], recs_b[:n]):
        sa, sb = ra.decision.state, rb.decision.state
        a_strong += int(sa == STRONG_VISITATION_CANDIDATE)
        b_strong += int(sb == STRONG_VISITATION_CANDIDATE)
        if sa == sb:
            agree += 1
            continue
        # "more aggressive" == proposes a shorter next interval.
        if rb.would_be_next_interval_sec < ra.would_be_next_interval_sec:
            b_more += 1
        elif ra.would_be_next_interval_sec < rb.would_be_next_interval_sec:
            a_more += 1
        disagreements.append(
            {
                "frame_index": ra.frame_index,
                "captured_at": ra.captured_at,
                "a_state": sa,
                "b_state": sb,
                "a_would_be": ra.would_be_next_interval_sec,
                "b_would_be": rb.would_be_next_interval_sec,
            }
        )

    return ABComparison(
        n_frames=n,
        agreement_rate=(agree / n) if n else 1.0,
        a_strong=a_strong,
        b_strong=b_strong,
        b_more_aggressive=b_more,
        a_more_aggressive=a_more,
        disagreements=disagreements,
    )


def load_frames_from_dir(directory: str, *, limit: Optional[int] = None) -> list:
    """Decode scheduled JPEGs from *directory* into grayscale numpy arrays.

    Dev-machine helper for real-image A/B. Requires Pillow (a dev dependency);
    the Pi runtime never calls this. Frames are returned oldest-first.
    """
    from pathlib import Path

    import numpy as np

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - dev-only path
        raise RuntimeError("load_frames_from_dir requires Pillow on the dev machine") from exc

    paths = sorted(
        (p for p in Path(directory).iterdir() if p.suffix.lower() in {".jpg", ".jpeg"}),
        key=lambda p: p.stat().st_mtime,
    )
    if limit is not None:
        paths = paths[-limit:]
    frames = []
    for path in paths:
        with Image.open(path) as img:
            frames.append(np.asarray(img.convert("L"), dtype=np.float32))
    return frames
