from __future__ import annotations

from fastapi import Depends
from fastapi.responses import Response

from base import app
from constants import Token
from sessions.schemas import (
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SessionUpdateRequest,
)
from sessions.service import (
    create_session,
    delete_session,
    get_session_response,
    list_sessions,
    update_session,
)
from user.auth import CurrentUser
from user.model import User


@app.get("/api/sessions", response_model=SessionListResponse)
async def api_list_sessions(user: User = Depends(CurrentUser(Token.Access.General))) -> SessionListResponse:
    return SessionListResponse(sessions=await list_sessions(user.id))


@app.post("/api/sessions", response_model=SessionResponse)
async def api_create_session(
    request: SessionCreateRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> SessionResponse:
    return await create_session(user.id, request)


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def api_get_session(
    session_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> SessionResponse:
    return await get_session_response(user.id, session_id)


@app.put("/api/sessions/{session_id}", response_model=SessionResponse)
async def api_update_session(
    session_id: int,
    request: SessionUpdateRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> SessionResponse:
    return await update_session(user.id, session_id, request)


@app.delete("/api/sessions/{session_id}", status_code=204)
async def api_delete_session(
    session_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    await delete_session(user.id, session_id)
    return Response(status_code=204)

