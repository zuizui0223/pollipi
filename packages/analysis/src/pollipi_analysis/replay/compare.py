"""Counterfactual replay of capture policies ①②③ over one recorded probe log.

Reads a per-run v2 probe-shadow log (``adaptive_probe_shadow_v2_<run_id>.csv``)
and, for the SAME recorded decision-state sequence, computes what each capture
policy would have done on that identical field record:

  ① fixed      — a plain fixed-interval timelapse (no adaptation)
  ② any-motion — faster stills whenever ANY motion is seen (wind/shadow/insect)
  ③ classified — noise filtered; local candidate -> faster; strong -> video clip

For each policy it reports the capture COST (stills, video clips + seconds,
estimated storage) and — when a visit-annotation file is supplied — the visit
CAPTURE RATE and mean latency. This is the offline evaluation for the study:
show that ③ sits between ①'s missed short visits and ②'s wind/shadow-driven
wasted captures, i.e. the best capture-rate vs storage/energy balance.

The decision states are read from the field log, but every policy is replayed
through the SAME :class:`ThreeStageController` the Pi runs, so the control logic
is byte-for-byte identical to production — only the input sequence is real.

Pure stdlib + the shared controller; no numpy/pandas, so it stays importable in
the same light environment as the rest of ``pollipi_analysis``.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from pollipi_analysis.policy.three_stage import ThreeStageConfig, ThreeStageController
from pollipi_analysis.schemas.states import NO_ACTIVITY


# ---------------------------------------------------------------------------
# Probe-log reading
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Probe:
    elapsed_sec: float
    decision_state: str
    actual_highres_saved: bool
    record_kind: str
    video_duration_sec: float


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.strip())


def load_probe_log(path: Union[str, Path]) -> list[Probe]:
    """Parse a v2 probe-shadow CSV into an elapsed-time decision sequence.

    Rows are ordered by ``probe_timestamp``; ``elapsed_sec`` is measured from the
    first probe so the controller sees a monotonic seconds clock.
    """
    rows: list[dict[str, str]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("probe_timestamp") and row.get("decision_state"):
                rows.append(row)
    if not rows:
        return []
    rows.sort(key=lambda r: r["probe_timestamp"])
    t0 = _parse_time(rows[0]["probe_timestamp"])
    probes: list[Probe] = []
    for r in rows:
        elapsed = (_parse_time(r["probe_timestamp"]) - t0).total_seconds()
        probes.append(
            Probe(
                elapsed_sec=elapsed,
                decision_state=r["decision_state"].strip(),
                actual_highres_saved=_truthy(r.get("actual_highres_saved", "")),
                record_kind=(r.get("record_kind") or "image").strip() or "image",
                video_duration_sec=float(r.get("video_duration_sec") or 0.0 or 0),
            )
        )
    return probes


# ---------------------------------------------------------------------------
# Capture events + cost model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CaptureEvent:
    time_sec: float
    kind: str  # "image" | "video"
    duration_sec: float = 0.0


@dataclass(frozen=True)
class CostModel:
    still_bytes: int = 500_000          # ~0.5 MB per JPEG (measured ~478-508 KB on-Pi)
    video_bitrate_bits: int = 6_000_000  # H.264 software encoder bitrate on the Pi 5


@dataclass
class PolicyResult:
    name: str
    stills: int
    video_clips: int
    video_seconds: float
    est_storage_mb: float
    capture_events: list[CaptureEvent] = field(default_factory=list)
    # Filled only when visit annotations are supplied:
    visits_total: Optional[int] = None
    visits_captured: Optional[int] = None
    visit_capture_rate: Optional[float] = None
    mean_first_capture_latency_sec: Optional[float] = None

    def as_dict(self) -> dict:
        d = {
            "name": self.name,
            "stills": self.stills,
            "video_clips": self.video_clips,
            "video_seconds": round(self.video_seconds, 1),
            "est_storage_mb": round(self.est_storage_mb, 2),
            "capture_events": len(self.capture_events),
        }
        if self.visits_total is not None:
            d.update(
                visits_total=self.visits_total,
                visits_captured=self.visits_captured,
                visit_capture_rate=round(self.visit_capture_rate, 3)
                if self.visit_capture_rate is not None else None,
                mean_first_capture_latency_sec=round(self.mean_first_capture_latency_sec, 1)
                if self.mean_first_capture_latency_sec is not None else None,
            )
        return d


def _summarize(name: str, events: list[CaptureEvent], cost: CostModel) -> PolicyResult:
    stills = sum(1 for e in events if e.kind == "image")
    clips = sum(1 for e in events if e.kind == "video")
    vsec = sum(e.duration_sec for e in events if e.kind == "video")
    storage = (stills * cost.still_bytes + vsec * cost.video_bitrate_bits / 8.0) / 1e6
    return PolicyResult(name, stills, clips, vsec, storage, list(events))


# ---------------------------------------------------------------------------
# Policy replays — schedule mirrors capture_loop.compute_next_due exactly:
# a still is due at a probe when (elapsed - last_save) >= the current interval.
# ---------------------------------------------------------------------------
def replay_fixed(probes: list[Probe], interval_sec: float) -> list[CaptureEvent]:
    """① plain fixed-interval timelapse — no adaptation."""
    events: list[CaptureEvent] = []
    last: Optional[float] = None
    for p in probes:
        due = p.elapsed_sec if last is None else last + interval_sec
        if p.elapsed_sec >= due:
            events.append(CaptureEvent(p.elapsed_sec, "image"))
            last = p.elapsed_sec
    return events


def _replay_controller(
    probes: list[Probe], config: ThreeStageConfig, *, is_video: bool
) -> list[CaptureEvent]:
    controller = ThreeStageController(config)
    events: list[CaptureEvent] = []
    last: Optional[float] = None
    for p in probes:
        out = controller.step(p.decision_state, p.elapsed_sec)
        if is_video and out.trigger_video:
            events.append(CaptureEvent(p.elapsed_sec, "video", config.video_duration_sec))
            # The clip is the record for this probe; the still schedule resumes
            # from the clip's end (same as the live loop).
            last = p.elapsed_sec + config.video_duration_sec
            continue
        due = p.elapsed_sec if last is None else last + out.interval_sec
        if p.elapsed_sec >= due:
            events.append(CaptureEvent(p.elapsed_sec, "image"))
            last = p.elapsed_sec
    return events


def replay_any_motion(probes: list[Probe], base: ThreeStageConfig) -> list[CaptureEvent]:
    """② any motion (wind/shadow/insect) -> fast interval; no classification, no video."""
    from dataclasses import replace
    return _replay_controller(probes, replace(base, classify=False), is_video=False)


def replay_classified(probes: list[Probe], base: ThreeStageConfig) -> list[CaptureEvent]:
    """③ classified adaptive, STILLS only: noise filtered, local candidate -> faster
    stills (HIGH is a 5 s burst of stills), no video. This is the classification arm
    of the ①②③ comparison without the video confounder."""
    from dataclasses import replace
    return _replay_controller(probes, replace(base, classify=True, high_mode="interval"), is_video=False)


def replay_video(probes: list[Probe], base: ThreeStageConfig) -> list[CaptureEvent]:
    """④ classified + video hybrid: like ③, but a sustained strong candidate also
    fires one short video clip (then cooldown)."""
    from dataclasses import replace
    return _replay_controller(probes, replace(base, classify=True, high_mode="video"), is_video=True)


def actual_from_log(probes: list[Probe]) -> list[CaptureEvent]:
    """The ③ run that actually produced this log (fidelity cross-check)."""
    events: list[CaptureEvent] = []
    for p in probes:
        if p.record_kind == "video":
            events.append(CaptureEvent(p.elapsed_sec, "video", p.video_duration_sec))
        elif p.actual_highres_saved:
            events.append(CaptureEvent(p.elapsed_sec, "image"))
    return events


# ---------------------------------------------------------------------------
# Visit-coverage (needs ground-truth annotations)
# ---------------------------------------------------------------------------
def _apply_coverage(result: PolicyResult, visits: list[tuple[float, float]]) -> None:
    if not visits:
        return
    captured = 0
    latencies: list[float] = []
    for start, end in visits:
        hit: Optional[float] = None
        for e in result.capture_events:
            e_start = e.time_sec
            e_end = e.time_sec + (e.duration_sec if e.kind == "video" else 0.0)
            if e_start <= end and e_end >= start:  # capture overlaps the visit window
                hit = max(e_start, start)
                break
        if hit is not None:
            captured += 1
            latencies.append(max(0.0, hit - start))
    result.visits_total = len(visits)
    result.visits_captured = captured
    result.visit_capture_rate = captured / len(visits)
    result.mean_first_capture_latency_sec = (sum(latencies) / len(latencies)) if latencies else None


def read_run_start(path: Union[str, Path]) -> Optional[datetime]:
    """The first probe's absolute timestamp (the elapsed-time zero point)."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        stamps = [r["probe_timestamp"] for r in csv.DictReader(handle) if r.get("probe_timestamp")]
    return _parse_time(min(stamps)) if stamps else None


