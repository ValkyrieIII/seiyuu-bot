#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QQ声优机器人 - 管理脚本
用于执行各种管理任务
"""

import sys
import os
import io

# 在极早的阶段强制stdout使用UTF-8编码
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="surrogateescape"
    )
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="surrogateescape"
    )

from pathlib import Path

# 添加项目路径到 Python 路径
sys.path.insert(0, "/app")

from bot.config import settings
from bot.plugins.voice_actor.models import VoiceActor, get_session
from bot.plugins.voice_actor.utils import (
    ensure_voice_actor_folders,
    initialize_image_records,
    scan_image_records,
)
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
    print("用法: python /app/manage.py <命令>")
    print()
    print("可用命令:")
    print("  reinit-folders              重新创建所有声优文件夹")
    print("  list-folders                列出所有声优及文件夹状态")
    print("  init-images-db              初始化图片命名并重建数据库记录")
    print("  scan-images-db              扫描文件系统并自动重命名后同步数据库（软删除）")
    print("  sync-database               等同 scan-images-db（兼容旧命令）")
    print("  help                        显示此帮助信息")
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

    elif command == "init-images-db":
        print("=" * 60)
        print("初始化图片命名并重建数据库记录")
        print("=" * 60)
        added_actors, added_images, renamed_total, rename_failed_total = (
            initialize_image_records(settings.image_folder)
        )
        print("\n" + "=" * 60)
        print("📊 初始化完成")
        print(f"+ 新增声优: {added_actors}")
        print(f"+ 新增图片: {added_images}")
        print(f"~ 重命名成功: {renamed_total}")
        if rename_failed_total > 0:
            print(f"❌ 重命名失败: {rename_failed_total}")
        print("=" * 60)
        sys.exit(0)

    elif command == "scan-images-db" or command == "sync-database":
        print("=" * 60)
        print("扫描文件系统（含自动重命名）并同步数据库")
        print("=" * 60)
        (
            added_actors,
            disabled_actors,
            added_images,
            updated_images,
            disabled_images,
        ) = scan_image_records(settings.image_folder)
        print("\n" + "=" * 60)
        print(f"📊 同步完成统计")
        if added_actors > 0:
            print(f"+ 新增声优: {added_actors}")
        if disabled_actors > 0:
            print(f"✗ 禁用声优: {disabled_actors}")
        if added_images > 0:
            print(f"+ 新增图片: {added_images}")
        if updated_images > 0:
            print(f"~ 更新图片: {updated_images}")
        if disabled_images > 0:
            print(f"✗ 禁用图片: {disabled_images}")
        print("=" * 60)
        sys.exit(0)

    elif command == "rename-images-all":
        print("⚠️ rename-images-all 已废弃，请使用 init-images-db")
        sys.exit(1)

    elif command == "rename-images":
        print("⚠️ rename-images 已废弃，请使用 init-images-db")
        sys.exit(1)

    else:
        print(f"❌ 未知命令: {command}")
        print()
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
