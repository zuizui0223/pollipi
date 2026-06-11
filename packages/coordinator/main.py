import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from base import app, BaseResponseModel, startup_tasks

import user
import devices
import sessions
import orchestration

from config import EnvConfig
from user.model import ensure_root_user
from utils.db import init_db


async def startup() -> None:
    await init_db()
    await ensure_root_user()


startup_tasks.append(startup)

if EnvConfig.mount_static:
    _CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    _WWWROOT_DIR = os.path.join(_CURRENT_DIR, "wwwroot")

    @app.get("/")
    async def root(): # type: ignore
        return FileResponse(os.path.join(_WWWROOT_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=_WWWROOT_DIR), name="static")

else:

    @app.get("/")
    async def root():
        return BaseResponseModel(detail="This is the root API entry point.")
