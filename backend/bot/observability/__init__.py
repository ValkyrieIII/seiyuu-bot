"""Low-overhead, best-effort observability for the bot process."""

from .events import EventStatus, ObservabilityEvent, elapsed_ms
from .recorder import get_recorder, record_event


def register_observability_hooks(driver) -> None:
    """Attach lifecycle-managed background tasks to the NoneBot driver."""
    if getattr(driver, "_observability_hooks_registered", False):
        return

    async def startup() -> None:
        from .retention import get_retention_manager
        from .system import get_system_sampler

        await get_recorder().start()
        await get_system_sampler().start()
        await get_retention_manager().start()

    async def shutdown() -> None:
        from bot.config import settings
        from .retention import get_retention_manager
        from .system import get_system_sampler

        await get_retention_manager().stop()
        await get_system_sampler().stop()
        await get_recorder().stop(settings.observability_shutdown_timeout_seconds)

    driver.on_startup(startup)
    driver.on_shutdown(shutdown)
    setattr(driver, "_observability_hooks_registered", True)

__all__ = [
    "EventStatus",
    "ObservabilityEvent",
    "elapsed_ms",
    "get_recorder",
    "record_event",
    "register_observability_hooks",
]
