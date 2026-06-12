"""Route handlers for /training/*."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from visit_monitor_server.api.auth import require_device_secret
from visit_monitor_server.api.schemas.training import TrainingStatusResponse
from visit_monitor_server.services import get_controller, get_trainer

router = APIRouter(tags=["training"], dependencies=[Depends(require_device_secret)])


@router.get("/training/status", response_model=TrainingStatusResponse)
def get_training_status() -> TrainingStatusResponse:
    return get_trainer().status()


@router.post("/training/start", response_model=TrainingStatusResponse)
def start_training() -> TrainingStatusResponse:
    if get_controller().status().running:
        raise HTTPException(
            status_code=409,
            detail="Stop field observation before training to save power.",
        )
    try:
        return get_trainer().start()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/training/model", response_model=TrainingStatusResponse)
def discard_training_model() -> TrainingStatusResponse:
    try:
        return get_trainer().reset_model()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
