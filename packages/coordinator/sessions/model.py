from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from utils.db import Base


class ObservationSession(Base):
    __tablename__ = "observation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    site_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    flower_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    plant_species: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    observer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    comparison_session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    method_mode: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    interval_sec: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    auto_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motion_trigger_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hybrid_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ml_assist_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    autonomous_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idle_interval_sec: Mapped[float] = mapped_column(Float, nullable=False, default=60.0)
    detection_interval_sec: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    pixel_difference: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    motion_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.01)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    last_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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


class SessionDevice(Base):
    __tablename__ = "session_devices"
    __table_args__ = (
        UniqueConstraint("session_id", "device_id", name="uq_session_devices_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("observation_sessions.id"), index=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True, nullable=False)
    camera_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

