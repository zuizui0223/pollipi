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
