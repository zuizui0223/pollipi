"""PMIC input-voltage parsing + graceful fallback for the power indicator.

A plain USB power bank has no fuel gauge, so the web "battery" indicator falls
back to the Pi 5 input 5V-rail voltage (EXT5V_V) as a health proxy. These tests
pin the parse and the no-PMIC path (older Pi / non-Pi host) so the endpoint
never raises and the schema field is always populated (float or None).
"""
from __future__ import annotations

import subprocess

from visit_monitor_server.adapters import system_info

_PMIC_SAMPLE = """ 3V7_WL_SW_A current(0)=0.11320790A
 VDD_CORE_A current(7)=0.62510000A
 3V7_WL_SW_V volt(8)=3.72761500V
     EXT5V_V volt(24)=5.06386000V
"""


def _fake_run(stdout: str):
    def run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["vcgencmd"], returncode=0, stdout=stdout)

    return run


def test_supply_voltage_parses_ext5v(monkeypatch) -> None:
    monkeypatch.setattr(system_info.subprocess, "run", _fake_run(_PMIC_SAMPLE))
    assert system_info.supply_voltage_v() == 5.064


def test_supply_voltage_none_without_pmic(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise FileNotFoundError("vcgencmd")

    monkeypatch.setattr(system_info.subprocess, "run", boom)
    assert system_info.supply_voltage_v() is None


def test_supply_voltage_none_on_unexpected_output(monkeypatch) -> None:
    monkeypatch.setattr(system_info.subprocess, "run", _fake_run("no adc here\n"))
    assert system_info.supply_voltage_v() is None


def test_throttle_status_includes_voltage_and_message(monkeypatch) -> None:
    calls = {"n": 0}

    def run(args, **_kwargs):
        calls["n"] += 1
        if args[:2] == ["vcgencmd", "pmic_read_adc"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=_PMIC_SAMPLE)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="throttled=0x0\n")

    monkeypatch.setattr(system_info.subprocess, "run", run)
    out = system_info.throttle_status()
    assert out["supply_voltage_v"] == 5.064
    assert out["undervoltage_now"] is False
    assert out["undervoltage_occurred"] is False
    assert "5.06V" in out["power_message"]
