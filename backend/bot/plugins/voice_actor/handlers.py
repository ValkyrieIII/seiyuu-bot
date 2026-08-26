"""
声优插件 - 事件处理层
"""

import os
from pathlib import Path
import time
from loguru import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message
from nonebot.matcher import Matcher
from bot.config import settings
from .services import AliasService, CooldownService, ImageService, get_known_names
from bot.observability import (
    elapsed_ms,
    record_event,
)

# 创建消息匹配器 - 监听所有群消息
matcher = on_message(priority=50, block=False)


@matcher.handle()
async def handle_voice_actor_message(event: GroupMessageEvent, matcher: Matcher):
    """处理群消息中的声优请求"""
    start_ns = time.perf_counter_ns()
    should_report_failure = event.is_tome()
    try:
        # 提取消息文本
        message_text = event.get_plaintext().strip()

        if not message_text:
            return

        # 忽略 @ 了其他用户（含 @全体成员）的消息：
        # get_plaintext() 会滤掉 at 段，导致 "@别人 声优名" 被解析成 "声优名" 而误触发
        for seg in event.get_message():
            if seg.type == "at" and seg.data.get("qq") != str(event.self_id):
                logger.debug("消息 @ 了其他用户，忽略 - user_id={}", event.user_id)
                return

        user_id = event.user_id
        group_id = event.group_id

        # These explicit commands are owned by mention_command and must not
        # be misattributed to the voice-actor resolver when propagation continues.
        if event.is_tome() and message_text in {"签到", "声优列表"}:
            return

        # 词表拦截：不在别名词表内的文本（绝大多数群闲聊）直接跳过。
        # 本业务只能观测"命中"，未命中不可观测（无法区分闲聊与找图意图），
        # 因此不发任何事件；不存在 notfound 状态。
        if message_text not in get_known_names():
            return

        # Resolve before cooldown so unrelated ordinary group chat is never logged.
        voice_actor = AliasService.resolve_alias(message_text, user_id)

        if not voice_actor:
            # 词表命中但解析失败（如缓存重建窗口内的陈旧词条）：静默退出。
            logger.debug(f"词表命中但未解析到声优: {message_text}")
            return

        should_report_failure = True

        # 检查冷却
        is_cooldown, remaining_seconds = CooldownService.check_cooldown(user_id)

        if is_cooldown:
            msg = f"操作冷却中，请在 {remaining_seconds} 秒后重试"
            logger.debug(f"用户 {user_id} 在冷却中")
            record_event(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="cooldown",
                voice_actor_id=voice_actor.id,
                duration_ms=elapsed_ms(start_ns),
                error_code="COOLDOWN_ACTIVE",
            )
            # 仅在冷却消息中被@时才回复
            if event.is_tome():
                await matcher.send(msg)
            return

        # 获取随机图片
        image = ImageService.get_random_image(voice_actor.id)

        if not image:
            msg = f"抱歉，{voice_actor.name} 没有可用的图片"
            logger.warning(f"声优 {voice_actor.name} 无可用图片")
            record_event(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="no_image",
                voice_actor_id=voice_actor.id,
                duration_ms=elapsed_ms(start_ns),
                error_code="NO_ACTIVE_IMAGE",
            )
            await matcher.send(msg)
            return

        # 验证图片文件存在
        if not os.path.exists(image.file_path):
            msg = f"错误：图片文件不存在"
            logger.error(f"图片文件缺失: {image.file_path}")
            record_event(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="file_missing",
                voice_actor_id=voice_actor.id,
                image_id=image.id,
                duration_ms=elapsed_ms(start_ns),
                error_code="IMAGE_FILE_MISSING",
            )
            await matcher.send(msg)
            return

        # 构建消息
        # 兼容 DB 中相对(images/...)与绝对(/app/images/...)两种存储格式
        image_path = Path(image.file_path)
        if not image_path.is_absolute():
            image_path = Path(settings.image_folder) / image.filename
        image_uri = f"file://{image_path}"
        logger.debug(f"原始路径: {image.file_path}")
        logger.debug(f"处理后路径: {image_path}")
        logger.debug(f"最终 URI: {image_uri}")
        msg_segments = [
            # MessageSegment.text(f"给你 {voice_actor.name} 的图片~\n"),
            MessageSegment.image(image_uri),
        ]
        msg = Message(msg_segments)

        # 发送消息
        await matcher.send(msg)

        # 更新冷却
        CooldownService.update_cooldown(user_id)

        # 记录成功请求
        response_time_ms = elapsed_ms(start_ns)
        record_event(
            user_id=user_id,
            group_id=group_id,
            command="voice_actor",
            status="success",
            voice_actor_id=voice_actor.id,
            image_id=image.id,
            duration_ms=response_time_ms,
        )

        logger.info(
            f"成功响应请求 - 用户: {user_id}, 声优: {voice_actor.name}, 耗时: {response_time_ms}ms"
        )

    except Exception as e:
        logger.error(f"处理消息异常: {e}", exc_info=True)
        if not should_report_failure:
            return
        try:
            msg = "处理请求时发生错误，请稍后重试"
            record_event(
                user_id=event.user_id,
                group_id=event.group_id,
                command="voice_actor",
                status="error",
                duration_ms=elapsed_ms(start_ns),
                error_code="VOICE_ACTOR_HANDLER_ERROR",
            )
            await matcher.send(msg)
        except Exception as send_error:
            logger.error(f"发送错误消息失败: {send_error}")
