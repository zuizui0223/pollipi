"""Master API router that aggregates all domain routers."""
from __future__ import annotations

from fastapi import APIRouter

from visit_monitor_server.api.routes.capture import router as capture_router
from visit_monitor_server.api.routes.device import router as device_router
from visit_monitor_server.api.routes.images import router as images_router
from visit_monitor_server.api.routes.preview import router as preview_router
from visit_monitor_server.config import ENABLE_LEGACY_ROUTES

router = APIRouter()

for _sub in (
    capture_router,
    device_router,
    images_router,
    preview_router,
):
    router.include_router(_sub)

if ENABLE_LEGACY_ROUTES:
    from visit_monitor_server.api.routes.events import router as events_router
    from visit_monitor_server.api.routes.roi import router as roi_router
    from visit_monitor_server.api.routes.training import router as training_router

    compat_router = APIRouter(prefix="/compat", tags=["compat"])
    for _sub in (events_router, roi_router, training_router):
        compat_router.include_router(_sub)
    router.include_router(compat_router)
