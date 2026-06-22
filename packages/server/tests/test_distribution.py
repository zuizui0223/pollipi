from __future__ import annotations

from pathlib import Path

from visit_monitor_server.distribution.bundle_single_file import _web_build_id, apply_build_metadata, collect_sources


def test_bundle_metadata_is_embedded() -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "visit_monitor_server"
    sources = apply_build_metadata(
        collect_sources(package_root),
        git_commit="abc123",
        build_timestamp="2026-06-22T00:00:00+00:00",
        web_build_id="web-42",
    )

    build_info = sources["visit_monitor_server.build_info"]
    assert 'EMBEDDED_GIT_COMMIT = "abc123"' in build_info
    assert 'EMBEDDED_BUILD_TIMESTAMP = "2026-06-22T00:00:00+00:00"' in build_info
    assert 'EMBEDDED_DEPLOYMENT_MODE = "packaged_artifact"' in build_info
    assert 'EMBEDDED_WEB_BUILD_ID = "web-42"' in build_info


def test_web_build_id_is_deterministic_from_commit_timestamp() -> None:
    assert _web_build_id("abc123", "2026-06-22T12:34:56+09:00") == "abc123-20260622-123456"
