import os
from fastapi.logger import logger
from dotenv import load_dotenv
from pydantic import BaseModel, field_serializer, Field, field_validator
from pydantic_yaml import parse_yaml_file_as, to_yaml_file
from datetime import timedelta
from typing import Dict, Union, List

from utils.data import parse_timedelta, create_timedelta_str

__all__ = ["AppConfigModel", "AppConfig", "EnvConfig"]


class AppConfigModel(BaseModel):

    JwtSecretKey: str = "JWT Secret Key"
    HmacSalt: bytes = b"HMAC Salt"

    AccessTokenExpires: timedelta = parse_timedelta("5min")
    RefreshTokenExpires: timedelta = parse_timedelta("180d")

    # TODO

    TokenAccessOverride: Dict[str, Union[str, List[str]]] = Field(default_factory=dict)

    RestrictLanguage: bool = False  # to avoid strange language recognition
    AllowedLanguages: List[str] = ["zh", "en", "jp"]
    TranslationTarget: str = "en"

    @field_serializer("AccessTokenExpires", "RefreshTokenExpires")
    def serialize_timedelta(self, delta: timedelta):
        return create_timedelta_str(delta)

    @field_validator("AccessTokenExpires", "RefreshTokenExpires", mode="before")
    @classmethod
    def validate_timedelta(cls, delta: str):
        if isinstance(delta, timedelta):
            return delta
        return parse_timedelta(delta)


# environment variables

load_dotenv()


def _parse_bool(val: str, default: bool = False) -> bool:
    if not val:
        return default
    return val.strip().lower() not in {"0", "false", "none", "null"}


mount_static_str = os.environ.get("MOUNT_STATIC", "")
mount_static = _parse_bool(mount_static_str)

allow_lan_str = os.environ.get("ALLOW_LAN", "")
allow_lan = _parse_bool(allow_lan_str)

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "visit-monitor.db"
)
db_url = os.environ.get("DB_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}")


class EnvConfig:
    mount_static = mount_static
    allow_lan = allow_lan
    db_url = db_url


# app config

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

try:
    AppConfig = parse_yaml_file_as(AppConfigModel, _CONFIG_PATH)
except Exception as e:
    logger.warning(e)
    AppConfig = AppConfigModel()
    if not os.path.exists(_CONFIG_PATH):
        to_yaml_file(_CONFIG_PATH, AppConfig)
