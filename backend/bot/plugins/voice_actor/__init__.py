"""
QQ声优机器人 - 主插件模块
"""

from .models import init_db
from .utils import scan_image_records
from bot.monitor import start_image_watcher
from loguru import logger

# 初始化数据库
try:
    init_db()
    scan_image_records()
    start_image_watcher()
    logger.info("声优插件已加载")
except Exception as e:
    logger.error(f"声优插件加载失败: {e}")

# 导入处理器以注册事件监听
from . import handlers
