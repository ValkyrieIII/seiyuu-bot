"""mai_bridge - 转发决策与出站限速（纯逻辑，无 nonebot 依赖）。"""

from __future__ import annotations

import time
from typing import Iterable, Optional, Set, Tuple


def parse_group_allowlist(raw: str) -> Set[str]:
    """解析逗号分隔的群号白名单；空串表示不过滤（空集合表示全部放行）。"""
    return {item.strip() for item in raw.split(",") if item.strip()}


# mention_command 插件拥有的显式命令文本：语义上属于功能车道，不外传给麦麦
OWNED_COMMAND_TEXTS = frozenset({"签到", "声优列表"})


def should_forward(
    *,
    is_self: bool,
    group_id: Optional[int],
    text: str,
    is_command_text: bool,
    allowlist: Set[str],
) -> Tuple[bool, str]:
    """判断一条入站群消息是否转发给麦麦。

    Returns:
        (是否转发, 原因码)。原因码用于日志与观测事件。
    """
    # 硬规则：永不把自己的发言喂回去，切断自循环
    if is_self:
        return False, "self_message"

    if group_id is None:
        return False, "not_group_message"

    # 白名单非空时只放行名单内的群
    if allowlist and str(group_id) not in allowlist:
        return False, "group_not_allowed"

    stripped = (text or "").strip()
    if not stripped:
        return False, "empty_text"

    # @机器人 的功能命令由 mention_command 处理，避免污染麦麦语境
    if is_command_text and stripped in OWNED_COMMAND_TEXTS:
        return False, "owned_command"

    return True, "ok"


class ReplyRateLimiter:
    """最小间隔限速器：间隔内到达的第二条回复直接丢弃（防刷屏优于排队延迟）。"""

    def __init__(self, min_interval_seconds: float):
        self._min_interval = max(0.0, float(min_interval_seconds))
        self._last_ts: Optional[float] = None

    def try_acquire(self, *, now: Optional[float] = None) -> Tuple[bool, float]:
        """尝试获取发送权。

        Returns:
            (是否放行, 距上次发送的秒数；首次为 0.0)
        """
        ts = time.monotonic() if now is None else now
        elapsed = 0.0 if self._last_ts is None else ts - self._last_ts
        if self._last_ts is not None and elapsed < self._min_interval:
            return False, elapsed
        self._last_ts = ts
        return True, elapsed


def truncate_reply(text: str, max_length: int) -> str:
    """按长度上限截断回复文本。"""
    limit = max(1, int(max_length))
    if len(text) <= limit:
        return text
    return text[:limit]


def flatten_segments(segment: dict) -> Tuple[str, bool]:
    """把 maim_message 的 Seg 字典拍平成纯文本。

    Returns:
        (文本, 是否包含图片)
    """
    seg_type = str(segment.get("type") or "")
    data = segment.get("data")

    if seg_type == "seglist" and isinstance(data, list):
        parts: list[str] = []
        has_image = False
        for child in data:
            if isinstance(child, dict):
                child_text, child_image = flatten_segments(child)
                has_image = has_image or child_image
                if child_text:
                    parts.append(child_text)
        return "".join(parts), has_image

    if seg_type == "image":
        return "[图片]", True

    if isinstance(data, str):
        return data, False

    return "", False
