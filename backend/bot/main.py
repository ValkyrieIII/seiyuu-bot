"""NoneBot application entry point."""

import io
import json
import os
from pathlib import Path
import sys


if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="surrogateescape",
    )
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding="utf-8",
        errors="surrogateescape",
    )

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from bot.config import settings
from loguru import logger


log_folder = Path(settings.log_folder)
log_folder.mkdir(exist_ok=True, parents=True)

logger.remove()
logger.add(
    sys.stdout,
    format=(
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level=settings.log_level,
)
logger.add(
    log_folder / "bot.log",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
    rotation="500 MB",
    retention="7 days",
    level=settings.log_level,
)

os.environ.setdefault("DRIVER", "~fastapi")
os.environ.setdefault("HOST", "0.0.0.0")
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("NONEBOT_LOG_LEVEL", settings.log_level)

listen_port = os.environ["PORT"]
os.environ.setdefault(
    "NONEBOT_ADAPTER_ONEBOT_WS_REVERSE_SERVERS",
    json.dumps([f"0.0.0.0:{listen_port}"]),
)
os.environ.setdefault(
    "NONEBOT_ADAPTER_ONEBOT_ACCESS_TOKEN",
    settings.onebot_access_token,
)

logger.info(f"运行环境: {settings.app_env}")
logger.info(f"OneBot 反向 WebSocket: 0.0.0.0:{listen_port}")
logger.info(
    "OneBot Access Token: {}",
    "已配置" if settings.onebot_access_token else "未配置",
)

import nonebot
from nonebot.adapters.onebot.v11 import Adapter

from bot.admin import register_admin_routes
from bot.health import register_health_route


def main():
    """Initialize adapters, plugins, HTTP routes, and start NoneBot."""
    logger.info("QQ声优机器人启动中...")
    logger.info(f"数据库: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    try:
        nonebot.init()
        driver = nonebot.get_driver()

        register_health_route(driver)
        driver.register_adapter(Adapter)

        nonebot.load_plugins("bot/plugins")
        register_admin_routes(driver)

        logger.info("所有插件加载完成")
        nonebot.run()
    except Exception as exc:
        logger.error(f"应用启动失败: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
