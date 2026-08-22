#!/usr/bin/env python3
"""
本地快速验证脚本
用于检查项目是否完整配置
"""
import os
import sys
from pathlib import Path


def check_file_exists(path, description=""):
    """检查文件是否存在"""
    exists = os.path.exists(path)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {path}")
    return exists


def check_directory_exists(path, description=""):
    """检查目录是否存在"""
    exists = os.path.isdir(path)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {path}")
    return exists


def main():
    print("=" * 60)
    print("QQ声优机器人 - 项目完整性检查")
    print("=" * 60)

    base_path = os.path.dirname(os.path.abspath(__file__))
    checks_passed = 0
    checks_total = 0

    # 1. 检查根目录文件
    print("\n📁 根目录文件检查:")
    checks = [
        ("docker-compose.yml", "Docker编排文件"),
        (".env", "环境变量文件"),
        ("Dockerfile", "NoneBot容器镜像"),
        ("requirements.txt", "Python依赖"),
        ("README.md", "项目说明"),
        ("QUICKSTART.md", "快速启动指南"),
        ("CHECKLIST.md", "部署检查清单"),
        (".gitignore", "Git忽略文件"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 2. 检查数据库文件
    print("\n📊 数据库初始化脚本检查:")
    checks = [
        ("database/init.sql", "数据库表定义"),
        ("database/seed.sql", "种子数据"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 3. 检查 NoneBot 应用结构
    print("\n🤖 NoneBot应用结构检查:")
    checks = [
        ("backend/bot/main.py", "启动入口"),
        ("backend/bot/config.py", "配置管理"),
        ("backend/bot/__init__.py", "应用包"),
        ("backend/bot/plugins/__init__.py", "插件包"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 4. 检查声优插件
    print("\n🎤 声优插件检查:")
    checks = [
        ("backend/bot/plugins/voice_actor/__init__.py", "插件入口"),
        ("backend/bot/plugins/voice_actor/models.py", "数据模型"),
        ("backend/bot/plugins/voice_actor/services.py", "业务逻辑"),
        ("backend/bot/plugins/voice_actor/handlers.py", "事件处理"),
        ("backend/bot/plugins/voice_actor/utils.py", "工具函数"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 5. 检查脚本工具
    print("\n🛠️  工具脚本检查:")
    checks = [
        ("scripts/import_images.py", "批量导入脚本"),
        ("scripts/manage_aliases.py", "别名管理脚本"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 6. 检查配置文件
    print("\n⚙️  配置文件检查:")
    checks = [
        ("config/bot_config.yml", "NoneBot配置"),
        ("config/aliases_example.csv", "别名示例"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 7. 检查文档
    print("\n📚 文档检查:")
    checks = [
        ("docs/DATABASE.md", "数据库设计文档"),
        ("docs/SETUP.md", "本地开发指南"),
        ("docs/DEPLOY.md", "云部署指南"),
    ]
    for file, desc in checks:
        checks_total += 1
        if check_file_exists(os.path.join(base_path, file), desc):
            checks_passed += 1

    # 8. 检查目录
    print("\n📂 目录结构检查:")
    dirs = [
        ("images", "图片存储目录"),
        ("logs", "日志目录"),
        ("database", "数据库目录"),
        ("config", "配置目录"),
        ("scripts", "脚本目录"),
        ("docs", "文档目录"),
        ("backend", "后端代码目录"),
    ]
    for dir, desc in dirs:
        checks_total += 1
        if check_directory_exists(os.path.join(base_path, dir), desc):
            checks_passed += 1

    # 9. 统计和建议
    print("\n" + "=" * 60)
    print(f"检查完成: {checks_passed}/{checks_total} 项通过")
    print("=" * 60)

    if checks_passed == checks_total:
        print("✅ 项目结构完整！可以开始部署")
        print("\n📝 后续步骤:")
        print("  1. 编辑 .env 文件配置必要参数")
        print("  2. 准备测试图片（放入 images/ 目录）")
        print("  3. 运行: docker-compose up -d")
        print("  4. 等待服务启动完成")
        print(
            "  5. 导入图片: docker exec qqbot-nonebot python /app/scripts/import_images.py /app/images"
        )
        print("  6. 查看日志: docker-compose logs -f nonebot")
        return 0
    else:
        missing = checks_total - checks_passed
        print(f"❌ 有 {missing} 项检查未通过，请检查上面的标记（✗）")
        print("\n💡 常见问题:")
        print("  - 确保项目目录完整")
        print("  - 检查文件是否在正确的位置")
        print("  - 查看是否有文件没有保存")
        return 1


if __name__ == "__main__":
    sys.exit(main())
