"""FastAPI application factory for the active PolliPi timelapse server."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from visit_monitor_server import __version__
from visit_monitor_server.api.router import router
from visit_monitor_server.config import IMAGE_DIR, WEB_DIR
from visit_monitor_server.services import TimelapseController
import visit_monitor_server.services as _services


def create_app() -> FastAPI:
    """Create the scheduled-image mesh-shadow API."""
    controller = TimelapseController(IMAGE_DIR)
    _services._controller_singleton = controller

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        controller.resume_autonomous()
        yield
        controller.stop(preserve_autonomous=True)

    app = FastAPI(
        title="PolliPi Timelapse API",
        version=__version__,
        description="Local-first scheduled timelapse and mesh shadow logging for field observation.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    if WEB_DIR.is_dir():
        app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web-app")

    @app.get("/", include_in_schema=False)
    def open_app() -> RedirectResponse:
        return RedirectResponse(url="/app/")

    app.include_router(router)
    return app
