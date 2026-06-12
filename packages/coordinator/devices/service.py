from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from devices.model import Device
from devices.pi_client import PiClient
from devices.schemas import DeviceCreateRequest, DeviceResponse, DeviceUpdateRequest
from utils.db import AsyncSessionLocal


def normalize_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="base_url must start with http:// or https://")
    return value


def normalize_device_secret(device_secret: str | None) -> str | None:
    value = (device_secret or "").strip()
    return value or None


def pi_client(device: Device, timeout: float = 8.0) -> PiClient:
    return PiClient(device.base_url, timeout=timeout, device_secret=device.device_secret)


async def probe_pi(base_url: str, device_secret: str | None = None) -> dict[str, Any]:
    return await PiClient(base_url, device_secret=device_secret).json("GET", "/device")


async def create_device(user_id: int, request: DeviceCreateRequest) -> DeviceResponse:
    base_url = normalize_base_url(request.base_url)
    device_secret = normalize_device_secret(request.device_secret)
    metadata = await probe_pi(base_url, device_secret) if request.verify_connection else {}
    device_id = str(metadata.get("device_id") or request.display_name or base_url)
    device = Device(
        user_id=user_id,
        address=request.address,
        base_url=base_url,
        device_secret=device_secret,
        device_id=device_id,
        device_name=str(metadata.get("device_name") or request.display_name or device_id),
        display_name=str(request.display_name or metadata.get("camera_label") or metadata.get("device_name") or device_id),
        camera_label=str(metadata.get("camera_label") or request.display_name or "PolliPi Camera"),
        camera_model=str(metadata.get("camera_model") or ""),
        camera_profile=str(metadata.get("camera_profile") or ""),
        is_ai_camera=bool(metadata.get("is_ai_camera")),
        is_noir=bool(metadata.get("is_noir")),
        is_wide=bool(metadata.get("is_wide")),
        last_seen_at=datetime.now(tz=timezone.utc) if metadata else None,
    )
    try:
        async with AsyncSessionLocal() as session:
            session.add(device)
            await session.commit()
            await session.refresh(device)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Device already exists for this user.") from exc
    return to_response(device)


async def list_devices(user_id: int) -> list[DeviceResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Device).where(Device.user_id == user_id).order_by(Device.id))
        return [to_response(device) for device in result.scalars().all()]


async def get_device(user_id: int, device_id: int) -> Device:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(Device.user_id == user_id, Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
        session.expunge(device)
        return device


async def update_device(user_id: int, device_id: int, request: DeviceUpdateRequest) -> DeviceResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(Device.user_id == user_id, Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
        if request.base_url is not None:
            device.base_url = normalize_base_url(request.base_url)
        if request.device_secret is not None:
            device.device_secret = normalize_device_secret(request.device_secret)
        if request.address is not None:
            device.address = request.address
        if request.display_name is not None:
            device.display_name = request.display_name
        if request.verify_connection:
            metadata = await probe_pi(device.base_url, device.device_secret)
            apply_device_metadata(device, metadata)
        await session.commit()
        await session.refresh(device)
        return to_response(device)


async def delete_device(user_id: int, device_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Device).where(Device.user_id == user_id, Device.id == device_id)
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Device not found.")


async def refresh_device_status(user_id: int, device_id: int) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(Device.user_id == user_id, Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
        try:
            status = await pi_client(device).json("GET", "/status")
            device.last_status = status
            device.last_error = None
            device.last_seen_at = datetime.now(tz=timezone.utc)
            await session.commit()
            return status
        except HTTPException as exc:
            device.last_error = str(exc.detail)
            await session.commit()
            raise


def apply_device_metadata(device: Device, metadata: dict[str, Any]) -> None:
    device.device_id = str(metadata.get("device_id") or device.device_id)
    device.device_name = str(metadata.get("device_name") or device.device_name)
    device.camera_label = str(metadata.get("camera_label") or device.camera_label)
    device.camera_model = str(metadata.get("camera_model") or device.camera_model)
    device.camera_profile = str(metadata.get("camera_profile") or device.camera_profile)
    device.is_ai_camera = bool(metadata.get("is_ai_camera"))
    device.is_noir = bool(metadata.get("is_noir"))
    device.is_wide = bool(metadata.get("is_wide"))
    device.last_seen_at = datetime.now(tz=timezone.utc)
    if not device.display_name:
        device.display_name = device.camera_label or device.device_name or device.device_id


def to_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        address=device.address,
        base_url=device.base_url,
        api_path_prefix=f"/api/devices/{device.id}",
        device_id=device.device_id,
        device_name=device.device_name,
        display_name=device.display_name,
        camera_label=device.camera_label,
        camera_model=device.camera_model,
        camera_profile=device.camera_profile,
        is_ai_camera=device.is_ai_camera,
        is_noir=device.is_noir,
        is_wide=device.is_wide,
        last_status=device.last_status,
        last_error=device.last_error,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )

