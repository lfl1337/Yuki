"""SQLAlchemy ORM models for Yuki."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class HistoryEntry(Base):
    __tablename__ = "history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(Text, default="")
    artist: Mapped[str] = mapped_column(Text, default="")
    platform: Mapped[str] = mapped_column(String(64), default="")
    format: Mapped[str] = mapped_column(String(16), default="audio")
    quality: Mapped[str] = mapped_column(String(32), default="")
    filepath: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    filesize: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(Text, default="")
    downloaded_at: Mapped[str] = mapped_column(
        String(32), default=lambda: datetime.now().isoformat()
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
