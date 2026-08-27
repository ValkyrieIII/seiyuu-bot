"""mai_bridge - NoneBot 事件接入与麦麦回复投递。"""

from __future__ import annotations

import time

from loguru import logger
from nonebot import get_bot, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment

from bot.config import settings
from bot.observability import elapsed_ms, record_event

from .client import MaiBridgeClient, get_instance, set_instance
from .router import (
    ReplyRateLimiter,
    flatten_segments,
    parse_group_allowlist,
    should_forward,
    truncate_reply,
)

_matcher = on_message(priority=60, block=False)

_rate_limiter = ReplyRateLimiter(settings.mai_min_interval_seconds)
_allowlist = parse_group_allowlist(settings.mai_allowed_groups)


def _self_user_id() -> Optional[int]:
    """观测事件的 user_id 哨兵：优先机器人自身 QQ 号，不可用时放弃记录。"""
    try:
        value = int(settings.bot_qq)
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _record_outbound(
    *,
    status: str,
    group_id: int,
    started_ns: int,
    error_code: Optional[str] = None,
) -> None:
    """出站方向的观测入口；无法确定 user_id 时降级为仅日志。"""
    user_id = _self_user_id()
    if user_id is None:
        return
    record_event(
        user_id=user_id,
        group_id=group_id,
        command="mai_chat",
        status=status,
        duration_ms=elapsed_ms(started_ns),
        error_code=error_code,
    )


async def _deliver_reply(payload: dict) -> None:
    """把麦麦的回复经 OneBot 投递到群聊。

    麦麦回复的 message_info.group_info.group_id 指明目标群；
    message_segment 支持 text / image(base64) / seglist 混合。
    """
    started_ns = time.perf_counter_ns()
    info = payload.get("message_info") or {}
    group_raw = (info.get("group_info") or {}).get("group_id")
    if not group_raw:
        logger.debug("麦麦回复缺少 group_id，丢弃")
        return

    try:
        group_id = int(str(group_raw))
    except ValueError:
        logger.warning("麦麦回复 group_id 非法: {!r}", group_raw)
        return

    # 群白名单同样约束出站，防止麦麦主动发往未授权群
    if _allowlist and str(group_id) not in _allowlist:
        _record_outbound(
            status="error",
            group_id=group_id,
            started_ns=started_ns,
            error_code="GROUP_NOT_ALLOWED",
        )
        return

    ok, elapsed_seconds = _rate_limiter.try_acquire()
    if not ok:
        logger.debug(
            "麦麦回复触发限速被丢弃: group_id={} 距上次{:.1f}s", group_id, elapsed_seconds
        )
        _record_outbound(
            status="error",
            group_id=group_id,
            started_ns=started_ns,
            error_code="RATE_LIMITED",
        )
        return

    segment = payload.get("message_segment") or {}
    if not isinstance(segment, dict):
        segment = {}
    text, has_image = flatten_segments(segment)

    # seglist 图文混合时一期先投文本（占位符剔除），纯图直投 base64
    if has_image and isinstance(segment.get("data"), str):
        msg = Message([MessageSegment.image(f"base64://{segment['data']}")])
    else:
        text = truncate_reply(text.replace("[图片]", ""), settings.mai_max_reply_length).strip()
        if not text:
            logger.debug("麦麦回复无有效文本，忽略: group_id={}", group_id)
            return
        msg = Message(text)

    try:
        bot = get_bot()
        await bot.call_api("send_group_msg", group_id=group_id, message=msg)
    except Exception as exc:
        logger.error("麦麦回复投递失败: group_id={}, {}", group_id, exc)
        _record_outbound(
            status="error",
            group_id=group_id,
            started_ns=started_ns,
            error_code="MAI_DELIVER_FAILED",
        )
        return

    _record_outbound(status="success", group_id=group_id, started_ns=started_ns)
    logger.info("已投递麦麦回复 - group_id={}, 文本长度={}", group_id, len(text))


@_matcher.handle()
async def handle_forward_to_mai(event: GroupMessageEvent):
    """所有群消息入站的转发入口（priority=60，位于功能插件之后）。"""
    client = _get_or_bootstrap()
    if client is None:
        return

    text = event.get_plaintext().strip()

    forwarded, reason = should_forward(
        is_self=str(event.user_id) == str(event.self_id),
        group_id=event.group_id,
        text=text,
        is_command_text=event.is_tome(),
        allowlist=_allowlist,
    )

    # 未转发的消息与 voice_actor 未命中同理：属正常闲聊路径，不做观测、不刷日志
    if not forwarded:
        if reason != "self_message":
            logger.debug("消息不转发给麦麦({}): group_id={}", reason, event.group_id)
        return

    sent = await client.send_group_chat(
        group_id=str(event.group_id),
        user_id=str(event.user_id),
        nickname=event.sender.nickname or str(event.user_id),
        cardname=(event.sender.card or None),
        text=text,
        message_id=str(event.message_id),
        timestamp=float(event.time),
        is_at=event.is_tome(),
        self_id=str(event.self_id),
    )
    if sent:
        logger.info(
            "已转发到麦麦 - group_id={}, 用户={}, 文本长度={}",
            event.group_id,
            event.user_id,
            len(text),
        )


def _get_or_bootstrap() -> MaiBridgeClient | None:
    """返回运行中的客户端实例；启用状态下惰性建立连接。"""
    client = get_instance()
    if client is not None:
        return client
    return _bootstrap()


def warmup() -> None:
    """nonebot 启动时预热：尽早建立与麦麦的连接。"""
    if not settings.mai_enabled:
        logger.info("麦麦桥接未启用 (MAI_ENABLED=false)")
        return
    _bootstrap()


def _bootstrap() -> MaiBridgeClient | None:
    if not settings.mai_enabled:
        return None
    client = MaiBridgeClient(
        ws_url=settings.mai_ws_url,
        platform=settings.mai_platform_name,
        token=settings.mai_auth_token,
        on_message=_deliver_reply,
    )
    set_instance(client)
    client.start()
    logger.info(
        "麦麦桥接已启动: {} (platform={})", settings.mai_ws_url, settings.mai_platform_name
    )
    return client
