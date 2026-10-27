"""官方 QQ 消息与现有声优、签到业务之间的适配。"""

from collections import OrderedDict
from base64 import b64encode
import hashlib
from pathlib import Path
import random
import time

from loguru import logger
from nonebot.adapters.qq.event import C2CMessageCreateEvent, GroupMessageCreateEvent
from nonebot.adapters.qq.models import Media
from nonebot.drivers import Request

from bot.config import settings
from bot.identity import resolve_qq_identity
from bot.observability import elapsed_ms, record_event


class RecentMessages:
    """单进程内过滤平台重复投递，容量和保留时间均有界。"""

    def __init__(self, ttl: float = 600, capacity: int = 10000):
        self.ttl = ttl
        self.capacity = capacity
        self._seen = OrderedDict()

    def add(self, key, now=None):
        now = time.monotonic() if now is None else now
        while self._seen:
            _, oldest = next(iter(self._seen.items()))
            if now - oldest < self.ttl:
                break
            self._seen.popitem(last=False)
        if key in self._seen:
            return False
        self._seen[key] = now
        if len(self._seen) > self.capacity:
            self._seen.popitem(last=False)
        return True


_recent_messages = RecentMessages()


def _mentions_other(event, bot):
    # 官方全量事件保留 mentions；若带有其他人的 @，不将去除 @ 后的文本误判为查图。
    mentions = getattr(event, "mentions", None) or []
    if any(getattr(mention, "scope", None) == "all" or not getattr(mention, "is_you", False)
           for mention in mentions):
        return True
    segments = getattr(event, "original_message", None) or event.get_message()
    self_info = getattr(bot, "self_info", None)
    self_id = getattr(self_info, "id", None)
    for segment in segments:
        if segment.type == "mention_everyone":
            return True
        if segment.type in {"mention_user", "group_mention_user"}:
            if not (segment.data.get("is_bot") or segment.data.get("is_you")
                    or segment.data.get("user_id") == self_id):
                return True
    return False


def _image_path(image):
    path = Path(image.file_path)
    if not path.is_absolute() and not path.is_file():
        root = Path(settings.image_folder)
        if path.parts and path.parts[0] == root.name:
            path = root.joinpath(*path.parts[1:])
        else:
            path = root / path
    return path


async def _send_image(bot, event, matcher, path, text=""):
    """显式提交媒体上传参数，发送时关联原消息而不触发主动发送。"""
    content = path.read_bytes()
    is_group = isinstance(event, GroupMessageCreateEvent)
    if is_group:
        target = event.group_openid
        target_param = {"group_openid": target}
        prepare_upload = bot.post_group_upload_prepare
        upload_part = bot._group_upload_part
        url_parts = ("v2", "groups", target, "files")
    else:
        target = event.author.user_openid
        target_param = {"openid": target}
        prepare_upload = bot.post_c2c_upload_prepare
        upload_part = bot._c2c_upload_part
        url_parts = ("v2", "users", target, "files")

    data = {"file_type": 1, "file_name": path.name, "srv_send_msg": False}
    if len(content) <= 5 * 1024 * 1024:
        data["file_data"] = b64encode(content).decode("ascii")
    else:
        prepared = await prepare_upload(
            **target_param, file_type=1, file_name=path.name, file_size=len(content),
            md5=hashlib.md5(content).hexdigest(), sha1=hashlib.sha1(content).hexdigest(),
            md5_10m=hashlib.md5(content[:10 * 1024 * 1024]).hexdigest(),
        )
        for index, part in enumerate(prepared.parts):
            chunk = content[index * prepared.block_size:(index + 1) * prepared.block_size]
            await upload_part(target, prepared.upload_id, part.index, part.presigned_url, chunk)
        data["upload_id"] = prepared.upload_id

    uploaded = await bot._request(Request(
        "POST", bot.adapter.get_api_base().joinpath(*url_parts), json=data,
    ))
    file_info = uploaded.get("file_info")
    if not file_info:
        raise RuntimeError("QQ 媒体上传未返回 file_info")
    event._reply_seq += 1
    kwargs = dict(msg_type=7, content=text or None, media=Media(file_info=file_info),
                  msg_id=event.id, msg_seq=event._reply_seq)
    if is_group:
        await bot.post_group_messages(**target_param, **kwargs)
    else:
        await bot.post_c2c_messages(**target_param, **kwargs)


async def _send_failure(matcher, text):
    try:
        await matcher.send(text)
    except Exception:
        logger.exception("发送官方机器人错误提示失败")


