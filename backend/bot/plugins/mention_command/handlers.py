"""
@Bot 命令插件 - 事件处理层
"""

from loguru import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.exception import FinishedException

from bot.plugins.voice_actor.services import VoiceActorService

# 仅处理 @bot 消息；优先于 voice_actor 插件（voice_actor 为 priority=50）
mention_command_matcher = on_message(rule=to_me(), priority=20, block=False)


@mention_command_matcher.handle()
async def handle_mention_command(event: MessageEvent, matcher: Matcher):
    """处理 @bot 命令"""
    message_text = event.get_plaintext().strip()

    # 当前仅支持一个命令：声优列表
    if message_text != "声优列表":
        return

    try:
        actors = VoiceActorService.get_all_voice_actors()

        if not actors:
            await matcher.finish("当前没有可用的活跃声优")
            return

        # actor_names = sorted(actor.name for actor in actors)
        # reply = f"当前可用声优（{len(actor_names)}）：\n" + "、".join(actor_names)
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
