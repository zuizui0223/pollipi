"""Route handlers for the active scheduled-mesh capture API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pollipi_analysis.policy import (
    DEFAULT_POLICY_PROFILE_ID,
    get_policy_profile,
    list_policy_profiles,
)
from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.capture import (
    PolicyProfileResponse,
    PolicyProfilesResponse,
    StartRequest,
    StatusResponse,
)
from visit_monitor_server.services import get_controller

router = APIRouter(tags=["capture"])


def _validate_start(request: StartRequest) -> None:
    if request.adaptive_min_interval_sec > request.adaptive_max_interval_sec:
        raise HTTPException(
            status_code=422,
            detail="adaptive_min_interval_sec must not exceed adaptive_max_interval_sec.",
        )
    try:
        get_policy_profile(request.policy_profile_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"unknown policy_profile_id: {exc.args[0]}",
        ) from exc


@router.post("/start", response_model=StatusResponse, dependencies=[Depends(require_device_secret)])
def start_timelapse(request: StartRequest) -> StatusResponse:
    _validate_start(request)
    try:
        return get_controller().start(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/stop", response_model=StatusResponse, dependencies=[Depends(require_device_secret)])
def stop_timelapse() -> StatusResponse:
    return get_controller().stop()


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return get_controller().status()


@router.get("/policy-profiles", response_model=PolicyProfilesResponse)
def get_policy_profiles() -> PolicyProfilesResponse:
    return PolicyProfilesResponse(
        default_profile_id=DEFAULT_POLICY_PROFILE_ID,
        profiles=[
            PolicyProfileResponse(
                schema=profile.schema,
                profile_id=profile.profile_id,
                simulation_run_id=profile.simulation_run_id,
                source_commit=profile.source_commit,
                kind=profile.kind,
                parameters=dict(profile.parameters),
                description=profile.description,
            )
            for profile in list_policy_profiles()
        ],
    )
