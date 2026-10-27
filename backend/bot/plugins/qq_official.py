"""QQ 官方机器人事件入口，只在对应接入模式下注册。"""

from bot.config import settings

if settings.bot_platform == "qq_official":
    from nonebot import on_message
    from nonebot.adapters.qq import Bot
    from nonebot.adapters.qq.event import QQMessageEvent
    from nonebot.matcher import Matcher

    from bot.qq_official import handle_message

    official_matcher = on_message(priority=20, block=False)

    @official_matcher.handle()
    async def handle_official_event(bot: Bot, event: QQMessageEvent, matcher: Matcher):
        await handle_message(bot, event, matcher)
