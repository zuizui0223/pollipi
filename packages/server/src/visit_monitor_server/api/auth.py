"""Optional device-secret authentication for protected Pi endpoints."""
from __future__ import annotations

from secrets import compare_digest

from fastapi import Header, HTTPException, status

from visit_monitor_server.config import DEVICE_SECRET

DEVICE_SECRET_HEADER = "X-Pollipi-Device-Secret"


def require_device_secret(
    x_pollipi_device_secret: str | None = Header(default=None, alias=DEVICE_SECRET_HEADER),
) -> None:
    """Require the configured device secret when POLLIPI_DEVICE_SECRET is set.

    Local direct field deployments can leave POLLIPI_DEVICE_SECRET unset and keep
    the historical unauthenticated LAN behavior. Remote/coordinator deployments
    should set the secret and have the coordinator attach it to protected calls.
    """
    expected = DEVICE_SECRET
    if not expected:
        return
    if not x_pollipi_device_secret or not compare_digest(x_pollipi_device_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid PolliPi device secret.",
        )
