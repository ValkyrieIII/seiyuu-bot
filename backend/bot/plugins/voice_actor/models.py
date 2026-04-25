"""
声优插件 - 数据模型层（ORM）
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from loguru import logger
from bot.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.db_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    connect_args={
        "charset": "utf8mb4",
        "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
    },
)

# 创建会话工厂
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# 声明基类
Base = declarative_base()


class VoiceActor(Base):
    """声优模型"""

    __tablename__ = "voice_actors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    image_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    images = relationship(
        "Image", back_populates="voice_actor", cascade="all, delete-orphan"
    )
    aliases = relationship(
        "Alias", back_populates="voice_actor", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<VoiceActor {self.name}>"


class Image(Base):
    """图片模型"""

    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voice_actor_id = Column(
        Integer, ForeignKey("voice_actors.id", ondelete="CASCADE"), nullable=False
    )
    filename = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    size_kb = Column(Integer, default=0)
    file_hash = Column(String(64))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    voice_actor = relationship("VoiceActor", back_populates="images")

    __table_args__ = (
        Index("idx_voice_actor_id", "voice_actor_id"),
        Index("idx_is_active", "is_active"),
        Index("idx_file_hash", "file_hash"),
    )

    def __repr__(self):
        return f"<Image {self.filename}>"


class Alias(Base):
    """别名模型"""

    __tablename__ = "aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_name = Column(String(255), nullable=False)
    target_voice_actor_id = Column(
        Integer, ForeignKey("voice_actors.id", ondelete="CASCADE"), nullable=False
    )
    is_global = Column(Boolean, default=True)
    user_id = Column(Integer)
    description = Column(Text)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    voice_actor = relationship("VoiceActor", back_populates="aliases")

    __table_args__ = (
        Index("idx_alias_name", "alias_name"),
        Index("idx_voice_actor_id", "target_voice_actor_id"),
        Index("idx_user_id", "user_id"),
        Index("idx_is_global", "is_global"),
    )

    def __repr__(self):
        return f"<Alias {self.alias_name} -> {self.target_voice_actor_id}>"


class UserCooldown(Base):
    """用户冷却模型"""

    __tablename__ = "user_cooldowns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    command_type = Column(String(64), nullable=False)
    last_request_time = Column(BigInteger, nullable=False)  # 毫秒时间戳
    cooldown_duration = Column(Integer, default=1)
    request_count = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_last_request_time", "last_request_time"),
    )

    def __repr__(self):
        return f"<UserCooldown user={self.user_id} command={self.command_type}>"


class RequestLog(Base):
    """请求日志模型"""

    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    group_id = Column(Integer)
    command = Column(String(64), nullable=False)
    voice_actor_id = Column(Integer)
    image_id = Column(Integer)
    status = Column(String(32), default="success")
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_group_id", "group_id"),
        Index("idx_command", "command"),
        Index("idx_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<RequestLog user={self.user_id} status={self.status}>"


def get_session():
    """获取数据库会话"""
    return SessionLocal()


def init_db():
    """初始化数据库（创建所有表）和文件夹结构"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")

        # 初始化声优数据（如果表为空）
        session = get_session()
        try:
            voice_actors = session.query(VoiceActor).all()

            # 如果表为空，插入初始数据
            if not voice_actors:
                logger.info("检测到声优表为空，正在插入初始数据...")
                initial_voice_actors = [
                    VoiceActor(name="中岛由贵", description="日本女性声优"),
                    VoiceActor(name="佐藤利奈", description="日本女性声优"),
                    VoiceActor(name="花澤香菜", description="日本女性声优"),
                    VoiceActor(name="水树奈奈", description="日本女性声优"),
                    VoiceActor(name="大西沙織", description="日本女性声优"),
                ]
                for actor in initial_voice_actors:
                    session.add(actor)
                session.commit()
                logger.info(f"成功插入 {len(initial_voice_actors)} 位声优数据")

            # 注意：不再自动创建文件夹
            # 文件夹结构应该根据实际文件系统通过 scan_image_records() 来管理

        finally:
            session.close()

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        raise
