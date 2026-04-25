"""
图片目录监听器
"""

import os
import threading
from typing import Optional
from loguru import logger
from bot.config import settings
from bot.plugins.voice_actor.utils import scan_image_records

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:  # pragma: no cover - 依赖缺失时降级
    Observer = None
    FileSystemEventHandler = object


_OBSERVER = None
_DEBOUNCE_TIMER = None
_DEBOUNCE_LOCK = threading.Lock()


class _ImageChangeHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds: float):
        super().__init__()
        self.debounce_seconds = debounce_seconds

    def on_any_event(self, event):
        src_path = getattr(event, "src_path", "") or ""
        if os.path.basename(src_path).startswith(".__tmp_"):
            return
        _schedule_scan(self.debounce_seconds)


def _run_scan_once():
    global _DEBOUNCE_TIMER
    with _DEBOUNCE_LOCK:
        _DEBOUNCE_TIMER = None

    try:
        scan_image_records(settings.image_folder)
    except Exception as e:
        logger.error(f"监听触发扫描失败: {e}", exc_info=True)


def _schedule_scan(debounce_seconds: float):
    global _DEBOUNCE_TIMER
    with _DEBOUNCE_LOCK:
        if _DEBOUNCE_TIMER is not None:
            _DEBOUNCE_TIMER.cancel()

        _DEBOUNCE_TIMER = threading.Timer(debounce_seconds, _run_scan_once)
        _DEBOUNCE_TIMER.daemon = True
        _DEBOUNCE_TIMER.start()


def start_image_watcher(base_path: Optional[str] = None, debounce_seconds: float = 0.8) -> bool:
    """启动图片目录监听器。"""
    global _OBSERVER

    if Observer is None:
        logger.warning("watchdog 未安装，图片目录监听器未启动")
        return False

    if _OBSERVER is not None:
        logger.info("图片目录监听器已启动，跳过重复启动")
        return True

    target_path = base_path or settings.image_folder
    if not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)

    try:
        handler = _ImageChangeHandler(debounce_seconds=debounce_seconds)
        observer = Observer()
        observer.schedule(handler, target_path, recursive=True)
        observer.daemon = True
        observer.start()
        _OBSERVER = observer
        logger.info(f"图片目录监听器已启动: {target_path}")
        return True
    except Exception as e:
        logger.error(f"启动图片目录监听器失败: {e}", exc_info=True)
        return False


def stop_image_watcher():
    """停止图片目录监听器。"""
    global _OBSERVER
    if _OBSERVER is None:
        return

    try:
        _OBSERVER.stop()
        _OBSERVER.join(timeout=2)
    except Exception as e:
        logger.error(f"停止图片目录监听器失败: {e}")
    finally:
        _OBSERVER = None
