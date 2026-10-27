"""
QQ声优机器人 - 主插件模块
"""

import threading

from loguru import logger

from .models import init_db
from .utils import scan_image_records
from bot.monitor import start_image_watcher

# 建表很快，保持同步，避免后续插件在表不存在时启动。
try:
    init_db()
    _db_ready = True
except Exception as e:
    _db_ready = False
    logger.error(f"声优插件数据库初始化失败: {e}")


def _initial_scan_and_watch() -> None:
    """全量图片扫描要哈希整个目录（生产上可达数分钟），放到后台执行。"""
    try:
        scan_image_records()
        # 扫描结束后再挂监听，避免扫描期间的文件事件触发并发扫描。
        start_image_watcher()
        logger.info("声优插件已加载（图片扫描完成）")
    except Exception as e:
        logger.error(f"声优插件后台扫描失败: {e}")


if _db_ready:
    threading.Thread(
        target=_initial_scan_and_watch,
        name="voice-actor-initial-scan",
        daemon=True,
    ).start()
    logger.info("声优插件已加载（图片扫描转入后台）")

# 导入处理器以注册事件监听
from . import handlers
