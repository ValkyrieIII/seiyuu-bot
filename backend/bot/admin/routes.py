# -*- coding: utf-8 -*-
"""管理后台路由：挂载到 NoneBot 的 FastAPI 应用。"""

import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy import func

from bot.plugins.voice_actor.models import (
    Alias,
    Image,
    RequestLog,
    VoiceActor,
    get_session,
)
from bot.plugins.voice_actor.utils import scan_image_records
from bot.config import settings
from .schemas import AliasCreate, VoiceActorCreate, VoiceActorUpdate, ImageUpdate


STATIC_INDEX = Path(__file__).parent / "static" / "index.html"
STATIC_DIR = Path(__file__).parent / "static"


def ok(data: Any):
    """统一成功响应结构。"""
    return {"success": True, "data": data}


def register_admin_routes(driver) -> None:
    """从 NoneBot driver 获取 FastAPI app，并注册管理后台路由。"""
    app = getattr(driver, "server_app", None)
    if app is None:
        logger.warning("未找到 FastAPI server_app，管理后台未挂载")
        return

    if getattr(app.state, "admin_routes_registered", False):
        logger.info("管理后台路由已注册，跳过重复挂载")
        return

    # 管理后台统一前缀，便于反向代理和权限隔离
    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.get("")
    async def admin_index():
        # 返回管理后台单页入口
        if not STATIC_INDEX.exists():
            raise HTTPException(status_code=500, detail="Admin page not found")
        return FileResponse(STATIC_INDEX)

    @router.get("/api/overview")
    async def overview():
        # 概览页统计：总量 + 近 24 小时表现 + 最新请求日志
        session = get_session()
        try:
            actor_total = session.query(func.count(VoiceActor.id)).scalar() or 0
            image_total = session.query(func.count(Image.id)).scalar() or 0
            alias_total = session.query(func.count(Alias.id)).scalar() or 0

            since = datetime.utcnow() - timedelta(hours=24)
            request_24h = (
                session.query(func.count(RequestLog.id))
                .filter(
                    RequestLog.created_at >= since,
                    RequestLog.status != "notfound",
                )
                .scalar()
                or 0
            )
            success_24h = (
                session.query(func.count(RequestLog.id))
                .filter(
                    RequestLog.created_at >= since,
                    RequestLog.status == "success",
                )
                .scalar()
                or 0
            )
            success_rate = round((success_24h / request_24h) * 100, 2) if request_24h else 0

            recent_logs = (
                session.query(RequestLog)
                .filter(RequestLog.status != "notfound")
                .order_by(RequestLog.created_at.desc())
                .limit(20)
                .all()
            )

            logs_data = [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "group_id": log.group_id,
                    "command": log.command,
                    "status": log.status,
                    "response_time_ms": log.response_time_ms,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in recent_logs
            ]

            return ok(
                {
                    "voice_actor_total": actor_total,
                    "image_total": image_total,
                    "alias_total": alias_total,
                    "request_24h": request_24h,
                    "success_rate_24h": success_rate,
                    "recent_logs": logs_data,
                }
            )
        finally:
            session.close()

    @router.get("/api/voice-actors")
    async def get_voice_actors():
        # 声优列表（管理端）
        session = get_session()
        try:
            actors = session.query(VoiceActor).order_by(VoiceActor.name.asc()).all()
            data = [
                {
                    "id": actor.id,
                    "name": actor.name,
                    "description": actor.description or "",
                    "image_count": actor.image_count or 0,
                    "is_active": bool(actor.is_active),
                }
                for actor in actors
            ]
            return ok(data)
        finally:
            session.close()

    @router.post("/api/voice-actors")
    async def create_voice_actor(payload: VoiceActorCreate):
        # 新增声优：数据库新增 + 文件系统创建同名目录
        session = get_session()
        try:
            name = payload.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="name cannot be empty")

            existing = session.query(VoiceActor).filter(VoiceActor.name == name).first()
            if existing:
                raise HTTPException(status_code=409, detail="voice actor already exists")

            # 与新增声优同步创建图片目录，避免后续上传/扫描时目录缺失
            actor_folder = Path(settings.image_folder) / name
            try:
                actor_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"创建声优图片目录失败 {actor_folder}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="failed to create actor folder")

            actor = VoiceActor(
                name=name,
                description=payload.description.strip(),
                image_count=0,
                is_active=True,
            )
            session.add(actor)
            session.commit()
            return ok({"id": actor.id})
        finally:
            session.close()

    @router.patch("/api/voice-actors/{actor_id}")
    async def update_voice_actor(actor_id: int, payload: VoiceActorUpdate):
        # 更新声优元信息（描述、启用状态）
        session = get_session()
        try:
            actor = session.query(VoiceActor).filter(VoiceActor.id == actor_id).first()
            if not actor:
                raise HTTPException(status_code=404, detail="voice actor not found")

            changed = False
            if payload.description is not None:
                actor.description = payload.description.strip()
                changed = True
            if payload.is_active is not None:
                actor.is_active = payload.is_active
                changed = True

            if not changed:
                raise HTTPException(status_code=400, detail="no fields to update")

            session.commit()
            return ok({"updated": True})
        finally:
            session.close()

    @router.get("/api/aliases")
    async def get_aliases():
        # 别名列表，联表返回目标声优名
        session = get_session()
        try:
            rows = (
                session.query(Alias, VoiceActor)
                .join(VoiceActor, VoiceActor.id == Alias.target_voice_actor_id)
                .order_by(Alias.priority.desc(), Alias.id.desc())
                .all()
            )
            data = [
                {
                    "id": alias.id,
                    "alias_name": alias.alias_name,
                    "target_voice_actor_id": alias.target_voice_actor_id,
                    "target_voice_actor_name": actor.name,
                    "priority": alias.priority,
                    "is_global": bool(alias.is_global),
                    "is_active": bool(alias.is_active),
                }
                for alias, actor in rows
            ]
            return ok(data)
        finally:
            session.close()

    @router.post("/api/aliases")
    async def create_alias(payload: AliasCreate):
        # 新增全局别名，避免与已有全局同名别名冲突
        session = get_session()
        try:
            alias_name = payload.alias_name.strip()
            if not alias_name:
                raise HTTPException(status_code=400, detail="alias_name cannot be empty")

            actor = (
                session.query(VoiceActor)
                .filter(VoiceActor.id == payload.target_voice_actor_id)
                .first()
            )
            if not actor:
                raise HTTPException(status_code=404, detail="target voice actor not found")

            existing = (
                session.query(Alias)
                .filter(
                    Alias.alias_name == alias_name,
                    Alias.user_id.is_(None),
                    Alias.is_global == True,
                )
                .first()
            )
            if existing:
                raise HTTPException(status_code=409, detail="alias already exists")

            alias = Alias(
                alias_name=alias_name,
                target_voice_actor_id=payload.target_voice_actor_id,
                is_global=True,
                user_id=None,
                description=payload.description.strip(),
                priority=payload.priority,
                is_active=True,
            )
            session.add(alias)
            session.commit()
            return ok({"id": alias.id})
        finally:
            session.close()

    @router.delete("/api/aliases/{alias_id}")
    async def delete_alias(alias_id: int):
        # 删除别名（物理删除）
        session = get_session()
        try:
            alias = session.query(Alias).filter(Alias.id == alias_id).first()
            if not alias:
                raise HTTPException(status_code=404, detail="alias not found")
            session.delete(alias)
            session.commit()
            return ok({"deleted": True})
        finally:
            session.close()

    @router.post("/api/sync-images")
    async def sync_images():
        # 触发图片目录扫描与数据库同步（复用现有核心逻辑）
        try:
            (
                added_actors,
                disabled_actors,
                added_images,
                updated_images,
                disabled_images,
            ) = scan_image_records()
            return ok(
                {
                    "added_actors": added_actors,
                    "disabled_actors": disabled_actors,
                    "added_images": added_images,
                    "updated_images": updated_images,
                    "disabled_images": disabled_images,
                }
            )
        except Exception as e:
            logger.error(f"触发图片同步失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="sync failed")

    # ---------- 图片管理 ----------

    VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    @router.get("/api/images")
    async def list_images(
        voice_actor_id: Optional[int] = Query(None),
        is_active: Optional[bool] = Query(None),
        search: str = Query(default=""),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ):
        """图片列表，支持按声优、状态、文件名筛选和分页。"""
        session = get_session()
        try:
            q = session.query(Image, VoiceActor).join(
                VoiceActor, VoiceActor.id == Image.voice_actor_id
            )

            if voice_actor_id is not None:
                q = q.filter(Image.voice_actor_id == voice_actor_id)
            if is_active is not None:
                q = q.filter(Image.is_active == is_active)
            if search.strip():
                q = q.filter(Image.filename.contains(search.strip()))

            total = q.count()
            rows = (
                q.order_by(Image.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            items = [
                {
                    "id": img.id,
                    "voice_actor_id": img.voice_actor_id,
                    "voice_actor_name": actor.name,
                    "filename": img.filename,
                    "file_path": img.file_path,
                    "size_kb": img.size_kb or 0,
                    "file_hash": img.file_hash or "",
                    "is_active": bool(img.is_active),
                    "created_at": img.created_at.isoformat() if img.created_at else None,
                }
                for img, actor in rows
            ]
            return ok(
                {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "items": items,
                }
            )
        finally:
            session.close()

    @router.post("/api/images/upload")
    async def upload_image(
        file: UploadFile = File(...),
        voice_actor_id: int = Query(...),
    ):
        """上传图片到指定声优目录。"""
        session = get_session()
        try:
            actor = (
                session.query(VoiceActor)
                .filter(VoiceActor.id == voice_actor_id, VoiceActor.is_active == True)
                .first()
            )
            if not actor:
                raise HTTPException(status_code=404, detail="voice actor not found or inactive")

            # 校验扩展名
            _, ext = os.path.splitext(file.filename or "")
            ext_lower = ext.lower()
            if ext_lower not in VALID_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"unsupported file type: {ext_lower}",
                )

            # 读取文件内容，计算 hash 和大小
            content = await file.read()
            file_hash = hashlib.md5(content).hexdigest()
            size_kb = max(1, len(content) // 1024)

            # 生成目标文件名：{声优名}_{序号}.{ext}
            actor_dir = Path(settings.image_folder) / actor.name
            actor_dir.mkdir(parents=True, exist_ok=True)

            # 取该目录下最大序号
            max_seq = 0
            existing = session.query(Image).filter(
                Image.voice_actor_id == voice_actor_id
            ).all()
            for img in existing:
                # 从 filename 中解析序号，如 中岛由贵_003.jpg → 3
                name_no_ext = img.filename.rsplit(".", 1)[0]
                parts = name_no_ext.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    max_seq = max(max_seq, int(parts[1]))

            new_seq = max_seq + 1
            new_filename = f"{actor.name}_{new_seq:03d}{ext_lower}"
            dest_path = actor_dir / new_filename

            # 写入文件
            with open(dest_path, "wb") as f:
                f.write(content)

            # 创建 DB 记录
            image = Image(
                voice_actor_id=voice_actor_id,
                filename=new_filename,
                file_path=str(dest_path),
                size_kb=size_kb,
                file_hash=file_hash,
                is_active=True,
            )
            session.add(image)
            session.flush()

            # 更新声优 image_count
            session.query(VoiceActor).filter(VoiceActor.id == voice_actor_id).update(
                {"image_count": VoiceActor.image_count + 1}
            )
            session.commit()

            return ok(
                {
                    "id": image.id,
                    "filename": new_filename,
                    "voice_actor_id": voice_actor_id,
                    "size_kb": size_kb,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"上传图片失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="upload failed")
        finally:
            session.close()

    @router.patch("/api/images/{image_id}")
    async def update_image(image_id: int, payload: ImageUpdate):
        """切换图片启用/禁用状态。"""
        session = get_session()
        try:
            image = session.query(Image).filter(Image.id == image_id).first()
            if not image:
                raise HTTPException(status_code=404, detail="image not found")

            image.is_active = payload.is_active
            session.commit()
            return ok({"updated": True})
        finally:
            session.close()

    @router.delete("/api/images/{image_id}")
    async def delete_image(image_id: int):
        """删除图片（物理文件 + 数据库记录）。"""
        session = get_session()
        try:
            image = session.query(Image).filter(Image.id == image_id).first()
            if not image:
                raise HTTPException(status_code=404, detail="image not found")

            voice_actor_id = image.voice_actor_id
            file_path = image.file_path

            # 删除物理文件
            try:
                if file_path and os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"删除图片文件失败 {file_path}: {e}")

            # 删除数据库记录
            session.delete(image)

            # 更新声优 image_count（不允许为负）
            session.query(VoiceActor).filter(VoiceActor.id == voice_actor_id).update(
                {"image_count": func.greatest(0, VoiceActor.image_count - 1)}
            )
            session.commit()
            return ok({"deleted": True})
        finally:
            session.close()

    @router.get("/api/images/{image_id}/file")
    async def serve_image_file(image_id: int):
        """返回图片原始文件，用于前端缩略图预览。"""
        session = get_session()
        try:
            image = session.query(Image).filter(Image.id == image_id).first()
            if not image:
                raise HTTPException(status_code=404, detail="image not found")

            file_path = image.file_path
            if not file_path or not os.path.isfile(file_path):
                raise HTTPException(status_code=404, detail="image file not found on disk")

            # 根据扩展名推断 media_type
            ext = Path(file_path).suffix.lower()
            media_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".bmp": "image/bmp",
            }
            return FileResponse(file_path, media_type=media_map.get(ext, "image/jpeg"))
        finally:
            session.close()

    @router.get("/api/system-info")
    async def system_info():
        """返回 bot 进程的 CPU/内存占用和系统信息。"""
        import psutil

        proc = psutil.Process()
        cpu_percent = proc.cpu_percent(interval=0.1)
        mem = proc.memory_info()
        mem_total = psutil.virtual_memory().total
        cpu_model = ""
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            cpu_model = "Unknown"

        return ok(
            {
                "cpu_percent": round(cpu_percent, 1),
                "memory_mb": round(mem.rss / 1024 / 1024, 1),
                "memory_total_mb": round(mem_total / 1024 / 1024, 1),
                "cpu_model": cpu_model,
            }
        )

    app.include_router(router)

    # 挂载管理后台静态文件（CSS/JS 等）
    if STATIC_DIR.exists():
        app.mount("/admin/static", StaticFiles(directory=str(STATIC_DIR)), name="admin_static")

    app.state.admin_routes_registered = True
    logger.info("管理后台路由挂载完成: /admin")
