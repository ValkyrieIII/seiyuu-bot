"""
声优插件 - 工具函数
"""

import os
import hashlib
import threading
import uuid
from pathlib import Path
from typing import Optional
from sqlalchemy import text
from loguru import logger
from bot.config import settings


def normalize_text(text: str) -> str:
    """规范化文本（去空格、转小写）"""
    return text.strip().lower()


def calculate_similarity(s1: str, s2: str) -> float:
    """
    计算两个字符串的相似度（使用编辑距离）
    返回值范围：0-1，1表示完全相同
    （未完成）
    """
    s1 = normalize_text(s1)
    s2 = normalize_text(s2)

    if s1 == s2:
        return 1.0

    if len(s1) == 0 or len(s2) == 0:
        return 0.0

    # 使用编辑距离计算
    # 这是一个简化版本，生产环境可使用更高效的算法
    from difflib import SequenceMatcher

    return SequenceMatcher(None, s1, s2).ratio()


def load_image_file(file_path: str) -> Optional[bytes]:
    """加载图片文件"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"图片文件不存在: {file_path}")
            return None

        with open(file_path, "rb") as f:
            data = f.read()

        return data
    except Exception as e:
        logger.error(f"加载图片文件失败 {file_path}: {e}")
        return None


def calculate_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希值"""
    try:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败 {file_path}: {e}")
        return ""


def get_file_size_kb(file_path: str) -> int:
    """获取文件大小（KB）"""
    try:
        size_bytes = os.path.getsize(file_path)
        return max(1, size_bytes // 1024)
    except Exception as e:
        logger.error(f"获取文件大小失败 {file_path}: {e}")
        return 0


def rename_file_with_sequence(actor_name: str, index: int, extension: str) -> str:
    """生成按规律的文件名"""
    # 格式: actor_name_001.jpg
    return f"{actor_name}_{index:06d}{extension}"


def validate_image_file(file_path: str) -> bool:
    """验证图片文件有效性"""
    if not os.path.exists(file_path):
        return False

    # 检查文件扩展名
    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in valid_extensions:
        return False

    # 检查文件大小（最小1KB，最大50MB）
    try:
        size = os.path.getsize(file_path)
        if size < 1024 or size > 50 * 1024 * 1024:
            return False
    except:
        return False


def ensure_voice_actor_folders(
    voice_actors: list, base_path: str = "/app/images"
) -> int:
    """
    根据声优名列表自动创建文件夹结构

    Args:
        voice_actors: VoiceActor 对象列表
        base_path: 基础路径，默认为 /app/images

    Returns:
        创建的文件夹数量
    """
    created_count = 0

    try:
        # 确保基础目录存在
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
            logger.info(f"创建基础目录: {base_path}")

        # 为每个声优创建文件夹
        for actor in voice_actors:
            if not actor or not actor.name:
                continue

            actor_folder = os.path.join(base_path, actor.name)

            if not os.path.exists(actor_folder):
                try:
                    os.makedirs(actor_folder, exist_ok=True)
                    created_count += 1
                    logger.info(f"创建声优文件夹: {actor_folder}")
                except Exception as e:
                    logger.error(f"创建文件夹失败 {actor_folder}: {e}")
            else:
                logger.debug(f"文件夹已存在: {actor_folder}")

        if created_count > 0:
            logger.info(f"成功创建 {created_count} 个声优文件夹")

        return created_count

    except Exception as e:
        logger.error(f"初始化声优文件夹失败: {e}")
        return 0

    return True


def log_error(error: Exception, context: str = ""):
    """记录错误"""
    logger.error(f"错误 [{context}]: {error}", exc_info=True)


VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_SCAN_LOCK = threading.Lock()


def _resolve_base_path(base_path: Optional[str] = None) -> Path:
    return Path(base_path or settings.image_folder)


def _iter_actor_folders(base_path_obj: Path):
    if not base_path_obj.exists():
        return []
    return [
        p
        for p in sorted(base_path_obj.iterdir(), key=lambda x: x.name)
        if p.is_dir() and not p.name.startswith(".")
    ]


def _collect_actor_images(actor_folder: Path):
    files = []
    for file_path in actor_folder.iterdir():
        if file_path.is_file() and not file_path.is_symlink():
            if file_path.suffix.lower() in VALID_IMAGE_EXTENSIONS:
                try:
                    mtime = file_path.stat().st_mtime
                    files.append((mtime, file_path))
                except Exception as e:
                    logger.error(f"读取文件信息失败 {file_path}: {e}")
    files.sort(key=lambda x: (x[0], x[1].name))
    return [item[1] for item in files]


def _rename_actor_images(actor_name: str, actor_folder: Path):
    source_files = _collect_actor_images(actor_folder)
    if not source_files:
        return 0, 0

    renamed_count = 0
    failed_count = 0

    rename_plan = []
    for index, file_path in enumerate(source_files, start=1):
        target_name = f"{actor_name}_{index:03d}{file_path.suffix.lower()}"
        target_path = actor_folder / target_name
        if file_path != target_path:
            rename_plan.append((file_path, target_path))

    staged_plan = []
    for src, target in rename_plan:
        try:
            temp_path = actor_folder / f".__tmp_{uuid.uuid4().hex}{src.suffix.lower()}"
            src.rename(temp_path)
            staged_plan.append((temp_path, target))
        except Exception as e:
            failed_count += 1
            logger.error(f"临时重命名失败 {src} -> {target}: {e}")

    for src, target in staged_plan:
        try:
            if target.exists() and target != src:
                raise FileExistsError(f"目标文件已存在: {target}")
            src.rename(target)
            renamed_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"最终重命名失败 {src} -> {target}: {e}")

    return renamed_count, failed_count


