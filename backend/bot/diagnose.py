#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UTF-8 编码诊断脚本"""

import sys
import os
from sqlalchemy import text

print("=" * 60)
print("UTF-8 编码诊断报告")
print("=" * 60)

# 1. 系统编码
print("\n【系统和Python编码】")
print(f"sys.stdout.encoding: {sys.stdout.encoding}")
print(f"sys.stdin.encoding: {sys.stdin.encoding}")
print(f"sys.getdefaultencoding(): {sys.getdefaultencoding()}")

print("\n【环境变量】")
print(f"LANG: {os.environ.get('LANG', '未设置')}")
print(f"LC_ALL: {os.environ.get('LC_ALL', '未设置')}")
print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', '未设置')}")

# 2. SQLAlchemy连接和数据库检查
print("\n【数据库字符集配置】")
sys.path.insert(0, "/app")

try:
    from bot.plugins.voice_actor.models import get_session, VoiceActor

    session = get_session()

    # 检查MySQL服务器字符集
    server_charset = session.execute(text("SELECT @@character_set_server")).scalar()
    server_collation = session.execute(text("SELECT @@collation_server")).scalar()
    conn_charset = session.execute(text("SELECT @@character_set_connection")).scalar()
    db_charset = session.execute(text("SELECT @@character_set_database")).scalar()
    client_charset = session.execute(text("SELECT @@character_set_client")).scalar()
    results_charset = session.execute(text("SELECT @@character_set_results")).scalar()

    print(f"character_set_server: {server_charset}")
    print(f"collation_server: {server_collation}")
    print(f"character_set_connection: {conn_charset}")
    print(f"character_set_database: {db_charset}")
    print(f"character_set_client: {client_charset}")
    print(f"character_set_results: {results_charset}")

    # 查询数据并检查编码
    print("\n【从数据库读取的数据】")
    actor = session.query(VoiceActor).first()

    if actor:
        print(f"actor.name 值: {actor.name}")
        print(f"actor.name repr: {repr(actor.name)}")
        print(f"actor.name 类型: {type(actor.name).__name__}")

        # 检查是否是mojibake
        print("\n【编码检查】")
        utf8_bytes = actor.name.encode("utf-8")
        print(f"UTF-8 bytes: {utf8_bytes}")

        # 尝试恢复
        try:
            recovered = actor.name.encode("latin-1").decode("utf-8")
            print(f"从 latin-1 恢复: {recovered}")
            if "中" in recovered:
                print("✓ 确认问题: 数据在MySQL中被latin-1误读")
        except Exception as e:
            print(f"恢复失败: {e}")

    session.close()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback

    traceback.print_exc()
