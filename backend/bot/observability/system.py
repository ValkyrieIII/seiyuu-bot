"""Cached system metrics and layered dependency readiness checks."""

import asyncio
from pathlib import Path
import platform
import time
from threading import Lock
from typing import Any, Callable, Dict, Optional

from loguru import logger
import psutil
from sqlalchemy import text

from bot.config import settings


class SystemSampler:
    def __init__(self, interval_seconds: float = 5.0) -> None:
        self.interval_seconds = interval_seconds
        self._process = psutil.Process()
        self._started_ns = time.perf_counter_ns()
        self._data: Dict[str, Any] = {}
        self._lock = Lock()
        self._task: Optional[asyncio.Task] = None
        self._process.cpu_percent(interval=None)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        await asyncio.to_thread(self.sample)
        self._task = asyncio.create_task(self._run(), name="system-metrics-sampler")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            try:
                await asyncio.to_thread(self.sample)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.opt(exception=True).warning("系统资源采样失败")

    def sample(self) -> Dict[str, Any]:
        """Sample in a worker thread; CPU sampling is always non-blocking."""
        memory = self._process.memory_info()
        virtual_memory = psutil.virtual_memory()
        disk_target = _existing_path(Path(settings.image_folder))
        disk = psutil.disk_usage(str(disk_target))
        data = {
            "cpu_percent": round(self._process.cpu_percent(interval=None), 1),
            "memory_mb": round(memory.rss / 1024 / 1024, 1),
            "memory_total_mb": round(virtual_memory.total / 1024 / 1024, 1),
            "memory_percent": round(self._process.memory_percent(), 1),
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "disk_percent": round(disk.percent, 1),
            "uptime_seconds": max(
                0, (time.perf_counter_ns() - self._started_ns) // 1_000_000_000
            ),
            "cpu_model": _cpu_model(),
            "sampled_at": time.time(),
        }
        with self._lock:
            self._data = data
        return dict(data)

    def get(self) -> Dict[str, Any]:
        with self._lock:
            data = dict(self._data)
        if data:
            data["uptime_seconds"] = max(
                0, (time.perf_counter_ns() - self._started_ns) // 1_000_000_000
            )
            return data
        return self.sample()


def _existing_path(path: Path) -> Path:
    candidate = path.resolve()
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    return candidate


def _cpu_model() -> str:
    model = platform.processor().strip()
    if model:
        return model
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "Unknown"


def check_database(session_factory: Optional[Callable] = None) -> Dict[str, Any]:
    if session_factory is None:
        from bot.plugins.voice_actor.models import get_session

        session_factory = get_session

    session = None
    try:
        session = session_factory()
        session.execute(text("SELECT 1"))
        return {"ready": True, "error_code": None}
    except Exception:
        logger.opt(exception=True).warning("readiness 数据库检查失败")
        return {"ready": False, "error_code": "DATABASE_UNAVAILABLE"}
    finally:
        if session is not None:
            session.close()


def check_onebot(get_bots: Optional[Callable] = None) -> Dict[str, Any]:
    try:
        if get_bots is None:
            import nonebot

            get_bots = nonebot.get_bots
        bots = get_bots()
        connected_ids = sorted(str(bot_id) for bot_id in bots)
        expected = settings.bot_qq.strip()
        ready = bool(connected_ids) and (not expected or expected in connected_ids)
        return {
            "ready": ready,
            "error_code": None if ready else "ONEBOT_DISCONNECTED",
            "connected_bots": len(connected_ids),
        }
    except Exception:
        logger.opt(exception=True).warning("readiness OneBot 检查失败")
        return {
            "ready": False,
            "error_code": "ONEBOT_CHECK_FAILED",
            "connected_bots": 0,
        }


async def readiness(
    database_check: Callable = check_database,
    onebot_check: Callable = check_onebot,
) -> Dict[str, Any]:
    database = await asyncio.to_thread(database_check)
    onebot = onebot_check()
    return {
        "ready": bool(database["ready"] and onebot["ready"]),
        "database": database,
        "onebot": onebot,
    }


_sampler = SystemSampler(settings.observability_system_sample_seconds)


def get_system_sampler() -> SystemSampler:
    return _sampler
