#!/usr/bin/env python3
"""Dry-run friendly PolliPi fleet deployment planner/executor."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
        return self.post_deploy_base_url.format(host=self.host)


def load_devices(path: Path) -> list[Device]:
    config = json.loads(path.read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
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
            if not merged.get(key) or str(merged.get(key)).startswith("CHANGE_ME")
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
    return devices


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


def plan_for(device: Device) -> list[tuple[str, list[str] | None]]:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    remote_server = f"{device.remote_dir}/{device.server_filename}"
    backup_server = f"{remote_server}.bak-{stamp}"
    remote_web = f"{device.remote_dir}/{device.web_remote_dir}"
    backup_web = f"{remote_web}.bak-{stamp}"
    return [
        ("prepare remote directory", ssh_cmd(device, f"mkdir -p {device.remote_dir} {remote_web}")),
        ("backup current server artifact", ssh_cmd(device, f"test ! -f {remote_server} || cp {remote_server} {backup_server}")),
        ("backup current web build", ssh_cmd(device, f"test ! -d {remote_web} || cp -a {remote_web} {backup_web}")),
        ("upload server artifact", scp_cmd(device, device.server_artifact, remote_server)),
        ("upload web build", scp_cmd(device, f"{device.web_build_dir}/.", remote_web, recursive=True)),
        ("restart service", ssh_cmd(device, f"sudo systemctl restart {device.service_name}")),
        ("post-check /device", None),
        ("post-check /status", None),
    ]


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode == 0, proc.stdout.strip()


def http_check(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return response.status == 200, response.read(4096).decode("utf-8", errors="replace")
    except Exception as exc:
        return False, str(exc)


def deploy_device(device: Device, *, dry_run: bool) -> dict[str, Any]:
    steps = []
    ok = True
    for label, cmd in plan_for(device):
        if cmd is None:
            url = f"{device.base_url}/{label.rsplit('/', 1)[-1]}"
            if dry_run:
                steps.append({"step": label, "status": "dry-run", "command": f"GET {url}"})
            else:
                step_ok, output = http_check(url)
                ok = ok and step_ok
                steps.append({"step": label, "status": "ok" if step_ok else "failed", "output": output[:500]})
            continue
        if dry_run:
            steps.append({"step": label, "status": "dry-run", "command": command_text(cmd)})
            continue
        step_ok, output = run_cmd(cmd)
        ok = ok and step_ok
        steps.append({"step": label, "status": "ok" if step_ok else "failed", "output": output[:500]})
        if not step_ok:
            break
    return {"device": device.name, "host": device.host, "status": "ok" if ok else "failed", "steps": steps}


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy PolliPi server/web builds to a configured Pi fleet.")
    parser.add_argument("--config", type=Path, default=Path("tools/fleet.example.json"))
    parser.add_argument("--execute", action="store_true", help="Actually run ssh/scp/systemctl commands. Default is dry-run.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON results.")
    args = parser.parse_args()

    try:
      devices = load_devices(args.config)
    except Exception as exc:
      print(f"config error: {exc}", file=sys.stderr)
      return 2

    results = [deploy_device(device, dry_run=not args.execute) for device in devices]
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            print(f"{result['device']} ({result['host']}): {result['status']}")
            for step in result["steps"]:
                detail = step.get("command") or step.get("output", "")
                print(f"  - {step['status']}: {step['step']}{' -> ' + detail if detail else ''}")
    return 0 if all(result["status"] == "ok" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
