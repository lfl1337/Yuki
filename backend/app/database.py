"""Async SQLAlchemy engine, session factory, init_db with legacy JSON migration."""

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import settings
from .models import Base, HistoryEntry, Setting

logger = logging.getLogger("yuki.database")

engine = create_async_engine(settings.db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized: %s", settings.db_url)
    await _migrate_legacy()


async def _migrate_legacy() -> None:
    """One-time migration from legacy JSON files to SQLite on first run."""
    data_dir = Path(settings.data_dir)

    # History migration
    old_history = data_dir / "history.json"
    if old_history.exists():
        async with AsyncSessionLocal() as s:
            count = await s.scalar(select(func.count(HistoryEntry.id)))
            if count == 0:
                try:
                    entries = json.loads(old_history.read_text(encoding="utf-8"))
                    valid_cols = {c.name for c in HistoryEntry.__table__.columns}
                    migrated = 0
                    for e in entries:
                        filtered = {k: v for k, v in e.items() if k in valid_cols}
                        filtered.setdefault("id", str(uuid4()))
                        filtered.setdefault("downloaded_at", datetime.now().isoformat())
                        s.add(HistoryEntry(**filtered))
                        migrated += 1
                    await s.commit()
                    logger.info("Migrated %d history entries from legacy JSON", migrated)
                    old_history.rename(data_dir / "history.json.legacy")
                except Exception as exc:
                    logger.error("History migration failed: %s", exc)

    # Settings migration
    old_settings = data_dir / "settings.json"
    if old_settings.exists():
        async with AsyncSessionLocal() as s:
            count = await s.scalar(select(func.count(Setting.key)))
            if count == 0:
                try:
                    cfg = json.loads(old_settings.read_text(encoding="utf-8"))
                    for k, v in cfg.items():
                        s.add(Setting(key=k, value=json.dumps(v)))
                    await s.commit()
                    logger.info("Migrated %d settings from legacy JSON", len(cfg))
                    old_settings.rename(data_dir / "settings.json.legacy")
                except Exception as exc:
                    logger.error("Settings migration failed: %s", exc)
