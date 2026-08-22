#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理并重新初始化数据库"""

import sys

sys.path.insert(0, "/app")

from sqlalchemy import text
from bot.config import settings
from bot.plugins.voice_actor.models import engine, Base, VoiceActor


def reinit_database():
    """完全重新初始化数据库"""
    print("=" * 60)
    print("数据库重新初始化")
    print("=" * 60)

    try:
        # 1. 删除所有表
        print("\n【步骤1】 删除现有表...")
        Base.metadata.drop_all(engine)
        print("✓ 表已删除")

        # 2. 创建新表
        print("\n【步骤2】 创建新表...")
        Base.metadata.create_all(engine)
        print("✓ 表已创建")

        # 3. 插入正确编码的数据
        print("\n【步骤3】 插入正确编码的声优数据...")
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # 声优数据 - 确保这些字符在源代码中是正确的UTF-8编码
        voice_actors_data = [
            {"name": "中岛由贵", "description": "日本女性声优"},
            {"name": "佐藤利奈", "description": "日本女性声优"},
            {"name": "花澤香菜", "description": "日本女性声优"},
            {"name": "水树奈奈", "description": "日本女性声优"},
            {"name": "大西沙織", "description": "日本女性声优"},
        ]

        for actor_data in voice_actors_data:
            actor = VoiceActor(
                name=actor_data["name"], description=actor_data["description"]
            )
            session.add(actor)
            print(f"✓ 添加: {actor_data['name']}")

        session.commit()
        session.close()

        print("\n✅ 数据库初始化成功！")

        # 4. 验证数据
        print("\n【步骤4】 验证数据...")
        session = SessionLocal()
        actors = session.query(VoiceActor).all()
        for actor in actors:
            print(f"  - ID {actor.id}: {actor.name}")
        session.close()

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reinit_database()