def _build_actor_file_index(actor_folder: Path):
    files = _collect_actor_images(actor_folder)
    index = {}
    for file_path in files:
        file_hash = calculate_file_hash(str(file_path))
        try:
            size_kb = max(1, file_path.stat().st_size // 1024)
        except Exception:
            size_kb = 0
        index[file_path.name] = {
            "filename": file_path.name,
            "file_path": str(file_path),
            "file_hash": file_hash,
            "size_kb": size_kb,
        }
    return index


def initialize_image_records(base_path: Optional[str] = None):
    """
    初始化图片记录：
    1. 扫描 images 目录下全部声优文件夹
    2. 将每个声优目录下图片重命名为 声优名_001 起始序号
    3. 清空 voice_actors 和 images 表
    4. 按扫描结果重建两表记录

    Returns:
        (新增声优数, 新增图片数, 重命名成功数, 重命名失败数)
    """
    from .models import VoiceActor, Image, get_session

    with _SCAN_LOCK:
        base_path_obj = _resolve_base_path(base_path)
        if not base_path_obj.exists():
            logger.error(f"基础路径不存在: {base_path_obj}")
            return 0, 0, 0, 0

        actor_folders = _iter_actor_folders(base_path_obj)

        renamed_total = 0
        rename_failed_total = 0
        actor_images = {}

        for actor_folder in actor_folders:
            actor_name = actor_folder.name
            renamed_count, failed_count = _rename_actor_images(actor_name, actor_folder)
            renamed_total += renamed_count
            rename_failed_total += failed_count
            actor_images[actor_name] = _build_actor_file_index(actor_folder)

        session = get_session()
        try:
            session.query(Image).delete(synchronize_session=False)
            session.query(VoiceActor).delete(synchronize_session=False)

            # 重置自增序列，确保重新初始化后 ID 从 1 开始。
            # 当前部署使用 MySQL；若非 MySQL 则忽略并继续插入。
            try:
                if session.bind and session.bind.dialect.name == "mysql":
                    session.execute(text("ALTER TABLE images AUTO_INCREMENT = 1"))
                    session.execute(text("ALTER TABLE voice_actors AUTO_INCREMENT = 1"))
            except Exception as e:
                logger.warning(f"重置自增序列失败，继续执行初始化: {e}")

            session.flush()

            added_actors = 0
            added_images = 0

            for actor_name in sorted(actor_images.keys()):
                images = actor_images[actor_name]
                actor = VoiceActor(
                    name=actor_name,
                    description="自动扫描同步",
                    image_count=len(images),
                    is_active=True,
                )
                session.add(actor)
                session.flush()
                added_actors += 1

                for image_info in images.values():
                    session.add(
                        Image(
                            voice_actor_id=actor.id,
                            filename=image_info["filename"],
                            file_path=image_info["file_path"],
                            size_kb=image_info["size_kb"],
                            file_hash=image_info["file_hash"],
                            is_active=True,
                        )
                    )
                    added_images += 1

            session.commit()
            logger.info(
                f"初始化完成: 声优 {added_actors}, 图片 {added_images}, 重命名成功 {renamed_total}, 重命名失败 {rename_failed_total}"
            )
            return added_actors, added_images, renamed_total, rename_failed_total
        except Exception as e:
            session.rollback()
            logger.error(f"初始化图片记录失败: {e}", exc_info=True)
            return 0, 0, renamed_total, rename_failed_total
        finally:
            session.close()


def scan_image_records(base_path: Optional[str] = None):
    """
    扫描 images 目录（扫描前会自动按规则重命名图片）并将增删改同步到数据库（删除采用软删除）。

    Returns:
        (新增声优数, 软删除声优数, 新增图片数, 更新图片数, 软删除图片数)
    """
    from .models import VoiceActor, Image, get_session

    with _SCAN_LOCK:
        base_path_obj = _resolve_base_path(base_path)
        if not base_path_obj.exists():
            logger.error(f"基础路径不存在: {base_path_obj}")
            return 0, 0, 0, 0, 0

        actor_folders = _iter_actor_folders(base_path_obj)

        renamed_total = 0
        rename_failed_total = 0
        for actor_folder in actor_folders:
            actor_name = actor_folder.name
            renamed_count, failed_count = _rename_actor_images(actor_name, actor_folder)
            renamed_total += renamed_count
            rename_failed_total += failed_count

        fs_actor_map = {}
        for actor_folder in actor_folders:
            fs_actor_map[actor_folder.name] = _build_actor_file_index(actor_folder)

        added_actors = 0
        disabled_actors = 0
        added_images = 0
        updated_images = 0
        disabled_images = 0

        session = get_session()
        try:
            db_actors = session.query(VoiceActor).all()
            db_actor_map = {actor.name: actor for actor in db_actors}

            # 新增或更新现有声优
            for actor_name, fs_images in fs_actor_map.items():
                actor = db_actor_map.get(actor_name)
                if not actor:
                    actor = VoiceActor(
                        name=actor_name,
                        description="自动扫描同步",
                        image_count=len(fs_images),
                        is_active=True,
                    )
                    session.add(actor)
                    session.flush()
                    db_actor_map[actor_name] = actor
                    added_actors += 1
                else:
                    changed = False
                    # if not actor.is_active:
                    #     actor.is_active = True
                    #     changed = True
                    if actor.image_count != len(fs_images):
                        actor.image_count = len(fs_images)
                        changed = True
                    if changed:
                        updated_images += 1

                db_images = (
                    session.query(Image)
                    .filter(Image.voice_actor_id == actor.id)
                    .all()
                )
                db_image_map = {image.filename: image for image in db_images}

                for filename, fs_image in fs_images.items():
                    db_image = db_image_map.get(filename)
                    if not db_image:
                        session.add(
                            Image(
                                voice_actor_id=actor.id,
                                filename=filename,
                                file_path=fs_image["file_path"],
                                size_kb=fs_image["size_kb"],
                                file_hash=fs_image["file_hash"],
                                is_active=True,
                            )
                        )
                        added_images += 1
                    else:
                        changed = False
                        if db_image.file_path != fs_image["file_path"]:
                            db_image.file_path = fs_image["file_path"]
                            changed = True
                        if db_image.size_kb != fs_image["size_kb"]:
                            db_image.size_kb = fs_image["size_kb"]
                            changed = True
                        if fs_image["file_hash"] and db_image.file_hash != fs_image["file_hash"]:
                            db_image.file_hash = fs_image["file_hash"]
                            changed = True
                        if not db_image.is_active:
                            db_image.is_active = True
                            changed = True
                        if changed:
                            updated_images += 1

                fs_filenames = set(fs_images.keys())
                for db_image in db_images:
                    if db_image.filename not in fs_filenames and db_image.is_active:
                        db_image.is_active = False
                        disabled_images += 1

            # 软删除已不存在的声优目录
            fs_actor_names = set(fs_actor_map.keys())
            for actor in db_actors:
                if actor.name not in fs_actor_names:
                    if actor.is_active:
                        actor.is_active = False
                        actor.image_count = 0
                        disabled_actors += 1

                    actor_images = (
                        session.query(Image)
                        .filter(Image.voice_actor_id == actor.id, Image.is_active == True)
                        .all()
                    )
                    for image in actor_images:
                        image.is_active = False
                        disabled_images += 1

            session.commit()
            logger.info(
                f"扫描完成: 新增声优 {added_actors}, 软删除声优 {disabled_actors}, 新增图片 {added_images}, 更新图片 {updated_images}, 软删除图片 {disabled_images}, 重命名成功 {renamed_total}, 重命名失败 {rename_failed_total}"
            )
            return added_actors, disabled_actors, added_images, updated_images, disabled_images
        except Exception as e:
            session.rollback()
            logger.error(f"扫描图片记录失败: {e}", exc_info=True)
            return 0, 0, 0, 0, 0
        finally:
            session.close()
