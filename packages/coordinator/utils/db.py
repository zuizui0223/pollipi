import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "visit-monitor.db")
_DB_URL = os.environ.get("DB_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}")

engine = create_async_engine(_DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def init_db(base=None):
    if base is None:
        base = Base
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
