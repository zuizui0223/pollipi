from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _clear_modules() -> None:
    prefixes = (
        "base",
        "config",
        "constants",
        "devices",
        "main",
        "orchestration",
        "sessions",
        "user",
        "utils",
    )
    for name in list(sys.modules):
        if name in prefixes or name.startswith(tuple(prefix + "." for prefix in prefixes)):
            sys.modules.pop(name)


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "coordinator.db"
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    _clear_modules()
    main = importlib.import_module("main")
    return TestClient(main.app)


def _register_and_login(client: TestClient) -> str:
    response = client.post(
        "/api/user/register",
        json={"email": "field@example.com", "username": "fielduser", "password": "secret1"},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        "/api/user/login",
        json={"username": "field@example.com", "password": "secret1"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert token
    return token


def test_user_device_session_and_orchestration_smoke(monkeypatch, tmp_path: Path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        token = _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/user/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "field@example.com"

        device = client.post(
            "/api/devices",
            headers=headers,
            json={
                "address": "pi@pollipi-test",
                "base_url": "http://127.0.0.1:9",
                "display_name": "Offline test Pi",
                "device_secret": "stored-but-not-returned",
                "verify_connection": False,
            },
        )
        assert device.status_code == 200, device.text
        device_payload = device.json()
        device_id = device_payload["id"]
        assert device_payload["api_path_prefix"] == f"/api/devices/{device_id}"
        assert "device_secret" not in device_payload
        assert "stored-but-not-returned" not in device.text

        listing = client.get("/api/devices", headers=headers)
        assert listing.status_code == 200
        listing_payload = listing.json()
        assert len(listing_payload["devices"]) == 1
        assert "device_secret" not in listing_payload["devices"][0]
        assert "stored-but-not-returned" not in listing.text

        session = client.post(
            "/api/sessions",
            headers=headers,
            json={
                "name": "Plot A morning",
                "site_id": "site_A",
                "interval_sec": 10,
                "devices": [{"device_id": device_id, "camera_role": "module3_reference"}],
            },
        )
        assert session.status_code == 200, session.text
        session_id = session.json()["id"]

        status = client.post(
            "/api/orchestration/status",
            headers=headers,
            json={"session_id": session_id},
        )
        assert status.status_code == 200, status.text
        payload = status.json()
        assert payload["ok"] is False
        assert payload["results"][0]["device_id"] == device_id
        assert payload["results"][0]["ok"] is False

