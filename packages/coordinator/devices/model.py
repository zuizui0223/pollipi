from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from utils.db import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_devices_user_device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    camera_label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    camera_model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    camera_profile: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    is_ai_camera: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_noir: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_wide: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_status: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

