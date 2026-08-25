# -*- coding: utf-8 -*-
"""
图片抓取插件：向目标机器人批量索要声优图片并入库（运维工具）。

触发：@bot 或私聊 bot 发送 "扒图 [声优名] [数量]"
  扒图            # 全部活跃声优，每声优默认 10 张
  扒图 爱美       # 仅爱美，10 张
  扒图 爱美 5     # 仅爱美，5 张
  扒图 5          # 全部声优，每声优 5 张

目标 QQ 通过环境变量 GRAB_TARGET_QQ 配置（默认 3889260680）。
每张之间随机间隔 3-5 秒，防 QQ 风控。
"""

import asyncio
import hashlib
import os
import random
import time
from pathlib import Path

from loguru import logger
from nonebot import on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.rule import to_me

from bot.config import settings

TARGET_QQ = int(os.getenv("GRAB_TARGET_QQ", "3889260680"))
DEFAULT_COUNT = 10
WAIT_TIMEOUT = 20.0        # 等待对方回复图片的超时（秒）
MIN_INTERVAL = 3.0         # 最小间隔（秒）
MAX_INTERVAL = 5.0         # 最大间隔（秒）

_image_queue: "asyncio.Queue[dict]" = asyncio.Queue()
_grabbing = False


# ---------- 私聊图片收集（仅目标机器人回复） ----------
collector = on_message(priority=30, block=False)


@collector.handle()
async def collect_target_images(event: PrivateMessageEvent):
    if event.user_id != TARGET_QQ:
        return
    for seg in event.get_message():
        if seg.type == "image":
            url = seg.data.get("url") or ""
            if url:
                await _image_queue.put({"url": url, "file": seg.data.get("file", "")})


# ---------- 触发命令 ----------
trigger = on_message(rule=to_me(), priority=15, block=False)


@trigger.handle()
async def handle_grab_command(event: MessageEvent, bot: Bot, matcher: Matcher):
    global _grabbing
    text = event.get_plaintext().strip()
    if not text.startswith("扒图"):
        return
    if _grabbing:
        await matcher.send("已有抓图任务运行中，请等待完成。")
        return

    parts = text.split()
    count = DEFAULT_COUNT
    actor_names = None
    for p in parts[1:]:
        if p.isdigit():
            count = int(p)
        else:
            actor_names = [p]
    count = max(1, min(count, 50))

    from bot.plugins.voice_actor.models import VoiceActor, get_session
    from bot.plugins.voice_actor.services import VoiceActorService

    if actor_names:
        actors = []
        for name in actor_names:
            actor = VoiceActorService.get_voice_actor_by_name(name)
            if actor and actor.is_active:
                actors.append(actor)
            else:
                await matcher.send(f"未找到活跃声优：{name}")
        if not actors:
            return
    else:
        session = get_session()
        try:
            actors = (
                session.query(VoiceActor)
                .filter(VoiceActor.is_active == True)
                .order_by(VoiceActor.id.asc())
                .all()
            )
        finally:
            session.close()

    if not actors:
        await matcher.send("没有可抓取的活跃声优。")
        return

    _grabbing = True
    names = "、".join(a.name for a in actors)
    await matcher.send(
        f"开始抓图：目标 {TARGET_QQ}\n声优：{names}\n每声优 {count} 张，间隔 3-5s"
    )
    asyncio.create_task(_run_grab(event, matcher, bot, actors, count))


# ---------- 抓取主流程 ----------
async def _run_grab(event: MessageEvent, matcher: Matcher, bot: Bot, actors, count: int):
    global _grabbing
    total_added = 0
    try:
        for actor in actors:
            added = 0
            for i in range(count):
                try:
                    await bot.send_private_msg(user_id=TARGET_QQ, message=actor.name)
                except Exception as e:
                    logger.error(f"发送私聊失败 {actor.name}: {e}")
                    break

                try:
                    item = await asyncio.wait_for(_image_queue.get(), timeout=WAIT_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.warning(f"{actor.name} 第 {i+1} 次无回复，跳过该声优")
                    break

                try:
                    data, ext = await _download(item["url"])
                    if not data:
                        continue
                    filename = _save_image(actor, data, ext)
                except Exception as e:
                    logger.error(f"保存图片失败 {actor.name}: {e}", exc_info=True)
                    continue

                if filename:
                    added += 1
                    total_added += 1
                    logger.info(f"已抓取 {actor.name}: {filename}")

                await asyncio.sleep(random.uniform(MIN_INTERVAL, MAX_INTERVAL))

            await matcher.send(f"📊 {actor.name} 完成：新增 {added} 张")

        await matcher.send(f"🎉 抓图全部完成，共新增 {total_added} 张。")
    except Exception as e:
        logger.error(f"抓图任务异常: {e}", exc_info=True)
        await matcher.send(f"❌ 抓图任务异常：{e}")
    finally:
        _grabbing = False


# ---------- 工具函数 ----------
async def _download(url: str):
    """下载图片，返回 (bytes, 扩展名)；失败返回 (None, None)。"""
    import aiohttp

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Referer": "https://qun.qq.com/",
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    logger.warning(f"下载失败 HTTP {resp.status}: {url[:80]}")
                    return None, None
                data = await resp.read()
                ctype = resp.headers.get("Content-Type", "")
        return data, _guess_ext(url, ctype)
    except Exception as e:
        logger.warning(f"下载异常: {e}")
        return None, None


def _guess_ext(url: str, ctype: str) -> str:
    path = url.split("?", 1)[0].lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        if path.endswith(ext):
            return ext
    if "png" in ctype:
        return ".png"
    if "gif" in ctype:
        return ".gif"
    if "webp" in ctype:
        return ".webp"
    return ".jpg"


def _save_image(actor, data: bytes, ext: str):
    """按命名规则保存并入库，md5 去重；重复返回 None。"""
    from bot.plugins.voice_actor.models import Image, VoiceActor, get_session

    file_hash = hashlib.md5(data).hexdigest()
    session = get_session()
    try:
        exists = (
            session.query(Image.id).filter(Image.file_hash == file_hash).first()
        )
        if exists:
            logger.info(f"重复图片跳过: {file_hash[:12]}")
            return None

        max_seq = 0
        for (filename,) in session.query(Image.filename).filter(
            Image.voice_actor_id == actor.id
        ):
            stem = filename.rsplit(".", 1)[0]
            parts = stem.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                max_seq = max(max_seq, int(parts[1]))

        new_seq = max_seq + 1
        filename = f"{actor.name}_{new_seq:03d}{ext}"
        target = Path(settings.image_folder) / actor.name / filename
        target.parent.mkdir(parents=True, exist_ok=True)

        # 临时文件放同目录（同一文件系统，rename 原子）；.__tmp_ 前缀会被 watchdog 忽略
        tmp = target.parent / f".__tmp_grab_{int(time.time() * 1000)}_{new_seq}{ext}"
        tmp.write_bytes(data)
        os.replace(tmp, target)

        img = Image(
            voice_actor_id=actor.id,
            filename=filename,
            file_path=str(target),
            size_kb=max(1, len(data) // 1024),
            file_hash=file_hash,
            is_active=True,
        )
        session.add(img)
        actor = session.query(VoiceActor).filter(VoiceActor.id == actor.id).first()
        actor.image_count += 1
        session.commit()
        return filename
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
