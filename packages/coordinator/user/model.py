import uuid
from datetime import datetime, timezone, timedelta

from typing import Optional, Tuple

from sqlalchemy import select, update, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from constants import Codes, UserGroup
from utils.db import Base, AsyncSessionLocal

import user.format as f


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.fromtimestamp(0, tz=timezone.utc),
    )
    tokens_valid_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0) - timedelta(seconds=5),
    )
    username: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    group: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    async def set_username(self, username: str, save=True):
        if not f.is_valid_username(username):
            return Codes.ERR_INVALID_USERNAME
        self.username = username
        if save:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(User).where(User.id == self.id).values(username=username)
                )
                await session.commit()
        return Codes.DONE

    async def set_password(self, password: str, save=True):
        if not f.is_valid_password(password):
            return Codes.ERR_INVALID_PASSWORD
        self.pw_hash = f.encode_password(password)
        self.updated_at = datetime.now(tz=timezone.utc)
        self.tokens_valid_after = datetime.now(tz=timezone.utc).replace(microsecond=0)
        if save:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(User)
                    .where(User.id == self.id)
                    .values(
                        pw_hash=self.pw_hash,
                        updated_at=self.updated_at,
                        tokens_valid_after=self.tokens_valid_after
                    )
                )
                await session.commit()
        return Codes.DONE


guest_user = User(
    email="__guest__",
    pw_hash="",
    username="guest",
    group=UserGroup.Guest,
    updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
    tokens_valid_after=datetime.fromtimestamp(0, tz=timezone.utc),
)


async def ensure_root_user() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "__root__"))
        if result.scalar_one_or_none() is not None:
            return
        root_pw = str(uuid.uuid1())
        session.add(
            User(
                email="__root__",
                username="root",
                pw_hash=f.encode_password(root_pw),
                updated_at=datetime.now(tz=timezone.utc),
                tokens_valid_after=datetime.now(tz=timezone.utc).replace(microsecond=0) - timedelta(seconds=5),
                group=UserGroup.Root,
            )
        )
        await session.commit()
        import os
        root_pwd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "root_pwd.txt")
        with open(root_pwd_path, "w", encoding="utf-8") as fp:
            fp.write(root_pw)


async def create_user(
    email: str, username: str, password: str, group: str = UserGroup.User
):
    if not f.is_valid_email(email):
        return Codes.ERR_INVALID_EMAIL
    if not f.is_valid_username(username):
        return Codes.ERR_INVALID_USERNAME
    if not f.is_valid_password(password):
        return Codes.ERR_INVALID_PASSWORD

    pw_hash = f.encode_password(password)

    try:
        async with AsyncSessionLocal() as session:
            session.add(
                User(
                    email=email,
                    username=username,
                    pw_hash=pw_hash,
                    updated_at=datetime.now(tz=timezone.utc),
                    tokens_valid_after=datetime.now(tz=timezone.utc).replace(microsecond=0) - timedelta(seconds=5),
                    group=group,
                )
            )
            await session.commit()
        return Codes.DONE
    except IntegrityError:
        return Codes.ERR_EXISTENT_EMAIL


async def authenticate_user(email: str, password: str) -> Tuple[int, Optional[User]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    if user is None:
        return Codes.ERR_WRONG_UNAME_OR_PW, None
    if f.verify_password(password, user.pw_hash):
        return Codes.DONE, user
    return Codes.ERR_WRONG_UNAME_OR_PW, None


async def get_user(email: str) -> Optional[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
