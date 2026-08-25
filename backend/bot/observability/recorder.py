"""Non-blocking queue and background batch writer for request events."""

import asyncio
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Callable, Dict, Optional, Sequence

from loguru import logger

from bot.config import settings
from .events import ObservabilityEvent


BatchWriter = Callable[[Sequence[ObservabilityEvent]], None]


@dataclass
class RecorderCounters:
    accepted: int = 0
    dropped: int = 0
    written: int = 0
    write_failures: int = 0
    failed_events: int = 0


class EventRecorder:
    """Best-effort recorder whose public write path never blocks or raises."""

    def __init__(
        self,
        capacity: int = 2048,
        batch_size: int = 50,
        flush_interval: float = 0.5,
        writer: Optional[BatchWriter] = None,
    ) -> None:
        if capacity <= 0 or batch_size <= 0 or flush_interval <= 0:
            raise ValueError("recorder limits must be positive")
        self.capacity = capacity
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._writer = writer or self._write_batch
        self._queue: Optional[asyncio.Queue[ObservabilityEvent]] = None
        self._worker: Optional[asyncio.Task] = None
        self._accepting = False
        self._counters = RecorderCounters()
        self._counter_lock = Lock()

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._queue = asyncio.Queue(maxsize=self.capacity)
        self._accepting = True
        self._worker = asyncio.create_task(
            self._run(), name="observability-event-writer"
        )
        logger.info(
            "统计事件记录器已启动 capacity={} batch_size={} flush_interval={}s",
            self.capacity,
            self.batch_size,
            self.flush_interval,
        )

    def try_record(self, event: ObservabilityEvent) -> bool:
        """Enqueue immediately; drop on overload or lifecycle races."""
        queue = self._queue
        if not self._accepting or queue is None:
            self._increment("dropped")
            return False
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            self._increment("dropped")
            return False
        except Exception:
            self._increment("dropped")
            logger.opt(exception=True).warning("统计事件入队失败")
            return False
        self._increment("accepted")
        return True

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop accepting and make a bounded attempt to drain queued events."""
        self._accepting = False
        worker = self._worker
        if worker is None:
            return
        try:
            await asyncio.wait_for(worker, timeout=timeout)
        except asyncio.TimeoutError:
            backlog = self.backlog
            self._increment("dropped", backlog)
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
            logger.warning("统计队列停机排空超时，丢弃 {} 条事件", backlog)
        finally:
            self._worker = None

    @property
    def backlog(self) -> int:
        return self._queue.qsize() if self._queue is not None else 0

    def stats(self) -> Dict[str, int]:
        with self._counter_lock:
            result = asdict(self._counters)
        result.update({"backlog": self.backlog, "capacity": self.capacity})
        return result

    def _increment(self, field_name: str, amount: int = 1) -> None:
        with self._counter_lock:
            setattr(
                self._counters,
                field_name,
                getattr(self._counters, field_name) + amount,
            )

    async def _run(self) -> None:
        queue = self._queue
        assert queue is not None
        try:
            while self._accepting or not queue.empty():
                try:
                    first = await asyncio.wait_for(
                        queue.get(), timeout=self.flush_interval
                    )
                except asyncio.TimeoutError:
                    continue

                batch = [first]
                deadline = asyncio.get_running_loop().time() + self.flush_interval
                while len(batch) < self.batch_size:
                    try:
                        batch.append(queue.get_nowait())
                        continue
                    except asyncio.QueueEmpty:
                        pass

                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0 or (not self._accepting and queue.empty()):
                        break
                    try:
                        batch.append(await asyncio.wait_for(queue.get(), timeout=remaining))
                    except asyncio.TimeoutError:
                        break

                await self._flush(batch)
                for _ in batch:
                    queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.opt(exception=True).error("统计事件后台任务异常退出")

    async def _flush(self, batch: Sequence[ObservabilityEvent]) -> None:
        try:
            await asyncio.to_thread(self._writer, batch)
        except Exception:
            self._increment("write_failures")
            self._increment("failed_events", len(batch))
            logger.opt(exception=True).error("统计事件批量写入失败 count={}", len(batch))
        else:
            self._increment("written", len(batch))

    @staticmethod
    def _write_batch(batch: Sequence[ObservabilityEvent]) -> None:
        from bot.plugins.voice_actor.models import RequestLog, get_session

        session = get_session()
        try:
            session.bulk_insert_mappings(
                RequestLog, [event.to_record() for event in batch]
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_recorder = EventRecorder(
    capacity=settings.observability_queue_capacity,
    batch_size=settings.observability_batch_size,
    flush_interval=settings.observability_flush_interval_seconds,
)


def get_recorder() -> EventRecorder:
    return _recorder


def record_event(
    event: Optional[ObservabilityEvent] = None, **event_fields: Any
) -> bool:
    """Failure boundary used by handlers: validation and queue errors never escape."""
    try:
        if event is None:
            event = ObservabilityEvent(**event_fields)
        return _recorder.try_record(event)
    except Exception:
        logger.opt(exception=True).warning("统计事件记录失败")
        return False
