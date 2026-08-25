"""
@Bot 命令插件 - 事件处理层
"""

import os
import random
import time

from loguru import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Message
from nonebot.matcher import Matcher
from nonebot.rule import to_me

from bot.plugins.mention_command.services import CheckInService
from bot.observability import elapsed_ms, record_event

# 仅处理 @bot 消息；优先于 voice_actor 插件（voice_actor 为 priority=50）
mention_command_matcher = on_message(rule=to_me(), priority=20, block=False)


@mention_command_matcher.handle()
async def handle_mention_command(event: MessageEvent, matcher: Matcher):
    """处理 @bot 命令"""
    start_ns = time.perf_counter_ns()
    # 延迟导入，避免在 voice_actor 插件加载前触发import导致注册失败
    from bot.plugins.voice_actor.services import VoiceActorService, ImageService

    message_text = event.get_plaintext().strip()

    group_id = None
    if hasattr(event, "group_id"):
        group_id = event.group_id

    # 签到命令
    if message_text == "签到":
        try:
            # 预选幸运声优和图片（首次签到时存储，重复签到时取回已存的）
            actors = VoiceActorService.get_all_voice_actors()
            lucky_actor_id = None
            lucky_image_id = None
            if actors:
                pre_actor = random.choice(actors)
                lucky_actor_id = pre_actor.id
                pre_image = ImageService.get_random_image(pre_actor.id)
                if pre_image:
                    lucky_image_id = pre_image.id

            is_new, total, lucky_actor_id, lucky_image_id = CheckInService.check_in(
                user_id=event.user_id,
                group_id=group_id,
                lucky_actor_id=lucky_actor_id,
                lucky_image_id=lucky_image_id,
            )

            prefix = "签到成功" if is_new else "你今天已经签到过了"
            text = f"{prefix}，累计签到{total}天"

            if lucky_actor_id:
                actor = VoiceActorService.get_voice_actor_by_id(lucky_actor_id)
                if actor:
                    text += f"\n今天你的妈妈是：{actor.name}"

                    image = (
                        ImageService.get_image_by_id(lucky_image_id)
                        if lucky_image_id
                        else None
                    )
                    if image and os.path.exists(image.file_path):
                        file_url = (
                            image.file_path.lstrip("/")
                            if image.file_path.startswith("/")
                            else image.file_path
                        )
                        image_uri = f"file:///{file_url}"
                        reply = Message([
                            MessageSegment.at(event.user_id),
                            MessageSegment.text(" " + text),
                            MessageSegment.image(image_uri),
                        ])
                        await matcher.send(reply)
                        record_event(
                            user_id=event.user_id,
                            group_id=group_id,
                            command="check_in",
                            status="success",
                            voice_actor_id=lucky_actor_id,
                            image_id=lucky_image_id,
                            duration_ms=elapsed_ms(start_ns),
                        )
                        return

            await matcher.send(Message([
                MessageSegment.at(event.user_id),
                MessageSegment.text(" " + text),
            ]))
            record_event(
                user_id=event.user_id,
                group_id=group_id,
                command="check_in",
                status="success",
                voice_actor_id=lucky_actor_id,
                image_id=lucky_image_id,
                duration_ms=elapsed_ms(start_ns),
            )
            return

        except Exception as e:
            logger.error(f"签到失败: {e}", exc_info=True)
            await matcher.send("签到失败，请稍后重试")
            record_event(
                user_id=event.user_id,
                group_id=group_id,
                command="check_in",
                status="error",
                duration_ms=elapsed_ms(start_ns),
                error_code="CHECK_IN_FAILED",
            )
            return

    # 声优列表命令
    if message_text == "声优列表":
        try:
            actors = VoiceActorService.get_all_voice_actors()

            if not actors:
                await matcher.send("当前没有可用的活跃声优")
                record_event(
                    user_id=event.user_id,
                    group_id=group_id,
                    command="voice_actor_list",
                    status="notfound",
                    duration_ms=elapsed_ms(start_ns),
                    error_code="NO_ACTIVE_VOICE_ACTORS",
                )
                return

            actors = sorted(actors, key=lambda x: x.name)
            actor_lines = [f"{actor.name}（{actor.image_count or 0}张）" for actor in actors]
            reply = f"当前可用声优（{len(actors)}）：\n" + "\n".join(actor_lines)

            logger.info(
                "@bot 命令执行成功 - command=声优列表 user_id={} count={}",
                event.user_id,
                len(actors),
            )
            await matcher.send(reply)
            record_event(
                user_id=event.user_id,
                group_id=group_id,
                command="voice_actor_list",
                status="success",
                duration_ms=elapsed_ms(start_ns),
            )
            return

        except Exception as e:
            logger.error(f"处理 @bot 命令失败: {e}", exc_info=True)
            await matcher.send("获取声优列表失败，请稍后重试")
            record_event(
                user_id=event.user_id,
                group_id=group_id,
                command="voice_actor_list",
                status="error",
                duration_ms=elapsed_ms(start_ns),
                error_code="VOICE_ACTOR_LIST_FAILED",
            )
            return
