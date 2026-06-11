from __future__ import annotations

from fastapi import Depends

from base import app
from constants import Token
from orchestration.schemas import (
    OrchestrationResponse,
    OrchestrationStartRequest,
    OrchestrationStatusRequest,
    OrchestrationStopRequest,
)
from orchestration.service import start_devices, status_devices, stop_devices
from user.auth import CurrentUser
from user.model import User


@app.post("/api/orchestration/start", response_model=OrchestrationResponse)
async def api_orchestration_start(
    request: OrchestrationStartRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> OrchestrationResponse:
    return await start_devices(
        user.id,
        payload=request.payload,
        device_ids=request.device_ids,
        session_id=request.session_id,
    )


@app.post("/api/orchestration/stop", response_model=OrchestrationResponse)
async def api_orchestration_stop(
    request: OrchestrationStopRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> OrchestrationResponse:
    return await stop_devices(user.id, device_ids=request.device_ids, session_id=request.session_id)


@app.post("/api/orchestration/status", response_model=OrchestrationResponse)
async def api_orchestration_status(
    request: OrchestrationStatusRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> OrchestrationResponse:
    return await status_devices(user.id, device_ids=request.device_ids, session_id=request.session_id)

