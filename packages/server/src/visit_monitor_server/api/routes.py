from fastapi import APIRouter

from visit_monitor_server import __version__
from visit_monitor_server.api.schemas import HealthResponse, RuntimeStatusResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse(version=__version__)


@router.get("/api/v1/runtime/status", response_model=RuntimeStatusResponse, tags=["runtime"])
def runtime_status() -> RuntimeStatusResponse:
    return RuntimeStatusResponse()
