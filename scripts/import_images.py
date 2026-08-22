#!/usr/bin/env python3
"""
图片批量导入脚本
用法: python import_images.py <source_folder>
例如: python import_images.py /app/images
"""
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "import_images.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="100 MB",
    level="DEBUG",
)

# 导入数据库模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "bot"))
from plugins.voice_actor.models import get_session, VoiceActor, Image
from plugins.voice_actor.utils import (
    calculate_file_hash,
    get_file_size_kb,
    validate_image_file,
)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
TARGET_IMAGE_FOLDER = "/app/images"


def get_supported_files(source_folder: str) -> dict:
    """
    扫描源文件夹，按声优分类
    返回: {voice_actor_name: [file_paths]}
    """
    actors = {}

    if not os.path.isdir(source_folder):
        logger.error(f"源文件夹不存在: {source_folder}")
        return actors

    # 扫描第一级子文件夹（声优名称）
    for actor_name in os.listdir(source_folder):
        actor_path = os.path.join(source_folder, actor_name)

        if not os.path.isdir(actor_path):
            continue

        files = []
        # 扫描该声优文件夹中的所有图片
        for filename in os.listdir(actor_path):
            file_path = os.path.join(actor_path, filename)

            if not os.path.isfile(file_path):
                continue

            # 检查文件扩展名
            _, ext = os.path.splitext(filename)
            if ext.lower() not in VALID_EXTENSIONS:
                continue

            # 验证图片文件
            if not validate_image_file(file_path):
                logger.warning(f"跳过无效图片文件: {file_path}")
                continue

            files.append(file_path)

        if files:
            actors[actor_name] = files
            logger.info(f"找到声优 [{actor_name}]: {len(files)} 张图片")

    return actors


def ensure_actor_folder(actor_name: str) -> str:
    """确保声优文件夹存在"""
    actor_folder = os.path.join(TARGET_IMAGE_FOLDER, actor_name)
    os.makedirs(actor_folder, exist_ok=True)
    return actor_folder


def copy_and_rename_image(src_path: str, actor_name: str, index: int) -> tuple:
    """
    复制图片到目标文件夹并重命名
    返回: (新文件名, 新文件路径, 文件哈希, 文件大小KB)
    """
    try:
        # 生成新文件名
        _, ext = os.path.splitext(src_path)
        new_filename = f"{actor_name}_{index:06d}{ext}"

        actor_folder = ensure_actor_folder(actor_name)
        dst_path = os.path.join(actor_folder, new_filename)

        # 复制文件
        import shutil

        shutil.copy2(src_path, dst_path)

        # 计算哈希和大小
        file_hash = calculate_file_hash(dst_path)
        file_size_kb = get_file_size_kb(dst_path)

        return new_filename, dst_path, file_hash, file_size_kb
    except Exception as e:
        logger.error(f"复制文件失败 {src_path}: {e}")
        raise


def import_images(source_folder: str) -> dict:
    """
    导入图片
    返回: {actor_name: {success: int, skipped: int, failed: int}}
    """
    session = get_session()
    stats = {}

    try:
        # 扫描源文件夹
        actors_files = get_supported_files(source_folder)

        if not actors_files:
            logger.warning("未找到任何有效的图片文件")
            return stats

        for actor_name, files in actors_files.items():
            stats[actor_name] = {"success": 0, "skipped": 0, "failed": 0}

            # 获取或创建声优
            voice_actor = (
                session.query(VoiceActor).filter(VoiceActor.name == actor_name).first()
            )

            if not voice_actor:
                voice_actor = VoiceActor(
                    name=actor_name,
                    description=f"自动导入的声优 - {actor_name}",
                    image_count=0,
                    is_active=True,
                )
                session.add(voice_actor)
                session.commit()
                logger.info(f"创建新声优: {actor_name}")

            # 导入该声优的所有图片
            for idx, src_path in enumerate(files, 1):
                try:
                    # 检查是否已存在（根据哈希值）
                    src_hash = calculate_file_hash(src_path)
                    existing = (
                        session.query(Image).filter(Image.file_hash == src_hash).first()
                    )

                    if existing:
                        logger.debug(
                            f"图片已存在（哈希重复）: {os.path.basename(src_path)}"
                        )
                        stats[actor_name]["skipped"] += 1
                        continue

                    # 复制并重命名图片
                    new_filename, dst_path, file_hash, file_size_kb = (
                        copy_and_rename_image(src_path, actor_name, idx)
                    )

                    # 创建数据库记录
                    image = Image(
                        voice_actor_id=voice_actor.id,
                        filename=new_filename,
                        file_path=dst_path,
                        size_kb=file_size_kb,
                        file_hash=file_hash,
                        is_active=True,
                    )
                    session.add(image)
                    session.commit()

                    stats[actor_name]["success"] += 1
                    logger.debug(f"导入图片: {new_filename} ({file_size_kb}KB)")

                except Exception as e:
                    logger.error(f"导入图片失败 {os.path.basename(src_path)}: {e}")
                    stats[actor_name]["failed"] += 1
                    session.rollback()

            # 更新声优的图片计数
            image_count = (
                session.query(Image)
                .filter(Image.voice_actor_id == voice_actor.id)
                .count()
            )
            voice_actor.image_count = image_count
            session.commit()

            total = (
                stats[actor_name]["success"]
                + stats[actor_name]["skipped"]
                + stats[actor_name]["failed"]
            )
            logger.info(
                f"声优 [{actor_name}] 导入完成: 成功 {stats[actor_name]['success']}, 跳过 {stats[actor_name]['skipped']}, 失败 {stats[actor_name]['failed']} (总计 {total})"
            )

    except Exception as e:
        logger.error(f"导入过程发生错误: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()

    return stats


def print_summary(stats: dict):
    """打印导入总结"""
    total_success = sum(s["success"] for s in stats.values())
    total_skipped = sum(s["skipped"] for s in stats.values())
    total_failed = sum(s["failed"] for s in stats.values())

    logger.info("=" * 60)
    logger.info("导入总结")
    logger.info("=" * 60)
    for actor_name, s in stats.items():
        logger.info(f"  {actor_name}: ✓{s['success']} ⊘{s['skipped']} ✗{s['failed']}")
    logger.info(f"总计: ✓{total_success} ⊘{total_skipped} ✗{total_failed}")
    logger.info("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python import_images.py <source_folder>")
        print("例如: python import_images.py /app/images")
        sys.exit(1)

    source_folder = sys.argv[1]
    logger.info(f"开始导入图片...")
    logger.info(f"源文件夹: {source_folder}")
    logger.info(f"目标文件夹: {TARGET_IMAGE_FOLDER}")

    stats = import_images(source_folder)
    print_summary(stats)

    if sum(s["failed"] for s in stats.values()) == 0:
        logger.info("导入完成！")
        sys.exit(0)
    else:
        logger.error("导入过程中出现错误")
        sys.exit(1)
