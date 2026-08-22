#!/usr/bin/env python
"""
QQ声优机器人 - 管理脚本
用于执行各种管理任务
"""

import sys
import os
from pathlib import Path

# 添加项目路径到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import settings
from bot.plugins.voice_actor.models import VoiceActor, get_session
from bot.plugins.voice_actor.utils import ensure_voice_actor_folders
from loguru import logger


def init_logger():
    """初始化日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )


def reinit_folders():
    """重新创建声优文件夹"""
    print("=" * 60)
    print("重新创建声优文件夹")
    print("=" * 60)

    try:
        session = get_session()
        try:
            voice_actors = session.query(VoiceActor).all()

            if not voice_actors:
                print("❌ 错误：数据库中没有声优数据")
                return False

            print(f"📊 找到 {len(voice_actors)} 位声优")
            for actor in voice_actors:
                print(f"   • {actor.name}")

            print("\n🔄 开始创建文件夹...")
            created_count = ensure_voice_actor_folders(voice_actors)

            print(f"\n✅ 成功创建 {created_count} 个文件夹")
            return True

        finally:
            session.close()

    except Exception as e:
        print(f"❌ 错误: {e}")
        logger.error(f"重新创建文件夹失败: {e}", exc_info=True)
        return False


def list_folders():
    """列出所有声优及其文件夹"""
    print("=" * 60)
    print("声优文件夹状态")
    print("=" * 60)

    try:
        session = get_session()
        try:
            voice_actors = session.query(VoiceActor).all()

            if not voice_actors:
                print("❌ 数据库中没有声优数据")
                return

            images_path = Path("/app/images")

            for actor in voice_actors:
                actor_folder = images_path / actor.name
                exists = "✅" if actor_folder.exists() else "❌"

                file_count = 0
                if actor_folder.exists():
                    file_count = len(list(actor_folder.glob("*")))

                print(f"{exists} {actor.name:<15} ({file_count} 张图片)")

        finally:
            session.close()

    except Exception as e:
        print(f"❌ 错误: {e}")


def show_help():
    """显示帮助信息"""
    print("=" * 60)
    print("QQ声优机器人 - 管理脚本")
    print("=" * 60)
    print()
    print("用法: python manage.py <命令>")
    print()
    print("可用命令:")
    print("  reinit-folders     重新创建所有声优文件夹")
    print("  list-folders       列出所有声优及文件夹状态")
    print("  help               显示此帮助信息")
    print()


def main():
    """主函数"""
    init_logger()

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1]

    if command == "reinit-folders":
        success = reinit_folders()
        sys.exit(0 if success else 1)

    elif command == "list-folders":
        list_folders()

    elif command == "help" or command == "--help" or command == "-h":
        show_help()

    else:
        print(f"❌ 未知命令: {command}")
        print()
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
