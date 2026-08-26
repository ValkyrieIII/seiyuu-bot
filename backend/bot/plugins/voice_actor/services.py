"""
声优插件 - 业务逻辑层
"""

import random
import time
from typing import Optional, List, Tuple
from loguru import logger
from sqlalchemy import and_, or_, func
from .models import VoiceActor, Image, Alias, UserCooldown, RequestLog, get_session
from bot.config import settings

# ---------------------------------------------------------------------------
# 别名词表缓存：拦截层用，避免每条群闲聊消息都打满 3 次 SQL
#
# 内容 = aliases.alias_name(活跃) ∪ voice_actors.name(活跃)，只回答"能否命中"，
# 不参与解析语义；写操作后整表重建（全量才几毫秒，不值得做增量维护）。
# 仅适用于单进程内有效；若用离线脚本改库（scripts/manage_aliases.py），
# 需重启机器人进程或调用 invalidate_known_names() 所在进程。
# ---------------------------------------------------------------------------
_known_names_cache: Optional[frozenset] = None


def get_known_names() -> frozenset:
    """获取可命中的别名词表（首次调用时全量加载，此后常驻内存）"""
    global _known_names_cache
    if _known_names_cache is None:
        session = get_session()
        try:
            names = {
                row[0]
                for row in session.query(Alias.alias_name).filter(
                    Alias.is_active == True
                )
            }
            names.update(
                row[0]
                for row in session.query(VoiceActor.name).filter(
                    VoiceActor.is_active == True
                )
            )
        finally:
            session.close()
        logger.info(f"已加载别名词表缓存，共 {len(names)} 条")
        _known_names_cache = frozenset(names)
    return _known_names_cache


def invalidate_known_names() -> None:
    """置空词表缓存，下一条消息触发时自动全量重建"""
    global _known_names_cache
    _known_names_cache = None


class VoiceActorService:
    """声优业务服务"""

    @staticmethod
    def get_voice_actor_by_name(name: str) -> Optional[VoiceActor]:
        """根据名称获取声优"""
        session = get_session()
        try:
            actor = (
                session.query(VoiceActor)
                .filter(and_(VoiceActor.name == name, VoiceActor.is_active == True))
                .first()
            )
            return actor
        finally:
            session.close()

    @staticmethod
    def get_voice_actor_by_id(actor_id: int) -> Optional[VoiceActor]:
        """根据ID获取声优"""
        session = get_session()
        try:
            actor = (
                session.query(VoiceActor)
                .filter(and_(VoiceActor.id == actor_id, VoiceActor.is_active == True))
                .first()
            )
            return actor
        finally:
            session.close()

    @staticmethod
    def get_all_voice_actors() -> List[VoiceActor]:
        """获取所有激活的声优"""
        session = get_session()
        try:
            actors = (
                session.query(VoiceActor).filter(VoiceActor.is_active == True).all()
            )
            return actors
        finally:
            session.close()


class ImageService:
    """图片业务服务"""

    @staticmethod
    def get_random_image(voice_actor_id: int) -> Optional[Image]:
        """获取声优的随机图片"""
        session = get_session()
        try:
            # 统计该声优有多少张激活图片
            count = (
                session.query(func.count(Image.id))
                .filter(
                    and_(
                        Image.voice_actor_id == voice_actor_id, Image.is_active == True
                    )
                )
                .scalar()
            )

            if count == 0:
                return None

            # 随机偏移
            offset = random.randint(0, count - 1)

            # 获取随机图片
            image = (
                session.query(Image)
                .filter(
                    and_(
                        Image.voice_actor_id == voice_actor_id, Image.is_active == True
                    )
                )
                .offset(offset)
                .first()
            )

            return image
        finally:
            session.close()

    @staticmethod
    def get_image_by_id(image_id: int) -> Optional[Image]:
        """根据ID获取图片"""
        session = get_session()
        try:
            return session.query(Image).filter(Image.id == image_id).first()
        finally:
            session.close()

    @staticmethod
    def get_images_by_actor_id(voice_actor_id: int, limit: int = 100) -> List[Image]:
        """获取声优的所有图片"""
        session = get_session()
        try:
            images = (
                session.query(Image)
                .filter(
                    and_(
                        Image.voice_actor_id == voice_actor_id, Image.is_active == True
                    )
                )
                .limit(limit)
                .all()
            )
            return images
        finally:
            session.close()


