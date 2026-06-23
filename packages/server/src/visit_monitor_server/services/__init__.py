"""Services sub-package."""
from visit_monitor_server.services.controller import TimelapseController

# Module-level singletons referenced by the app factory / capture loop
_controller_singleton: TimelapseController | None = None  # set by app factory


def get_controller() -> TimelapseController:
    assert _controller_singleton is not None, "Controller not initialised"
    return _controller_singleton


__all__ = [
    "TimelapseController",
    "get_controller",
]
