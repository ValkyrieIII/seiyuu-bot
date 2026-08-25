"""
@Bot 命令插件 - 数据模型层（ORM）
"""

from datetime import datetime, date
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    Date,
    TIMESTAMP,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger
from bot.config import settings

engine = create_engine(
    settings.db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    connect_args={
        "charset": "utf8mb4",
        "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
    },
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()


class CheckIn(Base):
    """签到记录模型"""

    __tablename__ = "check_ins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    group_id = Column(BigInteger, nullable=True)
    check_in_date = Column(Date, nullable=False, default=date.today)
    lucky_actor_id = Column(Integer, nullable=True)
    lucky_image_id = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_date", "user_id", "check_in_date", unique=True),
        Index("idx_check_in_date", "check_in_date"),
    )

    def __repr__(self):
        return f"<CheckIn user={self.user_id} date={self.check_in_date}>"


def get_session():
    """获取数据库会话"""
    return SessionLocal()


def init_db():
    """初始化数据库（创建签到表）"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("签到表初始化完成")
    except Exception as e:
        logger.error(f"签到表初始化失败: {e}", exc_info=True)
        raise