class AliasService:
    """别名业务服务"""

    @staticmethod
    def resolve_alias(alias_name: str, user_id: int = None) -> Optional[VoiceActor]:
        """
        解析别名为声优
        优先级：1. 用户自定义别名 2. 全局别名（按优先级）3. 模糊匹配
        """
        session = get_session()
        try:
            # 1. 精确匹配用户自定义别名
            if user_id:
                user_alias = (
                    session.query(Alias)
                    .filter(
                        and_(
                            Alias.alias_name == alias_name,
                            Alias.user_id == user_id,
                            Alias.is_active == True,
                        )
                    )
                    .first()
                )

                if user_alias:
                    actor = VoiceActorService.get_voice_actor_by_id(
                        user_alias.target_voice_actor_id
                    )
                    return actor

            # 2. 精确匹配全局别名（按优先级降序）
            global_alias = (
                session.query(Alias)
                .filter(
                    and_(
                        Alias.alias_name == alias_name,
                        Alias.is_global == True,
                        Alias.is_active == True,
                    )
                )
                .order_by(Alias.priority.desc())
                .first()
            )

            if global_alias:
                actor = VoiceActorService.get_voice_actor_by_id(
                    global_alias.target_voice_actor_id
                )
                return actor

            # 3. 精确匹配声优名称
            actor = VoiceActorService.get_voice_actor_by_name(alias_name)
            if actor:
                return actor

            # 4. 模糊匹配（仅当完全匹配失败时）
            # 这里可以使用编辑距离或其他相似度算法
            # 为简化起见，这里只实现精确匹配

            return None
        finally:
            session.close()

    @staticmethod
    def add_global_alias(
        alias_name: str, voice_actor_id: int, description: str = "", priority: int = 0
    ):
        """添加全局别名"""
        session = get_session()
        try:
            # 检查别名是否已存在
            existing = (
                session.query(Alias)
                .filter(and_(Alias.alias_name == alias_name, Alias.is_global == True))
                .first()
            )

            if existing:
                logger.warning(f"别名 {alias_name} 已存在")
                return False

            # 创建新别名
            alias = Alias(
                alias_name=alias_name,
                target_voice_actor_id=voice_actor_id,
                is_global=True,
                description=description,
                priority=priority,
                is_active=True,
            )
            session.add(alias)
            session.commit()
            # 写后失效：词表是全量快照，不做增量维护，置 None 由下一条消息重建
            invalidate_known_names()
            logger.info(f"添加全局别名: {alias_name} -> {voice_actor_id}")
            return True
        except Exception as e:
            logger.error(f"添加全局别名失败: {e}")
            session.rollback()
            return False
        finally:
            session.close()


class CooldownService:
    """冷却业务服务"""

    @staticmethod
    def check_cooldown(
        user_id: int, command_type: str = "voice_actor"
    ) -> Tuple[bool, int]:
        """
        检查用户是否在冷却中
        返回：(is_in_cooldown, remaining_seconds)
        """
        session = get_session()
        try:
            current_time_ms = int(time.time() * 1000)

            # 查询用户冷却记录
            cooldown = (
                session.query(UserCooldown)
                .filter(
                    and_(
                        UserCooldown.user_id == user_id,
                        UserCooldown.command_type == command_type,
                    )
                )
                .first()
            )

            if not cooldown:
                # 首次请求，无冷却
                return False, 0

            # 计算距上次请求的时间差（毫秒）
            time_since_last = current_time_ms - cooldown.last_request_time
            cooldown_ms = cooldown.cooldown_duration * 1000

            if time_since_last < cooldown_ms:
                # 仍在冷却中
                remaining_ms = cooldown_ms - time_since_last
                remaining_seconds = max(1, (remaining_ms + 999) // 1000)  # 向上取整
                return True, remaining_seconds

            return False, 0
        finally:
            session.close()

    @staticmethod
    def update_cooldown(
        user_id: int, command_type: str = "voice_actor", cooldown_duration: int = None
    ):
        """更新用户冷却状态"""
        if cooldown_duration is None:
            cooldown_duration = settings.cooldown_duration

        session = get_session()
        try:
            current_time_ms = int(time.time() * 1000)

            # 查询或创建冷却记录
            cooldown = (
                session.query(UserCooldown)
                .filter(
                    and_(
                        UserCooldown.user_id == user_id,
                        UserCooldown.command_type == command_type,
                    )
                )
                .first()
            )

            if cooldown:
                cooldown.last_request_time = current_time_ms
                cooldown.cooldown_duration = cooldown_duration
                cooldown.request_count += 1
            else:
                cooldown = UserCooldown(
                    user_id=user_id,
                    command_type=command_type,
                    last_request_time=current_time_ms,
                    cooldown_duration=cooldown_duration,
                    request_count=1,
                )
                session.add(cooldown)

            session.commit()
            logger.debug(f"更新冷却: user={user_id} command={command_type}")
        except Exception as e:
            logger.error(f"更新冷却失败: {e}")
            session.rollback()
        finally:
            session.close()


class RequestLogService:
    """请求日志业务服务"""

    @staticmethod
    def log_request(
        user_id: int,
        group_id: int,
        command: str,
        status: str = "success",
        voice_actor_id: int = None,
        image_id: int = None,
        response_time_ms: int = None,
        error_message: str = None,
        error_code: str = None,
    ):
        """Compatibility facade that delegates to the non-blocking recorder.

        ``error_message`` is intentionally ignored so user content cannot enter
        new rows through legacy call sites.
        """
        try:
            from bot.observability import record_event

            return record_event(
                user_id=user_id,
                group_id=group_id,
                command=command,
                status=status,
                voice_actor_id=voice_actor_id,
                image_id=image_id,
                duration_ms=response_time_ms,
                error_code=error_code,
            )
        except Exception as e:
            logger.error(f"记录请求失败: {e}")
            return False
