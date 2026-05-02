"""
@Bot 命令插件 - 业务逻辑层
"""

from datetime import date
from typing import Tuple, Optional
from loguru import logger
from sqlalchemy import func
from .models import CheckIn, get_session


class CheckInService:
    """签到业务服务"""

    @staticmethod
    def check_in(
        user_id: int,
        group_id: int = None,
        lucky_actor_id: int = None,
        lucky_image_id: int = None,
    ) -> Tuple[bool, int, Optional[int], Optional[int]]:
        """
        执行签到。返回 (is_new, total_days, lucky_actor_id, lucky_image_id)
        - is_new: True 为当日首次签到
        - total_days: 累计签到天数
        - lucky_actor_id / lucky_image_id: 幸运声优及图片（首次签到存储传入值，重复签到返回已存值）
        """
        session = get_session()
        try:
            today = date.today()

            existing = (
                session.query(CheckIn)
                .filter(
                    CheckIn.user_id == user_id,
                    CheckIn.check_in_date == today,
                )
                .first()
            )

            total = (
                session.query(func.count(CheckIn.id))
                .filter(CheckIn.user_id == user_id)
                .scalar()
            )

            if existing:
                return False, total, existing.lucky_actor_id, existing.lucky_image_id

            record = CheckIn(
                user_id=user_id,
                group_id=group_id,
                check_in_date=today,
                lucky_actor_id=lucky_actor_id,
                lucky_image_id=lucky_image_id,
            )
            session.add(record)
            session.commit()

            total_after = total + 1
            logger.info(
                f"签到成功 - user_id={user_id} total={total_after} "
                f"lucky_actor={lucky_actor_id} lucky_image={lucky_image_id}"
            )
            return True, total_after, lucky_actor_id, lucky_image_id

        except Exception as e:
            logger.error(f"签到失败: {e}", exc_info=True)
            session.rollback()
            return False, 0, None, None
        finally:
            session.close()

    @staticmethod
    def reset_table() -> int:
        """清空签到表，返回删除的记录数"""
        session = get_session()
        try:
            count = session.query(func.count(CheckIn.id)).scalar()
            session.query(CheckIn).delete()
            session.commit()
            logger.info(f"签到表已重置，删除 {count} 条记录")
            return count
        except Exception as e:
            logger.error(f"重置签到表失败: {e}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()
