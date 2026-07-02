from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select

from devices.model import Device
from devices.pi_client import PiClient
from orchestration.schemas import DeviceCommandResult, OrchestrationResponse, StartRequest
from sessions.model import ObservationSession, SessionDevice
from sessions.service import set_session_result
from utils.db import AsyncSessionLocal


async def start_devices(
    user_id: int,
    *,
    payload: StartRequest,
    device_ids: Optional[list[int]] = None,
    session_id: Optional[int] = None,
) -> OrchestrationResponse:
    devices = await resolve_devices(user_id, device_ids=device_ids, session_id=session_id)
    session_roles = await session_device_roles(session_id) if session_id is not None else {}
    base_payload = payload.model_dump(exclude_none=True)
    results = await asyncio.gather(
        *[
            _call_device(
                device,
                "POST",
                "/start",
                body={**base_payload, **({"camera_role": session_roles[device.id]} if session_roles.get(device.id) else {})},
                timeout=15,
            )
            for device in devices
        ]
    )
    response = OrchestrationResponse(ok=all(result.ok for result in results), results=results)
    if session_id is not None:
        await set_session_result(user_id, session_id, "running" if response.ok else "partial", response.model_dump())
    return response


async def stop_devices(
    user_id: int,
    *,
    device_ids: Optional[list[int]] = None,
    session_id: Optional[int] = None,
) -> OrchestrationResponse:
    devices = await resolve_devices(user_id, device_ids=device_ids, session_id=session_id)
    results = await asyncio.gather(*[_call_device(device, "POST", "/stop", timeout=15) for device in devices])
    response = OrchestrationResponse(ok=all(result.ok for result in results), results=results)
    if session_id is not None:
        await set_session_result(user_id, session_id, "stopped" if response.ok else "partial", response.model_dump())
    return response


async def status_devices(
    user_id: int,
    *,
    device_ids: Optional[list[int]] = None,
    session_id: Optional[int] = None,
) -> OrchestrationResponse:
    devices = await resolve_devices(user_id, device_ids=device_ids, session_id=session_id)
    results = await asyncio.gather(*[_call_device(device, "GET", "/status") for device in devices])
    return OrchestrationResponse(ok=all(result.ok for result in results), results=results)


async def resolve_devices(
    user_id: int,
    *,
    device_ids: Optional[list[int]] = None,
    session_id: Optional[int] = None,
) -> list[Device]:
    async with AsyncSessionLocal() as session:
        ids = device_ids
        if session_id is not None:
            session_result = await session.execute(
                select(ObservationSession).where(
                    ObservationSession.user_id == user_id,
                    ObservationSession.id == session_id,
                )
            )
            if session_result.scalar_one_or_none() is None:
                raise HTTPException(status_code=404, detail="Session not found.")
            link_result = await session.execute(
                select(SessionDevice.device_id).where(SessionDevice.session_id == session_id)
            )
            ids = [row[0] for row in link_result.all()]
        query = select(Device).where(Device.user_id == user_id)
        if ids is not None:
            if not ids:
                return []
            query = query.where(Device.id.in_(ids))
        result = await session.execute(query.order_by(Device.id))
        devices = list(result.scalars().all())
        for device in devices:
            session.expunge(device)
        if ids is not None and len(devices) != len(set(ids)):
            found = {device.id for device in devices}
            missing = sorted(set(ids) - found)
            raise HTTPException(status_code=404, detail=f"Device ids not found: {missing}")
        return devices


async def session_device_roles(session_id: Optional[int]) -> dict[int, str]:
    if session_id is None:
        return {}
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SessionDevice.device_id, SessionDevice.camera_role).where(SessionDevice.session_id == session_id)
        )
        return {device_id: role for device_id, role in result.all() if role}


async def _call_device(
    device: Device,
    method: str,
    path: str,
    *,
    body: Optional[dict[str, Any]] = None,
    timeout: float = 8,
) -> DeviceCommandResult:
    try:
        data = await PiClient(device.base_url, timeout=timeout).json(method, path, body=body)
        return DeviceCommandResult(device_id=device.id, ok=True, data=data)
    except HTTPException as exc:
        return DeviceCommandResult(device_id=device.id, ok=False, error=str(exc.detail))

