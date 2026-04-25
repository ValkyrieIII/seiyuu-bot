"""
声优插件 - 事件处理层
"""

import os
import time
from pathlib import Path
from loguru import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message
from nonebot.matcher import Matcher
from nonebot.rule import to_me

from .services import (
    VoiceActorService,
    ImageService,
    AliasService,
    CooldownService,
    RequestLogService,
)
from .utils import normalize_text, calculate_similarity, load_image_file, log_error
from bot.config import settings

# 创建消息匹配器 - 监听所有群消息
matcher = on_message(priority=50, block=False)


@matcher.handle()
async def handle_voice_actor_message(event: GroupMessageEvent, matcher: Matcher):
    """处理群消息中的声优请求"""
    try:
        # 提取消息文本
        message_text = event.get_plaintext().strip()

        if not message_text:
            return

        # 记录请求开始时间
        start_time = time.time()
        user_id = event.user_id
        group_id = event.group_id

        logger.info(f"收到消息 - 用户: {user_id}, 群: {group_id}, 内容: {message_text}")

        # 检查冷却
        is_cooldown, remaining_seconds = CooldownService.check_cooldown(user_id)

        if is_cooldown:
            msg = f"操作冷却中，请在 {remaining_seconds} 秒后重试"
            logger.debug(f"用户 {user_id} 在冷却中")
            RequestLogService.log_request(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="cooldown",
                response_time_ms=int((time.time() - start_time) * 1000),
                error_message=msg,
            )
            # 仅在冷却消息中被@时才回复
            if event.is_tome():
                await matcher.send(msg)
            return

        # 解析别名获取声优
        voice_actor = AliasService.resolve_alias(message_text, user_id)

        if not voice_actor:
            # 未找到匹配的声优
            logger.debug(f"未找到声优: {message_text}")
            RequestLogService.log_request(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="notfound",
                response_time_ms=int((time.time() - start_time) * 1000),
                error_message=f"未找到 {message_text}",
            )
            return

        # 获取随机图片
        image = ImageService.get_random_image(voice_actor.id)

        if not image:
            msg = f"抱歉，{voice_actor.name} 没有可用的图片"
            logger.warning(f"声优 {voice_actor.name} 无可用图片")
            RequestLogService.log_request(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="no_image",
                voice_actor_id=voice_actor.id,
                response_time_ms=int((time.time() - start_time) * 1000),
                error_message=msg,
            )
            await matcher.send(msg)
            return

        # 验证图片文件存在
        if not os.path.exists(image.file_path):
            msg = f"错误：图片文件不存在"
            logger.error(f"图片文件缺失: {image.file_path}")
            RequestLogService.log_request(
                user_id=user_id,
                group_id=group_id,
                command="voice_actor",
                status="file_missing",
                voice_actor_id=voice_actor.id,
                image_id=image.id,
                response_time_ms=int((time.time() - start_time) * 1000),
                error_message=msg,
            )
            await matcher.send(msg)
            return

        # 构建消息
        # 移除文件路径开头的 / 以避免 file:/// 变成 file:////
        file_url = (
            image.file_path.lstrip("/")
            if image.file_path.startswith("/")
            else image.file_path
        )
        image_uri = f"file:///{file_url}"
        logger.debug(f"原始路径: {image.file_path}")
        logger.debug(f"处理后路径: {file_url}")
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
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogService.log_request(
            user_id=user_id,
            group_id=group_id,
            command="voice_actor",
            status="success",
            voice_actor_id=voice_actor.id,
            image_id=image.id,
            response_time_ms=response_time_ms,
        )

        logger.info(
            f"成功响应请求 - 用户: {user_id}, 声优: {voice_actor.name}, 耗时: {response_time_ms}ms"
        )

    except Exception as e:
        logger.error(f"处理消息异常: {e}", exc_info=True)
        try:
            msg = "处理请求时发生错误，请稍后重试"
            RequestLogService.log_request(
                user_id=event.user_id,
                group_id=event.group_id,
                command="voice_actor",
                status="error",
                response_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e),
            )
            await matcher.send(msg)
        except Exception as send_error:
            logger.error(f"发送错误消息失败: {send_error}")
