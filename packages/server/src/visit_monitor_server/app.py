"""FastAPI application factory for the PolliPi visit-monitor server."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from visit_monitor_server import __version__
from visit_monitor_server.api.router import router
from visit_monitor_server.config import ENABLE_LEGACY_ROUTES, IMAGE_DIR, WEB_DIR
from visit_monitor_server.services import TimelapseController
import visit_monitor_server.services as _services


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    controller = TimelapseController(IMAGE_DIR)

    # Register the controller singleton so route handlers can call get_controller()
    _services._controller_singleton = controller

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if ENABLE_LEGACY_ROUTES:
            controller.migrate_legacy_candidates()
        controller.resume_autonomous()
        yield
        controller.stop(preserve_autonomous=True)

    app = FastAPI(
        title="PolliPi Timelapse API",
        version=__version__,
        description="Device backend for field monitoring of insect visitation.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    # Static web app (optional – only mounted when the build artefact exists)
    if WEB_DIR.is_dir():
        app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web-app")

    @app.get("/", include_in_schema=False)
    def open_app() -> RedirectResponse:
        return RedirectResponse(url="/app/")

    app.include_router(router)

    return app
