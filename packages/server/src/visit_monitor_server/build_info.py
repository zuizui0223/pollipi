"""Build metadata helpers for device/version visibility."""
from __future__ import annotations

import os


EMBEDDED_APP_VERSION = "0.1.0"
EMBEDDED_GIT_COMMIT = ""
EMBEDDED_BUILD_TIMESTAMP = ""
EMBEDDED_DEPLOYMENT_MODE = ""
EMBEDDED_WEB_BUILD_ID = ""


def _value(env_name: str, embedded: str, default: str = "unknown") -> str:
    value = os.getenv(env_name, "").strip() or embedded.strip()
    return value or default


def get_build_info() -> dict[str, str]:
    """Return build metadata without touching the camera stack."""
    return {
        "app_version": _value("POLLIPI_APP_VERSION", EMBEDDED_APP_VERSION),
        "git_commit": _value("POLLIPI_GIT_COMMIT", EMBEDDED_GIT_COMMIT),
        "build_timestamp": _value("POLLIPI_BUILD_TIMESTAMP", EMBEDDED_BUILD_TIMESTAMP),
        "deployment_mode": _value("POLLIPI_DEPLOYMENT_MODE", EMBEDDED_DEPLOYMENT_MODE),
        "web_build_id": _value("POLLIPI_WEB_BUILD_ID", EMBEDDED_WEB_BUILD_ID),
    }
