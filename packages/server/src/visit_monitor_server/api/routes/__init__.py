"""Active route exports."""

from visit_monitor_server.api.routes.capture import router as capture_router
from visit_monitor_server.api.routes.device import router as device_router
from visit_monitor_server.api.routes.images import router as images_router
from visit_monitor_server.api.routes.preview import router as preview_router

__all__ = [
    "capture_router",
    "device_router",
    "images_router",
    "preview_router",
]
