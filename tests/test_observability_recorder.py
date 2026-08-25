import asyncio
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from bot.observability.events import ObservabilityEvent
from bot.observability.recorder import EventRecorder, record_event


def event(user_id: int) -> ObservabilityEvent:
    return ObservabilityEvent(command="voice_actor", status="success", user_id=user_id)


def test_full_queue_drops_without_waiting():
    recorder = EventRecorder(capacity=1, batch_size=1, flush_interval=0.5, writer=lambda _: None)
    recorder._queue = asyncio.Queue(maxsize=1)
    recorder._accepting = True

    assert recorder.try_record(event(1)) is True
    assert recorder.try_record(event(2)) is False
    assert recorder.stats()["dropped"] == 1


def test_batch_flush_and_shutdown_drain():
    batches = []

    async def scenario():
        recorder = EventRecorder(
            capacity=8,
            batch_size=2,
            flush_interval=0.01,
            writer=lambda batch: batches.append([item.user_id for item in batch]),
        )
        await recorder.start()
        for user_id in (1, 2, 3):
            assert recorder.try_record(event(user_id))
        await recorder.stop(timeout=1)
        return recorder.stats()

    stats = asyncio.run(scenario())
    assert [item for batch in batches for item in batch] == [1, 2, 3]
    assert any(len(batch) == 2 for batch in batches)
    assert stats["written"] == 3
    assert stats["backlog"] == 0


def test_database_writer_failure_is_contained():
    def fail(_batch):
        raise RuntimeError("database unavailable")

    async def scenario():
        recorder = EventRecorder(
            capacity=4, batch_size=4, flush_interval=0.01, writer=fail
        )
        await recorder.start()
        assert recorder.try_record(event(1)) is True
        await recorder.stop(timeout=1)
        return recorder.stats()

    stats = asyncio.run(scenario())
    assert stats["write_failures"] == 1
    assert stats["failed_events"] == 1
    assert stats["written"] == 0


def test_invalid_statistics_event_never_escapes_to_caller():
    assert record_event(command="bad command", status="error", user_id=1) is False
