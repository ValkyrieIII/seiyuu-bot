"""mai_bridge 纯逻辑单测：转发决策 / 段拍平。"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from bot.plugins.mai_bridge.router import (
    flatten_segments,
    parse_group_allowlist,
    should_forward,
    truncate_reply,
)


class TestParseGroupAllowlist:
    def test_empty_means_all_groups(self):
        assert parse_group_allowlist("") == set()
        assert parse_group_allowlist("  , , ") == set()

    def test_parses_and_strips(self):
        assert parse_group_allowlist("123, 456,789") == {"123", "456", "789"}


class TestShouldForward:
    ALLOW = {"10001"}

    def test_never_forward_self_messages(self):
        ok, reason = should_forward(
            is_self=True, group_id=1, text="hi", is_command_text=False, allowlist=set()
        )
        assert not ok
        assert reason == "self_message"

    def test_requires_group(self):
        ok, reason = should_forward(
            is_self=False, group_id=None, text="hi", is_command_text=False, allowlist=set()
        )
        assert not ok
        assert reason == "not_group_message"

    def test_allowlist_filters_unknown_groups(self):
        ok, reason = should_forward(
            is_self=False,
            group_id=99999,
            text="今天天气不错",
            is_command_text=False,
            allowlist=self.ALLOW,
        )
        assert not ok
        assert reason == "group_not_allowed"

    def test_empty_text_skipped(self):
        ok, reason = should_forward(
            is_self=False, group_id=1, text="   ", is_command_text=False, allowlist=set()
        )
        assert not ok
        assert reason == "empty_text"

    @pytest.mark.parametrize("cmd", ["签到", "声优列表"])
    def test_owned_commands_not_forwarded(self, cmd: str):
        ok, reason = should_forward(
            is_self=False, group_id=1, text=cmd, is_command_text=True, allowlist=set()
        )
        assert not ok
        assert reason == "owned_command"

    def test_same_text_without_at_is_chat(self):
        # 不带 @ 的"签到"只是普通闲聊，应照常外传给麦麦
        ok, reason = should_forward(
            is_self=False, group_id=1, text="签到", is_command_text=False, allowlist=set()
        )
        assert ok and reason == "ok"

    def test_ordinary_chat_passes(self):
        ok, reason = should_forward(
            is_self=False,
            group_id=10001,
            text="大家中午吃什么",
            is_command_text=False,
            allowlist=self.ALLOW,
        )
        assert ok and reason == "ok"


class TestTruncateAndFlatten:
    def test_truncate_keeps_short(self):
        assert truncate_reply("短文本", 10) == "短文本"

    def test_truncate_cuts_long(self):
        assert truncate_reply("x" * 30, 10) == "x" * 10

    def test_truncate_min_length_floor(self):
        assert truncate_reply("abcdef", 0) == "a"

    def test_flatten_text_segment(self):
        text, has_image = flatten_segments({"type": "text", "data": "你好"})
        assert text == "你好" and not has_image

    def test_flatten_image_segment(self):
        text, has_image = flatten_segments({"type": "image", "data": "AAAA"})
        assert text == "[图片]" and has_image

    def test_flatten_seglist_mixed(self):
        seg = {
            "type": "seglist",
            "data": [
                {"type": "text", "data": "看这个 "},
                {"type": "image", "data": "AAAA"},
                {"type": "text", "data": " 好笑"},
            ],
        }
        text, has_image = flatten_segments(seg)
        assert text == "看这个 [图片] 好笑"
        assert has_image

    def test_flatten_unknown_type_returns_empty(self):
        text, has_image = flatten_segments({"type": "mystery", "data": None})
        assert text == "" and not has_image

    def test_flatten_reply_segment_stripped(self):
        """reply.data 是被回复的消息 ID，不属于正文。"""
        text, has_image = flatten_segments({"type": "reply", "data": "185498843"})
        assert text == "" and not has_image

    def test_flatten_at_segment_stripped(self):
        """at.data 是目标用户 ID，无昵称可渲染，直接剥离。"""
        seg = {
            "type": "seglist",
            "data": [
                {"type": "at", "data": "2717098884"},
                {"type": "text", "data": "别慌"},
            ],
        }
        text, has_image = flatten_segments(seg)
        assert text == "别慌" and not has_image
