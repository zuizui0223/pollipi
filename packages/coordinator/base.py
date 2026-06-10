from typing import Union, Optional

import asyncio
from pydantic import BaseModel, Field
from fastapi import FastAPI

from constants import Codes, getDescription

__, _def_desc, _ = getDescription(Codes.DONE)


class BaseResponseModel(BaseModel):
    code: int = Field(default=Codes.DONE)
    info: str = Field(default=_def_desc)
    detail: Optional[Union[dict, list, str]] = Field(default=None)


class TokenResponseModel(BaseResponseModel):
    tokens: Optional[dict] = Field(default=None)
    access_token: Optional[str] = None


# app

app = FastAPI()


@app.get("/api", response_model_exclude_none=True)
async def api_root() -> BaseResponseModel:
    return BaseResponseModel(detail="Server is Running.")
