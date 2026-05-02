"""
@Bot 命令插件
"""

from loguru import logger

from .models import init_db

init_db()

logger.info("@Bot 命令插件已加载")

# 导入处理器以注册事件监听
from . import handlers