def load_visits(path: Union[str, Path], run_start: Optional[datetime]) -> list[tuple[float, float]]:
    """Load visit windows from a CSV with ``start,end`` columns.

    Each value is either plain seconds from the run start, or an ISO timestamp
    (matching ``probe_timestamp``), converted to elapsed seconds against
    ``run_start`` — annotators can copy the wall-clock time straight off an image
    filename. Windows are what the visit CAPTURE RATE is measured against.
    """
    def to_elapsed(raw: str) -> float:
        raw = raw.strip()
        try:
            return float(raw)
        except ValueError:
            if run_start is None:
                raise ValueError(f"cannot resolve ISO visit time {raw!r}: run start unknown")
            return (_parse_time(raw) - run_start).total_seconds()

    visits: list[tuple[float, float]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw_s, raw_e = (row.get("start") or ""), (row.get("end") or "")
            if raw_s.strip() and raw_e.strip():
                visits.append((to_elapsed(raw_s), to_elapsed(raw_e)))
    return visits


# ---------------------------------------------------------------------------
# Top-level comparison
# ---------------------------------------------------------------------------
@dataclass
class Comparison:
    run_probes: int
    duration_sec: float
    fixed_interval_sec: float
    results: list[PolicyResult]

    def as_dict(self) -> dict:
        return {
            "run_probes": self.run_probes,
            "duration_sec": round(self.duration_sec, 1),
            "fixed_interval_sec": self.fixed_interval_sec,
            "policies": [r.as_dict() for r in self.results],
        }


def compare(
    probes: list[Probe],
    *,
    fixed_interval_sec: float = 30.0,
    config: Optional[ThreeStageConfig] = None,
    cost: Optional[CostModel] = None,
    visits: Optional[list[tuple[float, float]]] = None,
) -> Comparison:
    base = config or ThreeStageConfig()
    cost = cost or CostModel()
    # ASCII labels (1/2/3/4) so the report prints safely on any console encoding
    # (a Windows cp932 terminal garbles the circled ①②③④ glyphs).
    # ①②③ are stills-only (the clean capture-cost comparison); ④ adds video.
    results = [
        _summarize("1 fixed", replay_fixed(probes, fixed_interval_sec), cost),
        _summarize("2 any-motion", replay_any_motion(probes, base), cost),
        _summarize("3 classified", replay_classified(probes, base), cost),
        _summarize("4 video", replay_video(probes, base), cost),
        _summarize("actual(log)", actual_from_log(probes), cost),
    ]
    if visits:
        for r in results:
            _apply_coverage(r, visits)
    duration = probes[-1].elapsed_sec - probes[0].elapsed_sec if probes else 0.0
    return Comparison(len(probes), duration, fixed_interval_sec, results)


def format_report(cmp: Comparison) -> str:
    has_visits = any(r.visits_total is not None for r in cmp.results)
    lines = [
        f"Probes: {cmp.run_probes}  duration: {cmp.duration_sec:.0f}s "
        f"({cmp.duration_sec/3600:.2f} h)  fixed(1)={cmp.fixed_interval_sec:.0f}s",
        "",
    ]
    header = f"{'policy':<20}{'stills':>8}{'clips':>7}{'video_s':>9}{'storage_MB':>12}"
    if has_visits:
        header += f"{'visit%':>9}{'lat_s':>8}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in cmp.results:
        row = (
            f"{r.name:<20}{r.stills:>8}{r.video_clips:>7}"
            f"{r.video_seconds:>9.0f}{r.est_storage_mb:>12.1f}"
        )
        if has_visits:
            rate = "-" if r.visit_capture_rate is None else f"{r.visit_capture_rate*100:>7.0f}%"
            lat = "-" if r.mean_first_capture_latency_sec is None else f"{r.mean_first_capture_latency_sec:>7.0f}"
            row += f"{rate:>9}{lat:>8}"
        lines.append(row)
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay capture policies ①②③ over a recorded v2 probe log."
    )
    parser.add_argument("log", type=Path, help="adaptive_probe_shadow_v2_<run_id>.csv")
    parser.add_argument("--fixed-interval", type=float, default=30.0, help="① interval (s)")
    parser.add_argument("--low", type=float, default=None, help="override LOW interval (s)")
    parser.add_argument("--mid", type=float, default=None, help="override MID interval (s)")
    parser.add_argument("--video-duration", type=float, default=None, help="override clip length (s)")
    parser.add_argument("--cooldown", type=float, default=None, help="override video cooldown (s)")
    parser.add_argument("--still-kb", type=float, default=500.0, help="bytes/still estimate (KB)")
    parser.add_argument("--video-mbps", type=float, default=6.0, help="clip bitrate (Mbit/s)")
    parser.add_argument("--visits", type=Path, default=None, help="CSV of start,end visit windows (seconds)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args(argv)

    probes = load_probe_log(args.log)
    if not probes:
        parser.error(f"no usable probe rows in {args.log}")

    base = ThreeStageConfig()
    overrides = {}
    if args.low is not None:
        overrides["low_interval_sec"] = args.low
    if args.mid is not None:
        overrides["mid_interval_sec"] = args.mid
    if args.video_duration is not None:
        overrides["video_duration_sec"] = args.video_duration
    if args.cooldown is not None:
        overrides["video_cooldown_sec"] = args.cooldown
    if overrides:
        from dataclasses import replace
        base = replace(base, **overrides)

    cost = CostModel(
        still_bytes=int(args.still_kb * 1000),
        video_bitrate_bits=int(args.video_mbps * 1_000_000),
    )
    visits = load_visits(args.visits, read_run_start(args.log)) if args.visits else None
    cmp = compare(probes, fixed_interval_sec=args.fixed_interval, config=base, cost=cost, visits=visits)

    if args.json:
        print(json.dumps(cmp.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_report(cmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
