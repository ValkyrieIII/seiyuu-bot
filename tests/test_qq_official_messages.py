"""基于真实 QQ 适配器事件模型验证消息分流，不访问 QQ 或数据库。"""

import asyncio
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from nonebot.adapters.qq.bot import _check_at_me
from nonebot.adapters.qq.event import C2CMessageCreateEvent, GroupMessageCreateEvent
from nonebot.drivers import URL

import bot.qq_official as official


def fake_bot():
    return SimpleNamespace(
        self_id="app-id", self_info=SimpleNamespace(id="bot-id"),
        adapter=SimpleNamespace(get_api_base=lambda: URL("https://api.example.com/")),
        _request=AsyncMock(return_value={"file_info": "file-token"}),
        post_group_upload_prepare=AsyncMock(), _group_upload_part=AsyncMock(),
        post_c2c_upload_prepare=AsyncMock(), _c2c_upload_part=AsyncMock(),
        post_group_messages=AsyncMock(), post_c2c_messages=AsyncMock(),
    )


def group_event(content, *, event_id="msg1", mentions=None):
    return GroupMessageCreateEvent(
        id=event_id, content=content, timestamp="2026-10-28T12:00:00+08:00",
        group_id="group", group_openid="group-openid", mentions=mentions,
        author={"id": "author", "bot": False, "member_openid": "member-openid",
                "member_role": "member"},
    )


def private_event(content):
    return C2CMessageCreateEvent(
        id="private-msg", content=content, timestamp="2026-10-28T12:00:00+08:00",
        author={"id": "author", "user_openid": "user-openid"},
    )


def setup_services(monkeypatch, image):
    services = ModuleType("bot.plugins.voice_actor.services")
    actor = SimpleNamespace(id=8, name="声优甲", image_count=1)
    services.get_known_names = lambda: frozenset({"声优甲"})
    services.AliasService = SimpleNamespace(resolve_alias=lambda text, uid: actor)
    services.CooldownService = SimpleNamespace(
        check_cooldown=lambda uid: (False, 0), update_cooldown=lambda uid: None,
    )
    services.ImageService = SimpleNamespace(
        get_random_image=lambda actor_id: image, get_image_by_id=lambda image_id: image,
    )
    services.VoiceActorService = SimpleNamespace(
        get_all_voice_actors=lambda: [actor], get_voice_actor_by_id=lambda actor_id: actor,
    )
    monkeypatch.setitem(sys.modules, "bot.plugins.voice_actor.services", services)
    checkins = ModuleType("bot.plugins.mention_command.services")
    checkins.CheckInService = SimpleNamespace(check_in=lambda **kwargs: (True, 1, 8, image.id))
    monkeypatch.setitem(sys.modules, "bot.plugins.mention_command.services", checkins)
    monkeypatch.setattr(official, "resolve_qq_identity", lambda *args, **kwargs: -1)
    monkeypatch.setattr(official, "record_event", lambda **kwargs: None)
    monkeypatch.setattr(official, "_recent_messages", official.RecentMessages())


def test_group_text_sends_one_image_and_deduplicates(monkeypatch, tmp_path):
    path = tmp_path / "actor.jpg"
    path.write_bytes(b"image")
    image = SimpleNamespace(id=3, filename=path.name, file_path=str(path))
    setup_services(monkeypatch, image)
    bot = fake_bot()
    matcher = SimpleNamespace(send=AsyncMock())
    event = group_event("声优甲")

    asyncio.run(official.handle_message(bot, event, matcher))
    asyncio.run(official.handle_message(bot, event, matcher))

    bot.post_group_messages.assert_awaited_once()
    request = bot._request.await_args.args[0]
    assert request.json["file_name"] == "actor.jpg"
    assert request.json["file_data"] == "aW1hZ2U="
    assert request.json["srv_send_msg"] is False
    assert bot.post_group_messages.await_args.kwargs["msg_id"] == event.id


def test_group_mentions_other_or_everyone_are_ignored(monkeypatch, tmp_path):
    image = SimpleNamespace(id=3, filename="x.jpg", file_path=str(tmp_path / "x.jpg"))
    setup_services(monkeypatch, image)
    bot = SimpleNamespace(self_id="app-id", self_info=SimpleNamespace(id="bot-id"))
    matcher = SimpleNamespace(send=AsyncMock())
    other = {"scope": "single", "bot": False, "id": "other", "is_you": False,
             "member_openid": "other-openid", "username": "other"}
    everyone = {"scope": "all", "is_you": True, "username": "everyone"}
    for mention in (other, everyone):
        event = group_event("声优甲", mentions=[mention])
        _check_at_me(bot, event)
        asyncio.run(official.handle_message(bot, event, matcher))
    matcher.send.assert_not_awaited()


def test_private_checkin_sends_text_and_picture(monkeypatch, tmp_path):
    path = tmp_path / "actor.jpg"
    path.write_bytes(b"image")
    image = SimpleNamespace(id=3, filename=path.name, file_path=str(path))
    setup_services(monkeypatch, image)
    bot = fake_bot()
    matcher = SimpleNamespace(send=AsyncMock())

    asyncio.run(official.handle_message(bot, private_event("签到"), matcher))

    sent = bot.post_c2c_messages.await_args.kwargs
    assert "签到成功，累计签到1天" in sent["content"]
    assert sent["media"].file_info == "file-token"
    assert bot._request.await_args.args[0].json["srv_send_msg"] is False


def test_group_mention_checkin_uses_group_member_identity(monkeypatch, tmp_path):
    path = tmp_path / "actor.jpg"
    path.write_bytes(b"image")
    image = SimpleNamespace(id=3, filename=path.name, file_path=str(path))
    setup_services(monkeypatch, image)
    identities = []
    monkeypatch.setattr(official, "resolve_qq_identity",
                        lambda *args, **kwargs: identities.append((args, kwargs)) or -1)
    bot = fake_bot()
    matcher = SimpleNamespace(send=AsyncMock())
    mention = {"scope": "single", "bot": True, "id": "bot-id", "is_you": True,
               "member_openid": "bot-member-openid", "username": "bot"}
    event = group_event("签到", mentions=[mention])
    _check_at_me(bot, event)

    asyncio.run(official.handle_message(bot, event, matcher))

    assert event.is_tome()
    assert identities == [(('app-id', 'group', 'group-openid'), {}),
                          (('app-id', 'member', 'member-openid'),
                           {'group_openid': 'group-openid'})]
    assert "签到成功" in bot.post_group_messages.await_args.kwargs["content"]


def test_large_group_image_uses_chunked_passive_upload(tmp_path):
    path = tmp_path / "large.jpg"
    path.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    bot = fake_bot()
    bot.post_group_upload_prepare.return_value = SimpleNamespace(
        upload_id="upload-id", block_size=6 * 1024 * 1024,
        parts=[SimpleNamespace(index=1, presigned_url="https://example.com/part")],
    )
    matcher = SimpleNamespace(send=AsyncMock())
    event = group_event("声优甲")

    asyncio.run(official._send_image(bot, event, matcher, path))

    bot._group_upload_part.assert_awaited_once()
    request = bot._request.await_args.args[0]
    assert request.json == {"file_type": 1, "file_name": "large.jpg",
                            "srv_send_msg": False, "upload_id": "upload-id"}
    sent = bot.post_group_messages.await_args.kwargs
    assert sent["msg_id"] == event.id
    assert sent["msg_seq"] == 1
    assert sent["media"].file_info == "file-token"
    matcher.send.assert_not_awaited()
