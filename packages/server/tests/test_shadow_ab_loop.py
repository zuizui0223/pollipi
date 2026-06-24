"""Phase 3 integration: the capture loop writes a baseline-vs-candidate A/B log.

Drives the real run_capture_loop with the fake camera and a loaded artifact, and
asserts a shadow_ab.csv with both policies' decisions is produced. Neither policy
controls timing (control stays off until Phase 4 is enabled).

The server modules are imported fresh inside the test (with env pointing at the
temp dir + artifact) so the loop's deferred ``policy_runtime`` import resolves to
the same configuration we set up — independent of any other test that reloads the
``visit_monitor_server`` package.
"""
from __future__ import annotations

import csv
import importlib
import sys
import threading
import time

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig
from pollipi_analysis.policy.artifact import PolicyMeta, write_policy


def _clear_server_modules() -> None:
    for name in list(sys.modules):
        if name == "visit_monitor_server" or name.startswith("visit_monitor_server."):
            sys.modules.pop(name)


def test_capture_loop_writes_shadow_ab_log(monkeypatch, tmp_path) -> None:
    policy_path = tmp_path / "simulation_informed_policy.json"
    write_policy(
        policy_path,
        PipelineConfig(
            features=FeatureConfig(cell_size=48, pixel_difference=30),
            classifier=ClassifierConfig(strong_spatial_concentration=0.85),
        ),
        PolicyMeta(policy_name="simulation_informed", policy_version="1", validation_status="simulation_informed"),
    )

    monkeypatch.setenv("POLLIPI_FAKE_CAMERA", "1")
    monkeypatch.setenv("POLLIPI_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("POLLIPI_POLICY_PATH", str(policy_path))

    _clear_server_modules()
    config = importlib.import_module("visit_monitor_server.config")
    cl = importlib.import_module("visit_monitor_server.services.capture_loop")
    capture_schema = importlib.import_module("visit_monitor_server.api.schemas.capture")

    ab_path = config.SHADOW_AB_LOG_PATH
    request = capture_schema.StartRequest(interval_sec=1, comparison_session_id="abtest-1", camera_role="A")
    stop_event = threading.Event()
    error: list[BaseException] = []

    def run() -> None:
        try:
            cl.run_capture_loop(
                stop_event,
                request,
                tmp_path / "images",
                threading.Lock(),
                set_camera=lambda *_: None,
                update_state=lambda *_: None,
                set_message=lambda *_: None,
            )
        except BaseException as exc:  # noqa: BLE001 - surfaced to the test
            error.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    # Poll for the first analysed frame rather than guessing a fixed sleep — the
    # loop has a ~2s startup wait plus 1s intervals and can be slow under load.
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline and not ab_path.exists() and not error:
        time.sleep(0.1)
    stop_event.set()
    worker.join(timeout=10.0)

    assert not error, f"capture loop raised: {error}"
    assert ab_path.exists(), "shadow A/B log was not written"

    with ab_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "no A/B rows written"
    row = rows[0]
    assert row["a_policy_name"] == "baseline_rule"
    assert row["b_policy_name"] == "simulation_informed"
    assert row["comparison_session_id"] == "abtest-1"
    # Both decisions are recorded; agreement is a valid boolean string.
    assert row["a_state"] and row["b_state"]
    assert row["agree"] in {"True", "False"}
