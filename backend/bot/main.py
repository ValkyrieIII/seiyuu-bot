"""
NoneBot 应用启动入口
"""

import os
import sys
import io
import logging
from pathlib import Path

# 在极早的阶段强制stdout使用UTF-8编码
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="surrogateescape"
    )
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="surrogateescape"
    )

# 添加 /app 到 Python 路径以便导入 bot 包
sys.path.insert(0, "/app")

from loguru import logger

# 配置日志
logger.remove()  # 移除默认处理器
logger.add(
    sys.stdout,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
)
logger.add(
    "/app/logs/bot.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="500 MB",
    retention="7 days",
    level="INFO",
)

# 确保日志目录存在
Path("/app/logs").mkdir(exist_ok=True, parents=True)

# 必须在导入 nonebot 之前设置环境变量！
from bot.config import settings

# 设置环境变量 - 必须在导入 nonebot 和适配器之前
os.environ.setdefault(
    "DRIVER", "~fastapi"
)  # 使用 fastapi 驱动以支持反向 WebSocket 服务端
os.environ.setdefault("HOST", "0.0.0.0")  # 监听所有网络接口
os.environ.setdefault("PORT", "8080")  # WebSocket 服务端口
os.environ.setdefault("NONEBOT_LOG_LEVEL", settings.log_level)

# 配置 OneBot 反向 WebSocket（NapCat 主动连接到 NoneBot）
# 反向模式：NapCat 作为客户端推送消息到 NoneBot 的 WebSocket 服务器
# NapCat 会连接到 ws://nonebot:8080/onebot/v11/ws 推送消息
os.environ.setdefault("NONEBOT_ADAPTER_ONEBOT_WS_REVERSE_SERVERS", '["0.0.0.0:8080"]')
# 配置 OneBot 访问令牌（反向 WebSocket 连接时 NapCat 需要提供此令牌进行验证）
os.environ.setdefault(
    "NONEBOT_ADAPTER_ONEBOT_ACCESS_TOKEN", settings.onebot_access_token
)
logger.info("OneBot 反向 WebSocket 配置: 监听 0.0.0.0:8080")
logger.info(
    f"OneBot Access Token 已配置（长度: {len(settings.onebot_access_token)} 字符）"
)
logger.info(
    "NapCat 应连接到 ws://nonebot:8080/onebot/v11/ws 并提供相同的 Token 以完成连接"
)

import nonebot
from nonebot.adapters.onebot.v11 import Adapter
from bot.admin import register_admin_routes


def main():
    """应用主入口"""
    logger.info("=" * 50)
    logger.info("QQ声优机器人启动中...")
    logger.info(f"数据库: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    logger.info(f"NapCat WebSocket: {settings.napcat_ws_url}")
    logger.info("=" * 50)

    try:
        # 初始化 NoneBot
        nonebot.init()

        # 获取驱动
        driver = nonebot.get_driver()

        # 注册 OneBot v11 适配器
        driver.register_adapter(Adapter)

        # 挂载管理后台路由
        register_admin_routes(driver)

        # 加载插件
        nonebot.load_plugins("bot/plugins")

        logger.info("所有插件加载完成")

        # 启动应用
        nonebot.run()

    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
