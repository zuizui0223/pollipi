"""Services sub-package."""
from visit_monitor_server.services.controller import TimelapseController
from visit_monitor_server.services.training import BinaryTrainer

# Module-level singletons referenced by the capture loop
_trainer_singleton = BinaryTrainer()
_controller_singleton: TimelapseController | None = None  # set by app factory


def get_controller() -> TimelapseController:
    assert _controller_singleton is not None, "Controller not initialised"
    return _controller_singleton


def get_trainer() -> BinaryTrainer:
    return _trainer_singleton


__all__ = [
    "TimelapseController",
    "BinaryTrainer",
    "get_controller",
    "get_trainer",
]
