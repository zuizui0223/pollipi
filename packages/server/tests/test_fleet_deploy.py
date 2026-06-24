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


def test_app_base_url_uses_root_api_urls_in_preflight() -> None:
    tool = _load_tool()
    device = tool.Device(
        name="zuizui",
        host="192.168.11.17",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact="dist/pollipi_api_server.py",
        server_filename="pollipi_api_server.py",
        web_build_dir="packages/web/dist",
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )

    result = tool.preflight_device(device, subnet="192.168.11.0/24", dry_run=True)
    outputs = [step.get("output", "") for step in result["steps"]]

    assert "GET http://192.168.11.17:8000/device" in outputs
    assert "GET http://192.168.11.17:8000/status" in outputs
    assert all("/app/device" not in output for output in outputs)
    assert all("/app/status" not in output for output in outputs)


def test_full_deploy_ssh_auth_failure_stops_before_backup_upload(monkeypatch, tmp_path: Path) -> None:
    tool = _load_tool()
    artifact = tmp_path / "dist" / "pollipi_api_server.py"
    web_dir = tmp_path / "web-dist"
    artifact.parent.mkdir()
    artifact.write_text("print('artifact')\n", encoding="utf-8")
    web_dir.mkdir()
    device = tool.Device(
        name="zuizui",
        host="192.168.11.17",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact=str(artifact),
        server_filename="pollipi_api_server.py",
        web_build_dir=str(web_dir),
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )
    commands: list[str] = []

    monkeypatch.setattr(tool, "pc_on_subnet", lambda subnet, host: (True, "192.168.11.4"))
    monkeypatch.setattr(tool, "tcp_connect", lambda host, port: (True, "reachable"))

    def fake_run_cmd(cmd):
        commands.append(tool.command_text(cmd))
        if "BatchMode=yes" in cmd and cmd[-1] == "hostname":
            return False, "Permission denied"
        return True, ""

    monkeypatch.setattr(tool, "run_cmd", fake_run_cmd)
    result = tool.deploy_device(device, subnet="192.168.11.0/24", dry_run=False)

    assert result["status"] == "failed"
    assert any(step["step"] == "SSH auth" and step["status"] == "failed" for step in result["steps"])
    assert not any("cp /home/zuizui0223/pollipi_timelapse/pollipi_api_server.py" in command for command in commands)
    assert not any("scp" in command for command in commands)
    assert "rollback" not in result


def test_full_deploy_sudo_failure_stops_before_backup_upload(monkeypatch, tmp_path: Path) -> None:
    tool = _load_tool()
    artifact = tmp_path / "dist" / "pollipi_api_server.py"
    web_dir = tmp_path / "web-dist"
    artifact.parent.mkdir()
    artifact.write_text("print('artifact')\n", encoding="utf-8")
    web_dir.mkdir()
    device = tool.Device(
        name="zuizui",
        host="192.168.11.17",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact=str(artifact),
        server_filename="pollipi_api_server.py",
        web_build_dir=str(web_dir),
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )
    commands: list[str] = []

    monkeypatch.setattr(tool, "pc_on_subnet", lambda subnet, host: (True, "192.168.11.4"))
    monkeypatch.setattr(tool, "tcp_connect", lambda host, port: (True, "reachable"))

    def fake_run_cmd(cmd):
        commands.append(tool.command_text(cmd))
        if cmd[-1].startswith("sudo -n systemctl status"):
            return False, "sudo: a password is required"
        return True, "zuizui"

    monkeypatch.setattr(tool, "run_cmd", fake_run_cmd)
    result = tool.deploy_device(device, subnet="192.168.11.0/24", dry_run=False)

    assert result["status"] == "failed"
    assert any(step["step"] == "sudo restart permission" and step["status"] == "failed" for step in result["steps"])
    assert not any("cp /home/zuizui0223/pollipi_timelapse/pollipi_api_server.py" in command for command in commands)
    assert not any("scp" in command for command in commands)
    assert "rollback" not in result


def test_full_deploy_plan_uses_noninteractive_ssh_and_scp() -> None:
    tool = _load_tool()
    device = tool.Device(
        name="zuizui",
        host="192.168.11.17",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact="dist/pollipi_api_server.py",
        server_filename="pollipi_api_server.py",
        web_build_dir="packages/web/dist",
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )

    plan = tool.deploy_plan(device, "stamp")
    commands = [cmd for _label, cmd in plan["steps"]]
    ssh_commands = [cmd for cmd in commands if cmd[0] == "ssh"]
    scp_commands = [cmd for cmd in commands if cmd[0] == "scp"]

    assert ssh_commands
    assert scp_commands
    assert all("BatchMode=yes" in command for command in ssh_commands)
    assert all("ConnectTimeout=8" in command for command in ssh_commands)
    assert all("BatchMode=yes" in command for command in scp_commands)
    assert all("ConnectTimeout=8" in command for command in scp_commands)


def test_full_deploy_rollback_uses_noninteractive_ssh() -> None:
    tool = _load_tool()
    device = tool.Device(
        name="zuizui",
        host="192.168.11.17",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact="dist/pollipi_api_server.py",
        server_filename="pollipi_api_server.py",
        web_build_dir="packages/web/dist",
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )

    plan = tool.deploy_plan(device, "stamp")
    rollback_commands = [cmd for _label, cmd in plan["rollback"]]

    assert rollback_commands
    assert all(command[0] == "ssh" for command in rollback_commands)
    assert all("BatchMode=yes" in command for command in rollback_commands)
    assert all("ConnectTimeout=8" in command for command in rollback_commands)


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


def test_web_only_plan_omits_server_upload_and_restart() -> None:
    tool = _load_tool()
    device = tool.Device(
        name="zuizui",
        host="192.168.11.17",
        ssh_user="zuizui0223",
        ssh_port=22,
        remote_dir="/home/zuizui0223/pollipi_timelapse",
        server_artifact="dist/pollipi_api_server.py",
        server_filename="pollipi_api_server.py",
        web_build_dir="packages/web/dist",
        web_remote_dir="web",
        service_name="pollipi.service",
        post_deploy_base_url="http://{host}:8000/app",
    )

    plan = tool.web_only_deploy_plan(device, "stamp")
    commands = [tool.command_text(cmd) for _label, cmd in plan["steps"]]

    assert any("packages/web/dist/." in command for command in commands)
    assert not any("pollipi_api_server.py" in command for command in commands)
    assert not any("systemctl restart" in command for command in commands)
    assert all("BatchMode=yes" in command for command in commands)
    assert all("ConnectTimeout=8" in command for command in commands)


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
