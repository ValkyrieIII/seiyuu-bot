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

    # 麦麦 v1.2.x 出站组件：
    # - reply.data 是被回复的消息 ID（OneBot message_id），不属于正文
    # - at.data 是目标用户 ID（无昵称，正文里通常已有称呼），渲染成裸数字只会污染消息
    # 两者一律剥离；如需真正的引用回复/At 效果需接入 additional_config 定向字段，后续再做
    if seg_type in ("reply", "at"):
        return "", False

    if seg_type == "image":
        return "[图片]", True

    if isinstance(data, str):
        return data, False

    return "", False
