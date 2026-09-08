from __future__ import annotations

from types import SimpleNamespace

import visit_monitor_server.app as app_module
from visit_monitor_server.services import audit_capture_instrumentation as instrumentation


class _InnerPolicy:
    def __init__(self) -> None:
        self.config = SimpleNamespace(value=1)

    def step(self, state: str, now: float):
        return SimpleNamespace(mode="HIGH" if state == "candidate" else "LOW", now=now)


def test_policy_proxy_forwards_attributes_and_observes_step() -> None:
    inner = _InnerPolicy()
    proxy = instrumentation._PolicyControllerProxy(inner)
    assert proxy.config.value == 1
    replacement = SimpleNamespace(value=2)
    proxy.config = replacement
    assert inner.config is replacement
    out = proxy.step("candidate", 3.0)
    assert out.mode == "HIGH"
    assert instrumentation._state.latest_policy_output is out
    instrumentation._clear_probe_state()


def test_app_factory_invokes_audit_installer(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        app_module,
        "install_audit_capture_instrumentation",
        lambda: calls.append(True),
    )
    app = app_module.create_app()
    assert app is not None
    assert calls == [True]
