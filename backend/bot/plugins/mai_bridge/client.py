"""mai_bridge - maim_message 客户端封装。

以 MessageClient 身份连入麦麦的 Legacy WS server（默认 ws://mai:8000），
入站回调交给上层处理；断线自动指数退避重连。
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional

from loguru import logger

try:
    from maim_message import (
        BaseMessageInfo,
        GroupInfo,
        MessageBase,
        MessageClient,
        Seg,
        UserInfo,
    )

    MAIM_MESSAGE_AVAILABLE = True
except ImportError:  # pragma: no cover - 仅在依赖缺失时触发
    MAIM_MESSAGE_AVAILABLE = False


class MaiBridgeClient:
    """麦麦桥接客户端：单实例，进程内共享。"""

    def __init__(
        self,
        *,
        ws_url: str,
        platform: str,
        token: str,
        on_message: Callable[[dict], Awaitable[None]],
        reconnect_min_seconds: float = 5.0,
        reconnect_max_seconds: float = 60.0,
    ):
        self._ws_url = ws_url.rstrip("/")
        self._platform = platform
        self._token = token or None
        self._on_message = on_message
        self._reconnect_min = reconnect_min_seconds
        self._reconnect_max = reconnect_max_seconds

        self._client: Optional[MessageClient] = None
        self._runner_task: Optional[asyncio.Task] = None
        self._connected = asyncio.Event()
        self._stopped = False

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> None:
        """启动后台连接循环（非阻塞）。"""
        if not MAIM_MESSAGE_AVAILABLE:
            logger.error("maim-message 未安装，麦麦桥接不可用；请检查镜像内依赖")
            return
        if self._runner_task is not None and not self._runner_task.done():
            return
        self._stopped = False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("麦麦桥接启动失败：当前线程没有运行中的事件循环")
            return
        self._runner_task = loop.create_task(self._run_loop(), name="mai_bridge.connection")

    async def stop(self) -> None:
        self._stopped = True
        self._connected.clear()
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception as exc:  # pragma: no cover - 关停路径尽力而为
                logger.debug("mai 客户端 stop 异常（忽略）: {}", exc)
        if self._runner_task is not None:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except (asyncio.CancelledError, Exception):
                pass
            self._runner_task = None

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    async def _run_loop(self) -> None:
        backoff = self._reconnect_min
        while not self._stopped:
            try:
                client = MessageClient(mode="ws")
                client.register_message_handler(self._dispatch)
                await client.connect(url=self._ws_url, platform=self._platform, token=self._token)
                self._client = client
                logger.info("已连接麦麦 maim_message 服务: {} (platform={})", self._ws_url, self._platform)
                backoff = self._reconnect_min
                run_task = asyncio.create_task(client.run(), name="mai_bridge.client_run")

                # client.run() 正常情况下常驻；用轮询检测断线（库未暴露 disconnect 回调）
                while not self._stopped and run_task.done() is False and client.is_connected():
                    await asyncio.sleep(1.0)

                if run_task.done() and run_task.exception() is not None:
                    raise run_task.exception()  # type: ignore[misc]

                if not self._stopped:
                    logger.warning("与麦麦的连接已断开，准备重连")
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("麦麦桥接异常: {}，{}秒后重试", exc, backoff)

            self._connected.clear()
            if self._stopped:
                return
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, self._reconnect_max)

    async def _dispatch(self, message: dict) -> None:
        """库回调：收到麦麦发来的消息（主要是回复）。"""
        try:
            await self._on_message(message)
        except Exception:
            logger.exception("处理麦麦回复时出错")
            if message:
                reply_platform = (message.get("message_info") or {}).get("platform", "?")
                group_id = (message.get("message_info") or {}).get("group_info", {}).get("group_id")
                logger.debug(
                    "出错回复概要: platform={} group_id={} msg_id={}",
                    reply_platform,
                    group_id,
                    (message.get("message_info") or {}).get("message_id"),
                )

    # ------------------------------------------------------------------
    # 出站
    # ------------------------------------------------------------------

    async def send_group_chat(
        self,
        *,
        group_id: str,
        user_id: str,
        nickname: str,
        cardname: Optional[str],
        text: str,
        message_id: str,
        timestamp: float,
        is_at: bool,
        self_id: str,
    ) -> bool:
        """把一条群消息按官方适配器同构结构转发给麦麦。

        消息字典构造对齐 MaiBot-Napcat-Adapter 的 inbound codec：
        additional_config 携带 self_id 与 is_tome，平台名固定 "qqbot"，
        麦麦侧无需感知两个消息源的差异。
        """
        if self._client is None:
            logger.debug("麦麦未连接，丢弃转发: group_id={}", group_id)
            return False

        additional_config: dict[str, Any] = {"self_id": self_id}
        if is_at:
            additional_config["is_tome"] = True

        payload = MessageBase(
            message_info=BaseMessageInfo(
                platform=self._platform,
                message_id=message_id,
                time=timestamp,
                group_info=GroupInfo(platform=self._platform, group_id=str(group_id)),
                user_info=UserInfo(
                    platform=self._platform,
                    user_id=str(user_id),
                    user_nickname=nickname,
                    user_cardname=cardname or None,
                ),
                additional_config=additional_config,
            ),
            message_segment=Seg(type="text", data=text),
            raw_message=text,
        )
        try:
            return bool(await self._client.send_message(payload.to_dict()))
        except Exception as exc:
            logger.warning("转发消息到麦麦失败: {}", exc)
            return False


# 进程级单例（由 handlers.py 初始化并持有）
_instance: Optional[MaiBridgeClient] = None


def set_instance(client: MaiBridgeClient) -> None:
    global _instance
    _instance = client


def get_instance() -> Optional[MaiBridgeClient]:
    return _instance
