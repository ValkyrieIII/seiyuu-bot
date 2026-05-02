"""
@Bot 命令插件 - 事件处理层
"""

import os
import random

from loguru import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Message
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.exception import FinishedException

from bot.plugins.voice_actor.services import VoiceActorService, ImageService
from bot.plugins.mention_command.services import CheckInService

# 仅处理 @bot 消息；优先于 voice_actor 插件（voice_actor 为 priority=50）
mention_command_matcher = on_message(rule=to_me(), priority=20, block=False)


@mention_command_matcher.handle()
async def handle_mention_command(event: MessageEvent, matcher: Matcher):
    """处理 @bot 命令"""
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
                    text += f"\n今天你的幸运女声优是：{actor.name}"

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
                            MessageSegment.text(text),
                            MessageSegment.image(image_uri),
                        ])
                        await matcher.finish(reply)

            await matcher.finish(text)

        except FinishedException:
            raise

        except Exception as e:
            logger.error(f"签到失败: {e}", exc_info=True)
            await matcher.finish("签到失败，请稍后重试")

    # 声优列表命令
    if message_text == "声优列表":
        try:
            actors = VoiceActorService.get_all_voice_actors()

            if not actors:
                await matcher.finish("当前没有可用的活跃声优")
                return

            actors = sorted(actors, key=lambda x: x.name)
            actor_lines = [f"{actor.name}（{actor.image_count or 0}张）" for actor in actors]
            reply = f"当前可用声优（{len(actors)}）：\n" + "\n".join(actor_lines)

            logger.info(
                "@bot 命令执行成功 - command=声优列表 user_id={} count={}",
                event.user_id,
                len(actors),
            )
            await matcher.finish(reply)

        except FinishedException:
            raise

        except Exception as e:
            logger.error(f"处理 @bot 命令失败: {e}", exc_info=True)
            await matcher.finish("获取声优列表失败，请稍后重试")
