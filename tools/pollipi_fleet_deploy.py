#!/usr/bin/env python3
"""Dry-run friendly PolliPi fleet deployment planner/executor."""
from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Fleet:
    subnet: str
    devices: list["Device"]


@dataclass
class Device:
    name: str
    host: str
    ssh_user: str
    ssh_port: int
    remote_dir: str
    server_artifact: str
    server_filename: str
    web_build_dir: str
    web_remote_dir: str
    service_name: str
    post_deploy_base_url: str

    @property
    def target(self) -> str:
        return f"{self.ssh_user}@{self.host}"

    @property
    def base_url(self) -> str:
        return self.post_deploy_base_url.format(host=self.host).rstrip("/")


def _required_value(merged: dict[str, Any], key: str) -> bool:
    value = merged.get(key)
    return bool(value) and not str(value).startswith("CHANGE_ME")


def load_fleet(path: Path) -> Fleet:
    config = json.loads(path.read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
    subnet = str(config.get("subnet") or defaults.get("subnet") or "192.168.8.0/24")
    devices: list[Device] = []
    for item in config.get("devices", []):
        merged = {**defaults, **item}
        missing = [
            key for key in (
                "name",
                "host",
                "ssh_user",
                "remote_dir",
                "server_artifact",
                "server_filename",
                "web_build_dir",
                "web_remote_dir",
                "service_name",
                "post_deploy_base_url",
            )
            if not _required_value(merged, key)
        ]
        if missing:
            raise ValueError(f"{item.get('name', item.get('host', '<unknown>'))}: missing {', '.join(missing)}")
        devices.append(Device(
            name=merged["name"],
            host=merged["host"],
            ssh_user=merged["ssh_user"],
            ssh_port=int(merged.get("ssh_port", 22)),
            remote_dir=merged["remote_dir"].rstrip("/"),
            server_artifact=merged["server_artifact"],
            server_filename=merged["server_filename"],
            web_build_dir=merged["web_build_dir"].rstrip("/"),
            web_remote_dir=merged["web_remote_dir"].strip("/"),
            service_name=merged["service_name"],
            post_deploy_base_url=merged["post_deploy_base_url"],
        ))
    if not devices:
        raise ValueError("config has no devices")
    return Fleet(subnet=subnet, devices=devices)


def load_devices(path: Path) -> list[Device]:
    return load_fleet(path).devices


def ssh_cmd(device: Device, remote: str) -> list[str]:
    return ["ssh", "-p", str(device.ssh_port), device.target, remote]


def scp_cmd(device: Device, source: str, dest: str, *, recursive: bool = False) -> list[str]:
    cmd = ["scp", "-P", str(device.ssh_port)]
    if recursive:
        cmd.append("-r")
    cmd.extend([source, f"{device.target}:{dest}"])
    return cmd


def command_text(cmd: list[str]) -> str:
    return " ".join(cmd)


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode == 0, proc.stdout.strip()


def http_get_json(url: str) -> tuple[bool, dict[str, Any] | str]:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
            if response.status != 200:
                return False, body
            return True, json.loads(body)
    except Exception as exc:
        return False, str(exc)


def tcp_connect(host: str, port: int, timeout: float = 4.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "reachable"
    except Exception as exc:
        return False, str(exc)


def local_ip_for(host: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((host, 9))
        return sock.getsockname()[0]


def pc_on_subnet(subnet: str, probe_host: str) -> tuple[bool, str]:
    try:
        local_ip = local_ip_for(probe_host)
        network = ipaddress.ip_network(subnet, strict=False)
        return ipaddress.ip_address(local_ip) in network, local_ip
    except Exception as exc:
        return False, str(exc)


def local_artifacts_ok(device: Device) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not Path(device.server_artifact).is_file():
        errors.append(f"missing server artifact: {device.server_artifact}")
    if not Path(device.web_build_dir).is_dir():
        errors.append(f"missing web build dir: {device.web_build_dir}")
    return not errors, errors


def read_web_build_id(web_build_dir: str) -> str:
    path = Path(web_build_dir) / "build-info.json"
    if not path.is_file():
        return ""
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("web_build_id", "")).strip()
    except Exception:
        return ""


def expected_git_commit() -> str:
    ok, output = run_cmd(["git", "rev-parse", "--short=12", "HEAD"])
    return output.strip() if ok else ""


def preflight_device(device: Device, *, subnet: str, dry_run: bool) -> dict[str, Any]:
    steps: list[dict[str, str]] = []
    ok = True

    artifact_ok, artifact_errors = local_artifacts_ok(device)
    ok = ok and artifact_ok
    steps.append({
        "step": "local artifacts",
        "status": "ok" if artifact_ok else "failed",
        "output": "; ".join(artifact_errors) if artifact_errors else "server artifact and web build exist",
    })

    subnet_ok, local_ip = pc_on_subnet(subnet, device.host)
    if not dry_run:
        ok = ok and subnet_ok
    steps.append({
        "step": "PC subnet",
        "status": "ok" if subnet_ok else "dry-run" if dry_run else "failed",
        "output": f"local={local_ip}, required={subnet}",
    })

    ssh_ok, ssh_output = (True, "dry-run") if dry_run else tcp_connect(device.host, device.ssh_port)
    ok = ok and ssh_ok
    steps.append({"step": "SSH reachability", "status": "ok" if ssh_ok else "failed", "output": ssh_output})

    http_ok, http_output = (True, "dry-run") if dry_run else tcp_connect(device.host, 8000)
    ok = ok and http_ok
    steps.append({"step": "HTTP reachability", "status": "ok" if http_ok else "failed", "output": http_output})

    for endpoint in ("device", "status"):
        if dry_run:
            steps.append({"step": f"GET /{endpoint}", "status": "dry-run", "output": f"GET {device.base_url}/{endpoint}"})
            continue
        endpoint_ok, payload = http_get_json(f"{device.base_url}/{endpoint}")
        ok = ok and endpoint_ok
        steps.append({
            "step": f"GET /{endpoint}",
            "status": "ok" if endpoint_ok else "failed",
            "output": json.dumps(payload, ensure_ascii=False)[:500] if isinstance(payload, dict) else str(payload)[:500],
        })

    return {"status": "ok" if ok else "failed", "steps": steps}


def deploy_plan(device: Device, stamp: str) -> dict[str, Any]:
    remote_server = f"{device.remote_dir}/{device.server_filename}"
    backup_server = f"{remote_server}.bak-{stamp}"
    remote_web = f"{device.remote_dir}/{device.web_remote_dir}"
    backup_web = f"{remote_web}.bak-{stamp}"
    steps = [
        ("prepare remote directory", ssh_cmd(device, f"mkdir -p {device.remote_dir} {remote_web}")),
        ("backup current server artifact", ssh_cmd(device, f"test ! -f {remote_server} || cp {remote_server} {backup_server}")),
        ("backup current web build", ssh_cmd(device, f"test ! -d {remote_web} || cp -a {remote_web} {backup_web}")),
        ("upload server artifact", scp_cmd(device, device.server_artifact, remote_server)),
        ("upload web build", scp_cmd(device, f"{device.web_build_dir}/.", remote_web, recursive=True)),
        ("restart service", ssh_cmd(device, f"sudo systemctl restart {device.service_name}")),
    ]
    rollback = [
        ("restore server backup", ssh_cmd(device, f"test ! -f {backup_server} || cp {backup_server} {remote_server}")),
        ("restore web backup", ssh_cmd(device, f"if test -d {backup_web}; then rm -rf {remote_web}; cp -a {backup_web} {remote_web}; fi")),
        ("restart service after rollback", ssh_cmd(device, f"sudo systemctl restart {device.service_name}")),
    ]
    return {"steps": steps, "rollback": rollback}


def verify_post_deploy(device: Device, *, expected_commit: str, expected_web_build_id: str) -> tuple[bool, str]:
    ok, payload = http_get_json(f"{device.base_url}/device")
    if not ok or not isinstance(payload, dict):
        return False, str(payload)
    build_info = payload.get("build_info") or {}
    commit = str(build_info.get("git_commit", ""))
    web_build_id = str(build_info.get("web_build_id", ""))
    mode = str(build_info.get("deployment_mode", ""))
    mismatches = []
    if mode != "packaged_artifact":
        mismatches.append(f"deployment_mode={mode}")
    if expected_commit and commit != expected_commit:
        mismatches.append(f"git_commit={commit}, expected={expected_commit}")
    if expected_web_build_id and web_build_id != expected_web_build_id:
        mismatches.append(f"web_build_id={web_build_id}, expected={expected_web_build_id}")
    if mismatches:
        return False, "; ".join(mismatches)
    return True, f"{mode} / {commit or 'unknown'} / {web_build_id or 'unknown'}"


def run_rollback(device: Device, rollback_steps: list[tuple[str, list[str]]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for label, cmd in rollback_steps:
        step_ok, output = run_cmd(cmd)
        results.append({"step": label, "status": "ok" if step_ok else "failed", "output": output[:500]})
    return results


def deploy_device(
    device: Device,
    *,
    subnet: str = "192.168.8.0/24",
    dry_run: bool,
    expected_commit: str = "",
    expected_web_build_id: str = "",
) -> dict[str, Any]:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    plan = deploy_plan(device, stamp)
    result: dict[str, Any] = {"device": device.name, "host": device.host, "status": "ok", "steps": []}

    preflight = preflight_device(device, subnet=subnet, dry_run=dry_run)
    result["steps"].extend(preflight["steps"])
    if preflight["status"] != "ok":
        result["status"] = "failed"
        return result

    for label, cmd in plan["steps"]:
        if dry_run:
            result["steps"].append({"step": label, "status": "dry-run", "command": command_text(cmd)})
            continue
        step_ok, output = run_cmd(cmd)
        result["steps"].append({"step": label, "status": "ok" if step_ok else "failed", "output": output[:500]})
        if not step_ok:
            result["status"] = "failed"
            result["rollback"] = run_rollback(device, plan["rollback"])
            return result

    if dry_run:
        result["steps"].append({
            "step": "post-deploy version check",
            "status": "dry-run",
            "command": f"GET {device.base_url}/device and compare commit/web_build_id",
        })
        return result

    verify_ok, verify_output = verify_post_deploy(
        device,
        expected_commit=expected_commit,
        expected_web_build_id=expected_web_build_id,
    )
    result["steps"].append({
        "step": "post-deploy version check",
        "status": "ok" if verify_ok else "failed",
        "output": verify_output,
    })
    if not verify_ok:
        result["status"] = "failed"
        result["rollback"] = run_rollback(device, plan["rollback"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy PolliPi server/web builds to a configured Pi fleet.")
    parser.add_argument("--config", type=Path, default=Path("tools/fleet.example.json"))
    parser.add_argument("--execute", action="store_true", help="Prepare for live execution. Requires --confirm-live-deploy too.")
    parser.add_argument("--confirm-live-deploy", action="store_true", help="Required with --execute to touch real Pis.")
    parser.add_argument("--expected-git-commit", default="")
    parser.add_argument("--expected-web-build-id", default="")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON results.")
    args = parser.parse_args()

    try:
        fleet = load_fleet(args.config)
    except Exception as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    dry_run = not (args.execute and args.confirm_live_deploy)
    if args.execute and not args.confirm_live_deploy:
        print("--execute requires --confirm-live-deploy; running dry-run only.", file=sys.stderr)

    expected_commit = args.expected_git_commit or expected_git_commit()
    expected_web_build_id = args.expected_web_build_id or read_web_build_id(fleet.devices[0].web_build_dir)
    results = []
    for device in fleet.devices:
        result = deploy_device(
            device,
            subnet=fleet.subnet,
            dry_run=dry_run,
            expected_commit=expected_commit,
            expected_web_build_id=expected_web_build_id,
        )
        results.append(result)
        if result["status"] != "ok":
            break

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            print(f"{result['device']} ({result['host']}): {result['status']}")
            for step in result["steps"]:
                detail = step.get("command") or step.get("output", "")
                print(f"  - {step['status']}: {step['step']}{' -> ' + detail if detail else ''}")
            for step in result.get("rollback", []):
                print(f"  - rollback {step['status']}: {step['step']} -> {step.get('output', '')}")
    return 0 if all(result["status"] == "ok" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
