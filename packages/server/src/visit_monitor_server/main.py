from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from visit_monitor_server import __version__
from visit_monitor_server.api import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Visit Monitor Server",
        version=__version__,
        description="Device backend for field monitoring of insect visitation.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
