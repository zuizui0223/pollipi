from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_tool():
    repo_root = Path(__file__).resolve().parents[3]
    tool_path = repo_root / "tools" / "pollipi_fleet_deploy.py"
    spec = importlib.util.spec_from_file_location("pollipi_fleet_deploy", tool_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fleet_deploy_dry_run_plans_five_gl_lan_devices(tmp_path: Path) -> None:
    tool = _load_tool()
    artifact = tmp_path / "dist" / "pollipi_api_server.py"
    web_dir = tmp_path / "web-dist"
    artifact.parent.mkdir()
    artifact.write_text("print('artifact')\n", encoding="utf-8")
    web_dir.mkdir()
    (web_dir / "build-info.json").write_text('{"web_build_id":"web-test"}\n', encoding="utf-8")
    config = tmp_path / "fleet.json"
    config.write_text(json.dumps({
        "subnet": "192.168.8.0/24",
        "defaults": {
            "ssh_port": 22,
            "server_artifact": str(artifact),
            "web_build_dir": str(web_dir),
            "remote_dir": "/home/pollipi/pollipi_timelapse",
            "server_filename": "pollipi_api_server.py",
            "web_remote_dir": "web",
            "service_name": "pollipi.service",
            "post_deploy_base_url": "http://{host}:8000",
        },
        "devices": [
            {"name": f"pollipi-{i}", "host": f"192.168.8.{i}", "ssh_user": "pi"}
            for i in range(11, 16)
        ],
    }), encoding="utf-8")

    devices = tool.load_devices(config)
    results = [tool.deploy_device(device, dry_run=True) for device in devices]

    assert [device.host for device in devices] == [f"192.168.8.{i}" for i in range(11, 16)]
    assert all(result["status"] == "ok" for result in results)
    assert any(step["step"] == "local artifacts" and step["status"] == "ok" for step in results[0]["steps"])
    assert any(step["step"] == "GET /device" and step["status"] == "dry-run" for step in results[0]["steps"])
    assert any(
        "GET http://192.168.8.11:8000/device" in step.get("command", "")
        for step in results[0]["steps"]
    )


def test_fleet_deploy_execute_requires_confirmation(tmp_path: Path, capsys) -> None:
    tool = _load_tool()
    artifact = tmp_path / "dist" / "pollipi_api_server.py"
    web_dir = tmp_path / "web-dist"
    artifact.parent.mkdir()
    artifact.write_text("print('artifact')\n", encoding="utf-8")
    web_dir.mkdir()
    (web_dir / "build-info.json").write_text('{"web_build_id":"web-test"}\n', encoding="utf-8")
    config = tmp_path / "fleet.json"
    config.write_text(json.dumps({
        "subnet": "192.168.8.0/24",
        "defaults": {
            "ssh_port": 22,
            "server_artifact": str(artifact),
            "web_build_dir": str(web_dir),
            "remote_dir": "/home/pollipi/pollipi_timelapse",
            "server_filename": "pollipi_api_server.py",
            "web_remote_dir": "web",
            "service_name": "pollipi.service",
            "post_deploy_base_url": "http://{host}:8000",
        },
        "devices": [{"name": "pollipi-11", "host": "192.168.8.11", "ssh_user": "pi"}],
    }), encoding="utf-8")

    old_argv = sys.argv
    try:
        sys.argv = ["pollipi_fleet_deploy.py", "--config", str(config), "--execute"]
        exit_code = tool.main()
    finally:
        sys.argv = old_argv
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "requires --confirm-live-deploy" in captured.err
    assert "dry-run" in captured.out


def test_latest_main_web_only_requires_apply_even_with_legacy_execute(monkeypatch, tmp_path: Path, capsys) -> None:
    tool = _load_tool()
    web_dir = tmp_path / "web-dist"
    web_dir.mkdir()
    (web_dir / "build-info.json").write_text(
        '{"web_build_id":"abc123-20260624","git_commit":"abc123"}\n',
        encoding="utf-8",
    )
    config = tmp_path / "fleet.json"
    config.write_text(json.dumps({
        "subnet": "192.168.11.0/24",
        "defaults": {
            "ssh_port": 22,
            "ssh_user": "zuizui0223",
            "server_artifact": "dist/pollipi_api_server.py",
            "web_build_dir": str(web_dir),
            "remote_dir": "/home/zuizui0223/pollipi_timelapse",
            "server_filename": "pollipi_api_server.py",
            "web_remote_dir": "web",
            "service_name": "pollipi.service",
            "post_deploy_base_url": "http://{host}:8000/app",
        },
        "devices": [{"name": "zuizui", "host": "zuizui.local"}],
    }), encoding="utf-8")

    monkeypatch.setattr(tool, "require_latest_origin_main", lambda: ("abc123", "abc123" * 10))
    monkeypatch.setattr(tool, "build_web_or_fail", lambda: "built")

    old_argv = sys.argv
    try:
        sys.argv = [
            "pollipi_fleet_deploy.py",
            "--config",
            str(config),
            "--latest-main-web-only",
            "--execute",
            "--confirm-live-deploy",
        ]
        exit_code = tool.main()
    finally:
        sys.argv = old_argv

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "requires --apply" in captured.err
    assert "mode: dry-run" in captured.out
    assert "upload web build" in captured.out
    assert "restart service" not in captured.out


def test_web_only_verifies_static_build_info_instead_of_device_metadata(monkeypatch, tmp_path: Path) -> None:
    tool = _load_tool()
    web_dir = tmp_path / "web-dist"
    web_dir.mkdir()
    (web_dir / "build-info.json").write_text(
        '{"web_build_id":"web-test","git_commit":"commit-test"}\n',
        encoding="utf-8",
    )
    device = tool.Device(
        name="zuizui",
        host="zuizui.local",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact="dist/pollipi_api_server.py",
        server_filename="pollipi_api_server.py",
        web_build_dir=str(web_dir),
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )

    called_urls: list[str] = []

    def fake_http_get_json(url: str):
        called_urls.append(url)
        return True, {"git_commit": "commit-test", "web_build_id": "web-test"}

    monkeypatch.setattr(tool, "http_get_json", fake_http_get_json)
    ok, output = tool.verify_web_build_info(
        device,
        expected_commit="commit-test",
        expected_web_build_id="web-test",
    )

    assert ok is True
    assert output == "commit-test / web-test"
    assert called_urls == ["http://zuizui.local:8000/app/build-info.json"]
