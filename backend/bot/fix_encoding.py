#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复MySQL中double-encoded的中文数据"""

import sys
from sqlalchemy import text

sys.path.insert(0, "/app")
from bot.plugins.voice_actor.models import get_session


def fix_encoding():
    """修复数据库中的mojibake编码"""
    print("=" * 60)
    print("开始修复数据库编码问题")
    print("=" * 60)

    session = get_session()

    try:
        # 1. 查看当前数据
        print("\n【修复前的数据】")
        actors_before = session.execute(
            text("SELECT id, name, HEX(name) as hex FROM voice_actors")
        ).fetchall()
        for actor_id, name, hex_val in actors_before:
            print(f"ID {actor_id}: {name} (HEX: {hex_val})")

        # 2. 修复double-encoded的UTF-8数据
        # 当UTF-8字节被误读为latin-1时，每个UTF-8字节都变成了单个字符
        # 我们需要获取这些字符的Latin-1编码，然后解码为UTF-8
        print("\n【尝试修复】")

        for actor_id, name_mojibake, _ in actors_before:
            # 将mojibake字符串的每个字符转换回UTF-8字节
            try:
                # mojibake 是通过 UTF-8字节被latin-1读取得到的
                # 反向过程：取mojibake的UTF-8编码，作为原始字节
                utf8_bytes = name_mojibake.encode("utf-8")

                # 但这不对，因为mojibake本身已经是Unicode字符了
                # 正确的方法是：mojibake是由UTF-8字节组成的，每个字节被作为单个拉丁1字符
                # 所以我们需要将mojibake的拉丁1"编码"提取出来

                # 实际上，当UTF-8字节被误读为latin-1时：
                # 原始字符"中"(E4 B8 AD)被mysql作为3个拉丁1字符存储
                # 在Python中读取时，这3个字符会被还原为E4 B8 AD的字节
                # 然后再被解码为对应的unicode字符

                # 为了恢复，我们需要：
                # 1. 获取mojibake的UTF-8字节 (这会失败，因为mojibake中可能包含不能编码的字符)
                # 2. 或者尝试用latin-1编码mojibake（这样会得到原始的UTF-8字节）

                raw_bytes = name_mojibake.encode("latin-1")
                fixed_name = raw_bytes.decode("utf-8")

                print(f"ID {actor_id}: {name_mojibake} -> {fixed_name}")

                # 3. 更新数据库
                session.execute(
                    text("UPDATE voice_actors SET name = :name WHERE id = :id"),
                    {"name": fixed_name, "id": actor_id},
                )

            except Exception as e:
                print(f"ID {actor_id} 修复失败: {e}")

        # 提交更改
        session.commit()

        # 4. 验证修复结果
        print("\n【修复后的数据】")
        actors_after = session.execute(
            text("SELECT id, name, HEX(name) as hex FROM voice_actors")
        ).fetchall()
        for actor_id, name, hex_val in actors_after:
            print(f"ID {actor_id}: {name} (HEX: {hex_val})")

        print("\n✅ 修复完成！")

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        session.rollback()
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    fix_encoding()
