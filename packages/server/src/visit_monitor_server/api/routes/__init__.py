"""Routes sub-package."""
from visit_monitor_server.api.routes.capture import router as capture_router
from visit_monitor_server.api.routes.device import router as device_router
from visit_monitor_server.api.routes.events import router as events_router
from visit_monitor_server.api.routes.images import router as images_router
from visit_monitor_server.api.routes.preview import router as preview_router
from visit_monitor_server.api.routes.roi import router as roi_router
from visit_monitor_server.api.routes.training import router as training_router

__all__ = [
    "capture_router",
    "device_router",
    "events_router",
    "images_router",
    "preview_router",
    "roi_router",
    "training_router",
]
