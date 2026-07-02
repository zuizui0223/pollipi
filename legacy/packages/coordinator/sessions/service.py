from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select

from devices.model import Device
from sessions.model import ObservationSession, SessionDevice
from sessions.schemas import (
    SessionCreateRequest,
    SessionDeviceResponse,
    SessionResponse,
    SessionUpdateRequest,
)
from utils.db import AsyncSessionLocal


async def create_session(user_id: int, request: SessionCreateRequest) -> SessionResponse:
    async with AsyncSessionLocal() as session:
        await _ensure_devices_owned(session, user_id, [item.device_id for item in request.devices])
        obs = ObservationSession(user_id=user_id)
        _apply_session_fields(obs, request)
        session.add(obs)
        await session.flush()
        for item in request.devices:
            session.add(SessionDevice(session_id=obs.id, device_id=item.device_id, camera_role=item.camera_role))
        await session.commit()
        return await get_session_response(user_id, obs.id)


async def list_sessions(user_id: int) -> list[SessionResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ObservationSession).where(ObservationSession.user_id == user_id).order_by(ObservationSession.id.desc())
        )
        ids = [obs.id for obs in result.scalars().all()]
    return [await get_session_response(user_id, session_id) for session_id in ids]


async def get_session_response(user_id: int, session_id: int) -> SessionResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ObservationSession).where(
                ObservationSession.user_id == user_id,
                ObservationSession.id == session_id,
            )
        )
        obs = result.scalar_one_or_none()
        if obs is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        devices_result = await session.execute(
            select(SessionDevice).where(SessionDevice.session_id == obs.id).order_by(SessionDevice.id)
        )
        devices = devices_result.scalars().all()
        return to_response(obs, devices)


async def update_session(user_id: int, session_id: int, request: SessionUpdateRequest) -> SessionResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ObservationSession).where(
                ObservationSession.user_id == user_id,
                ObservationSession.id == session_id,
            )
        )
        obs = result.scalar_one_or_none()
        if obs is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        if obs.status == "running":
            raise HTTPException(status_code=409, detail="Stop the session before editing it.")
        await _ensure_devices_owned(session, user_id, [item.device_id for item in request.devices])
        _apply_session_fields(obs, request)
        await session.execute(delete(SessionDevice).where(SessionDevice.session_id == obs.id))
        for item in request.devices:
            session.add(SessionDevice(session_id=obs.id, device_id=item.device_id, camera_role=item.camera_role))
        await session.commit()
    return await get_session_response(user_id, session_id)


async def delete_session(user_id: int, session_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ObservationSession).where(
                ObservationSession.user_id == user_id,
                ObservationSession.id == session_id,
            )
        )
        obs = result.scalar_one_or_none()
        if obs is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        if obs.status == "running":
            raise HTTPException(status_code=409, detail="Stop the session before deleting it.")
        await session.execute(delete(SessionDevice).where(SessionDevice.session_id == obs.id))
        await session.delete(obs)
        await session.commit()


async def set_session_result(user_id: int, session_id: int, status: str, result: dict) -> SessionResponse:
    async with AsyncSessionLocal() as session:
        db_result = await session.execute(
            select(ObservationSession).where(
                ObservationSession.user_id == user_id,
                ObservationSession.id == session_id,
            )
        )
        obs = db_result.scalar_one_or_none()
        if obs is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        obs.status = status
        obs.last_result = result
        now = datetime.now(tz=timezone.utc)
        if status == "running":
            obs.started_at = now
        if status == "stopped":
            obs.stopped_at = now
        await session.commit()
    return await get_session_response(user_id, session_id)


async def _ensure_devices_owned(session, user_id: int, device_ids: list[int]) -> None:
    if not device_ids:
        return
    result = await session.execute(select(Device.id).where(Device.user_id == user_id, Device.id.in_(device_ids)))
    owned = {item[0] for item in result.all()}
    missing = sorted(set(device_ids) - owned)
    if missing:
        raise HTTPException(status_code=404, detail=f"Device ids not found: {missing}")


def _apply_session_fields(obs: ObservationSession, request: SessionCreateRequest) -> None:
    for field in (
        "name",
        "site_id",
        "flower_id",
        "plant_species",
        "observer",
        "notes",
        "comparison_session_id",
        "method_mode",
        "interval_sec",
        "auto_mode",
        "motion_trigger_mode",
        "hybrid_mode",
        "ml_assist_mode",
        "autonomous_mode",
        "idle_interval_sec",
        "detection_interval_sec",
        "pixel_difference",
        "motion_ratio",
    ):
        setattr(obs, field, getattr(request, field))


def to_response(obs: ObservationSession, devices: list[SessionDevice]) -> SessionResponse:
    return SessionResponse(
        id=obs.id,
        name=obs.name,
        status=obs.status,
        devices=[
            SessionDeviceResponse(device_id=device.device_id, camera_role=device.camera_role)
            for device in devices
        ],
        site_id=obs.site_id,
        flower_id=obs.flower_id,
        plant_species=obs.plant_species,
        observer=obs.observer,
        notes=obs.notes,
        comparison_session_id=obs.comparison_session_id,
        method_mode=obs.method_mode,
        interval_sec=obs.interval_sec,
        auto_mode=obs.auto_mode,
        motion_trigger_mode=obs.motion_trigger_mode,
        hybrid_mode=obs.hybrid_mode,
        ml_assist_mode=obs.ml_assist_mode,
        autonomous_mode=obs.autonomous_mode,
        idle_interval_sec=obs.idle_interval_sec,
        detection_interval_sec=obs.detection_interval_sec,
        pixel_difference=obs.pixel_difference,
        motion_ratio=obs.motion_ratio,
        last_result=obs.last_result,
        started_at=obs.started_at,
        stopped_at=obs.stopped_at,
        created_at=obs.created_at,
        updated_at=obs.updated_at,
    )

