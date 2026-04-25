#!/usr/bin/env python3
"""
别名管理脚本
用法:
  python manage_aliases.py add <alias> <voice_actor> [--priority=0]
  python manage_aliases.py remove <alias>
  python manage_aliases.py list
  python manage_aliases.py import <csv_file>
"""
import os
import sys
import argparse
import csv
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

# 导入数据库模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "bot"))
from plugins.voice_actor.models import get_session, VoiceActor, Alias


def add_alias(alias_name: str, voice_actor_name: str, priority: int = 0):
    """添加别名"""
    session = get_session()
    try:
        # 查找声优
        voice_actor = (
            session.query(VoiceActor)
            .filter(VoiceActor.name == voice_actor_name)
            .first()
        )

        if not voice_actor:
            logger.error(f"声优不存在: {voice_actor_name}")
            return False

        # 检查别名是否已存在
        existing = session.query(Alias).filter(Alias.alias_name == alias_name).first()

        if existing:
            logger.warning(f"别名已存在: {alias_name}")
            return False

        # 创建别名
        alias = Alias(
            alias_name=alias_name,
            target_voice_actor_id=voice_actor.id,
            is_global=True,
            priority=priority,
            is_active=True,
        )
        session.add(alias)
        session.commit()
        logger.info(
            f"✓ 添加别名成功: [{alias_name}] -> [{voice_actor_name}] (优先级: {priority})"
        )
        return True
    except Exception as e:
        logger.error(f"添加别名失败: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def remove_alias(alias_name: str):
    """删除别名"""
    session = get_session()
    try:
        alias = session.query(Alias).filter(Alias.alias_name == alias_name).first()

        if not alias:
            logger.error(f"别名不存在: {alias_name}")
            return False

        session.delete(alias)
        session.commit()
        logger.info(f"✓ 删除别名成功: {alias_name}")
        return True
    except Exception as e:
        logger.error(f"删除别名失败: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def list_aliases():
    """列出所有别名"""
    session = get_session()
    try:
        aliases = (
            session.query(Alias)
            .filter(Alias.is_active == True, Alias.is_global == True)
            .order_by(Alias.priority.desc())
            .all()
        )

        if not aliases:
            logger.info("暂无别名")
            return

        logger.info(f"共 {len(aliases)} 个别名:")
        logger.info("-" * 60)
        for alias in aliases:
            actor = (
                session.query(VoiceActor)
                .filter(VoiceActor.id == alias.target_voice_actor_id)
                .first()
            )
            actor_name = actor.name if actor else "未知"
            logger.info(
                f"  [{alias.alias_name}] -> [{actor_name}] (优先级: {alias.priority})"
            )
        logger.info("-" * 60)
    finally:
        session.close()


def import_aliases_from_csv(csv_file: str):
    """从CSV文件导入别名"""
    if not os.path.exists(csv_file):
        logger.error(f"文件不存在: {csv_file}")
        return False

    success_count = 0
    error_count = 0

    try:
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                alias_name = row.get("alias", "").strip()
                voice_actor_name = row.get("voice_actor", "").strip()
                priority = int(row.get("priority", "0"))

                if not alias_name or not voice_actor_name:
                    logger.warning(f"跳过无效行: {row}")
                    error_count += 1
                    continue

                if add_alias(alias_name, voice_actor_name, priority):
                    success_count += 1
                else:
                    error_count += 1
    except Exception as e:
        logger.error(f"导入CSV失败: {e}", exc_info=True)
        return False

    logger.info(f"导入完成: 成功 {success_count}, 失败 {error_count}")
    return error_count == 0


def main():
    parser = argparse.ArgumentParser(description="QQ机器人别名管理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加别名")
    add_parser.add_argument("alias", help="别名")
    add_parser.add_argument("voice_actor", help="声优名称")
    add_parser.add_argument("--priority", type=int, default=0, help="优先级")

    # remove 命令
    remove_parser = subparsers.add_parser("remove", help="删除别名")
    remove_parser.add_argument("alias", help="别名")

    # list 命令
    subparsers.add_parser("list", help="列出所有别名")

    # import 命令
    import_parser = subparsers.add_parser("import", help="从CSV文件导入别名")
    import_parser.add_argument("csv_file", help="CSV文件路径")

    args = parser.parse_args()

    if args.command == "add":
        add_alias(args.alias, args.voice_actor, args.priority)
    elif args.command == "remove":
        remove_alias(args.alias)
    elif args.command == "list":
        list_aliases()
    elif args.command == "import":
        import_aliases_from_csv(args.csv_file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
