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
    config = tmp_path / "fleet.json"
    config.write_text(json.dumps({
        "defaults": {
            "ssh_port": 22,
            "server_artifact": "dist/pollipi_api_server.py",
            "web_build_dir": "packages/web/dist",
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
    assert all(step["status"] == "dry-run" for result in results for step in result["steps"])
    assert any("GET http://192.168.8.11:8000/device" in step["command"] for step in results[0]["steps"])