async def handle_message(bot, event, matcher):
    """只处理官方群消息及用户单聊；普通闲聊不落库或记录内容。"""
    if not isinstance(event, (GroupMessageCreateEvent, C2CMessageCreateEvent)):
        return
    is_group = isinstance(event, GroupMessageCreateEvent)
    text = event.get_plaintext().strip()
    if not text:
        return
    # 延迟导入以保持现有插件初始化顺序。
    from bot.plugins.voice_actor.services import (
        AliasService, CooldownService, ImageService, VoiceActorService, get_known_names,
    )

    command = text in {"签到", "声优列表"} and event.is_tome()
    voice_request = is_group and not command and text in get_known_names()
    if not command and not voice_request:
        return
    if voice_request and _mentions_other(event, bot):
        return
    scope = event.group_openid if is_group else "c2c"
    if not _recent_messages.add((bot.self_id, scope, event.id)):
        return

    started = time.perf_counter_ns()
    user_id = None
    group_id = None
    try:
        if is_group:
            # 官方 QQ 只提供按群隔离的 member_openid，且当前应用拿不到 union_openid，
            # 因此同一用户在不同群/私聊会映射到不同内部 ID，签到与冷却按群独立统计。
            group_id = resolve_qq_identity(bot.self_id, "group", event.group_openid)
            user_id = resolve_qq_identity(
                bot.self_id, "member", event.author.member_openid,
                group_openid=event.group_openid,
            )
        else:
            user_id = resolve_qq_identity(bot.self_id, "user", event.author.user_openid)

        if command and text == "签到":
            from bot.plugins.mention_command.services import CheckInService

            actors = VoiceActorService.get_all_voice_actors()
            selected = random.choice(actors) if actors else None
            image = ImageService.get_random_image(selected.id) if selected else None
            is_new, total, actor_id, image_id = CheckInService.check_in(
                user_id=user_id, group_id=group_id,
                lucky_actor_id=selected.id if selected else None,
                lucky_image_id=image.id if image else None,
            )
            if is_new:
                prefix = "签到成功"
            else:
                prefix = "你今天已经在本群签到过了" if is_group else "你今天已经签到过了"
            # 官机群身份按群隔离，累计天数只统计当前群；私聊单独统计。
            scope = "本群" if is_group else ""
            reply = f"{prefix}，{scope}累计签到{total}天"
            actor = VoiceActorService.get_voice_actor_by_id(actor_id) if actor_id else None
            if actor:
                reply += f"\n今天你的妈妈是：{actor.name}"
            image = ImageService.get_image_by_id(image_id) if image_id else None
            path = _image_path(image) if image else None
            if path and path.is_file():
                await _send_image(bot, event, matcher, path, reply)
            else:
                await matcher.send(reply)
            record_event(user_id=user_id, group_id=group_id, command="check_in",
                         status="success", voice_actor_id=actor_id, image_id=image_id,
                         duration_ms=elapsed_ms(started))
            return

        if command:
            actors = sorted(VoiceActorService.get_all_voice_actors(), key=lambda actor: actor.name)
            if actors:
                lines = [f"{actor.name}（{actor.image_count or 0}张）" for actor in actors]
                await matcher.send(f"当前可用声优（{len(actors)}）：\n" + "\n".join(lines))
                status, error = "success", None
            else:
                await matcher.send("当前没有可用的活跃声优")
                status, error = "error", "NO_ACTIVE_VOICE_ACTORS"
            record_event(user_id=user_id, group_id=group_id, command="voice_actor_list",
                         status=status, error_code=error, duration_ms=elapsed_ms(started))
            return

        actor = AliasService.resolve_alias(text, user_id)
        if not actor:
            return
        cooling, seconds = CooldownService.check_cooldown(user_id)
        if cooling:
            record_event(user_id=user_id, group_id=group_id, command="voice_actor",
                         status="cooldown", voice_actor_id=actor.id,
                         error_code="COOLDOWN_ACTIVE", duration_ms=elapsed_ms(started))
            if event.is_tome():
                await matcher.send(f"操作冷却中，请在 {seconds} 秒后重试")
            return
        image = ImageService.get_random_image(actor.id)
        if not image:
            record_event(user_id=user_id, group_id=group_id, command="voice_actor",
                         status="no_image", voice_actor_id=actor.id,
                         error_code="NO_ACTIVE_IMAGE", duration_ms=elapsed_ms(started))
            await matcher.send(f"抱歉，{actor.name} 没有可用的图片")
            return
        path = _image_path(image)
        if not path.is_file():
            record_event(user_id=user_id, group_id=group_id, command="voice_actor",
                         status="file_missing", voice_actor_id=actor.id, image_id=image.id,
                         error_code="IMAGE_FILE_MISSING", duration_ms=elapsed_ms(started))
            await matcher.send("错误：图片文件不存在")
            return
        await _send_image(bot, event, matcher, path)
        CooldownService.update_cooldown(user_id)
        record_event(user_id=user_id, group_id=group_id, command="voice_actor", status="success",
                     voice_actor_id=actor.id, image_id=image.id, duration_ms=elapsed_ms(started))
    except Exception:
        logger.exception("处理官方机器人请求失败")
        if user_id is not None:
            command_name = "check_in" if text == "签到" else (
                "voice_actor_list" if text == "声优列表" else "voice_actor"
            )
            record_event(user_id=user_id, group_id=group_id, command=command_name,
                         status="error", error_code="QQ_OFFICIAL_HANDLER_ERROR",
                         duration_ms=elapsed_ms(started))
        await _send_failure(matcher, "处理请求时发生错误，请稍后重试")
