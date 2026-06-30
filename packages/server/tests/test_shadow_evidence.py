"""Shadow evidence: one previous+current lores pair saved per local-candidate event.

no_activity / environmental_noise never save; entering uncertain/strong saves two
images once; continuing probes in the same event save nothing more. Live adaptive
stays OFF, the high-res timelapse is untouched, and no video is recorded.
"""
from __future__ import annotations

import csv
import importlib
import sys
import threading
import time
from types import SimpleNamespace

from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.features import MeshFeatures
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)


def _clear() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def _features() -> MeshFeatures:
    return MeshFeatures(
        active_cell_proportion=0.05,
        largest_component_cells=1,
        concentration=0.5,
        spatial_concentration=0.7,
        offset_active_cell_proportion=0.04,
        offset_agreement=0.5,
        persistence=0.0,
        centroid_x=3.0,
        centroid_y=4.0,
        centroid_displacement=0.0,
        path_efficiency=0.0,
        active_set_jaccard=0.0,
        global_synchrony=0.01,
        estimated_global_shift=0.0,
        cell_size=32,
    )


def _scripted_analyze(states):
    """Return an analyze() stand-in that yields the scripted states in order."""
    box = {"i": 0}

    def fake_analyze(frame, background, **kwargs):
        i = box["i"]
        state = states[i] if i < len(states) else NO_ACTIVITY
        box["i"] = i + 1
        return MeshDecision(state=state, reason="scripted", features=_features(), active_cells=frozenset())

    return fake_analyze


def _run_with_script(monkeypatch, tmp_path, states):
    images = tmp_path / "images"
    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(images))
    monkeypatch.setenv("POLLIPI_PROBE_INTERVAL_SEC", "0.05")
    monkeypatch.delenv("POLLIPI_LIVE_ADAPTIVE_ENABLED", raising=False)
    _clear()
    capture_loop = importlib.import_module("visit_monitor_server.services.capture_loop")
    monkeypatch.setattr(capture_loop, "analyze", _scripted_analyze(states))

    stop = threading.Event()
    request = SimpleNamespace(
        interval_sec=30,
        policy_profile_id="three_stage_default_v1",
        live_adaptive_requested=False,
    )
    thread = threading.Thread(
        target=capture_loop.run_capture_loop,
        args=(stop, request, images, threading.Lock(), lambda c: None, lambda d: None, lambda m: None),
        daemon=True,
    )
    thread.start()
    try:
        # +1 because probe 1 has no reference frame (no analyze call).
        target_rows = len(states) + 1
        log = images / ""
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            logs = list(images.glob("adaptive_probe_shadow_v2_*.csv"))
            if logs and sum(1 for _ in logs[0].open(encoding="utf-8")) >= target_rows:
                break
            time.sleep(0.1)
    finally:
        stop.set()
        thread.join(timeout=5.0)

    logs = list(images.glob("adaptive_probe_shadow_v2_*.csv"))
    rows = list(csv.DictReader(logs[0].open(encoding="utf-8")))
    evidence_dir = images / "shadow_evidence"
    evidence_files = sorted(p.name for p in evidence_dir.glob("*.jpg")) if evidence_dir.exists() else []
    return rows, evidence_files


def test_no_and_noise_save_no_evidence(monkeypatch, tmp_path) -> None:
    rows, evidence_files = _run_with_script(
        monkeypatch, tmp_path,
        [NO_ACTIVITY, ENVIRONMENTAL_NOISE, NO_ACTIVITY, ENVIRONMENTAL_NOISE, NO_ACTIVITY],
    )
    assert evidence_files == []
    assert all(r["evidence_event_id"] == "" for r in rows)
    assert all(r["evidence_previous_filename"] == "" for r in rows)


def test_candidate_entry_saves_one_pair_without_duplicates(monkeypatch, tmp_path) -> None:
    # no -> uncertain(enter) -> uncertain(continue) -> no(end) -> strong(enter) -> strong(continue)
    script = [
        NO_ACTIVITY,
        UNCERTAIN_LOCAL_ACTIVITY,
        UNCERTAIN_LOCAL_ACTIVITY,
        NO_ACTIVITY,
        STRONG_VISITATION_CANDIDATE,
        STRONG_VISITATION_CANDIDATE,
    ]
    rows, evidence_files = _run_with_script(monkeypatch, tmp_path, script)

    # Exactly two events -> two previous+current pairs -> four JPEGs.
    assert len(evidence_files) == 4

    event_rows = [r for r in rows if r["evidence_event_id"]]
    assert len(event_rows) == 2  # only the two entry probes, not the continuations
    for r in event_rows:
        assert r["decision_state"] in (UNCERTAIN_LOCAL_ACTIVITY, STRONG_VISITATION_CANDIDATE)
        assert r["evidence_previous_filename"].startswith("shadow_evidence/")
        assert r["evidence_current_filename"].startswith("shadow_evidence/")
        assert r["evidence_previous_filename"].endswith("_prev.jpg")
        assert r["evidence_current_filename"].endswith("_curr.jpg")
    # Distinct event ids; continuation/quiet probes carry no evidence.
    assert len({r["evidence_event_id"] for r in event_rows}) == 2

    # Evidence stays separate from the scientific record and never fires video.
    assert all(r["record_kind"] == "image" for r in rows)
    assert all(r["live_adaptive_active"] == "False" for r in rows)
