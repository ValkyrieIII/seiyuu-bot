"""Best-effort raw request-log retention."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from bot.config import settings


class RetentionManager:
    def __init__(self, days: int = 30, interval_hours: int = 24) -> None:
        self.days = days
        self.interval_seconds = interval_hours * 3600
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="request-log-retention")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _run(self) -> None:
        while True:
            try:
                deleted = await asyncio.to_thread(self.cleanup_once)
                if deleted:
                    logger.info("已清理 {} 条过期原始请求日志", deleted)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.opt(exception=True).warning("原始请求日志留存清理失败")
            await asyncio.sleep(self.interval_seconds)

    def cleanup_once(self, now: Optional[datetime] = None) -> int:
        from bot.plugins.voice_actor.models import RequestLog, get_session

        cutoff = (now or datetime.utcnow()) - timedelta(days=self.days)
        total = 0
        while True:
            session = get_session()
            try:
                ids = [
                    row[0]
                    for row in (
                        session.query(RequestLog.id)
                        .filter(RequestLog.created_at < cutoff)
                        .order_by(RequestLog.id.asc())
                        .limit(1000)
                        .all()
                    )
                ]
                if not ids:
                    return total
                deleted = (
                    session.query(RequestLog)
                    .filter(RequestLog.id.in_(ids))
                    .delete(synchronize_session=False)
                )
                session.commit()
                total += deleted
                if len(ids) < 1000:
                    return total
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()


_retention = RetentionManager(
    days=settings.observability_retention_days,
    interval_hours=settings.observability_retention_interval_hours,
)


def get_retention_manager() -> RetentionManager:
    return _retention
