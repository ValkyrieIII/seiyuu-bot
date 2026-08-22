"""Application liveness endpoint registration."""

from loguru import logger


async def health() -> dict[str, str]:
    """Return a lightweight liveness response without touching external services."""
    return {"status": "ok"}


def register_health_route(driver) -> bool:
    """Register the liveness endpoint on the NoneBot FastAPI application."""
    app = getattr(driver, "server_app", None)
    if app is None:
        logger.warning("未找到 FastAPI server_app，健康检查路由未挂载")
        return False

    if getattr(app.state, "health_route_registered", False):
        return True

    app.add_api_route("/health", health, methods=["GET"], tags=["health"])
    app.state.health_route_registered = True
    logger.info("健康检查路由挂载完成: /health")
    return True
