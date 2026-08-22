# 本地开发环境搭建指南（Windows）

> 当前 Dev / Test / Prod 的权威启动方式见 [`ENVIRONMENTS.md`](ENVIRONMENTS.md)。本文保留功能配置细节；其中旧版单环境 Compose 示例不再作为启动依据。

本指南将帮助您在 Windows 开发环境中完整部署和测试 QQ 声优机器人。

## 前置要求

### 系统环境

- Windows 10 / 11
- Docker Desktop for Windows（[下载链接](https://www.docker.com/products/docker-desktop)）
- WSL 2 后端（Docker Desktop 会自动配置）

### 软件工具

- Git（可选，用于版本控制）
- Python 3.11+（仅用于本地脚本开发）

### 硬件要求

- 内存：≥ 4GB（推荐 8GB）
- 磁盘：≥ 10GB（主要用于图片存储）
- CPU：双核及以上

## 安装步骤

### 1. 安装 Docker Desktop

1. 下载 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. 运行安装程序，选择"WSL 2"作为后端
3. 完成安装并重启计算机
4. 验证安装：

```bash
docker --version
docker-compose --version
```

### 2. 克隆项目

```bash
# 进入工作目录
cd c:\Users\i\Desktop

# 克隆项目（如果使用Git）
# git clone <repository_url> qqbot

# 或进入已有的 qqbot 目录
cd qqbot
```

### 3. 配置环境变量

复制并编辑 `.env` 文件：

```bash
# 使用 Git Bash 或 PowerShell
cp .env .env.local

# 用编辑器打开并修改
# 主要需要修改的字段：
# BOT_QQ - 机器人的QQ号
# GROUP_ID - 要监听的群号（可选）
# DB_PASSWORD - 数据库密码（保安全）
```

**重要配置说明**：

| 参数                | 说明           | 示例                    |
| ------------------- | -------------- | ----------------------- |
| `DB_HOST`           | 数据库主机     | mysql（Docker内部使用） |
| `DB_NAME`           | 数据库名称     | qqbot                   |
| `DB_USER`           | 数据库用户     | qqbot                   |
| `DB_PASSWORD`       | 数据库密码     | qqbot123                |
| `BOT_QQ`            | 机器人QQ号     | 123456789               |
| `NAPCAT_HOST`       | NapCat 地址    | napcat（Docker内）      |
| `COOLDOWN_DURATION` | 冷却时间（秒） | 1                       |
| `LOG_LEVEL`         | 日志级别       | INFO/DEBUG              |

### 4. 启动 Docker 容器

在项目根目录运行：

```bash
# 启动所有服务（MySQL、NoneBot）
docker-compose up -d

# 验证容器状态
docker-compose ps

# 预期输出：
# NAME              STATUS
# qqbot-mysql       Up ...
# qqbot-nonebot     Up ...
```

### 5. 验证服务连接

检查 MySQL 是否正常运行：

```bash
# 查看 MySQL 日志
docker-compose logs mysql

# 连接到 MySQL 容器测试
docker exec qqbot-mysql mysql -u qqbot -pqqbot123 -e "SELECT 1;"

# 预期输出应包含 "1" 行
```

检查 NoneBot 是否启动成功：

```bash
# 查看 NoneBot 日志
docker-compose logs -f nonebot

# 应该看到类似的输出：
# INFO: 声优插件已加载
# INFO: 所有插件加载完成
```

### 6. 准备测试图片

在 `images/` 目录下创建声优文件夹并放入图片：

```bash
# 创建测试数据目录
mkdir -p images/测试声优1
mkdir -p images/测试声优2

# 从其他位置复制图片到这些文件夹
# 每个文件夹内放至少 3-5 张 .jpg 或 .png 文件
```

**图片要求**：
- 格式：JPG、PNG、GIF、WebP 等常见格式
- 大小：100KB 到 50MB
- 命名：任意（导入脚本会自动重命名）

### 7. 导入图片到数据库

在本地临时创建源图片目录或使用现有目录，然后运行导入脚本：

```bash
# 方式1：通过 Docker 容器运行
# （假设本地图片在 images/ 目录）
docker exec qqbot-nonebot python /app/scripts/import_images.py /app/images

# 方式2：直接通过 Python（本地需要安装依赖）
python scripts/import_images.py ./images

# 预期输出：
# 找到声优 [测试声优1]: 5 张图片
# 找到声优 [测试声优2]: 3 张图片
# 导入完成: ✓10 ⊘0 ✗0
```

### 8. 配置别名

添加一些别名以便测试：

```bash
# 通过 Docker 容器运行
docker exec qqbot-nonebot python /app/scripts/manage_aliases.py add "别名1" "测试声优1" --priority=10
docker exec qqbot-nonebot python /app/scripts/manage_aliases.py add "别名2" "测试声优2" --priority=5

# 列出所有别名
docker exec qqbot-nonebot python /app/scripts/manage_aliases.py list

# 预期输出：
# 共 2 个别名:
# [别名1] -> [测试声优1] (优先级: 10)
# [别名2] -> [测试声优2] (优先级: 5)
```

### 9. 配置 NapCat 连接

机器人需要连接到 QQ 协议层（NapCat）。有两种方式：

#### 方式A：使用本地 NapCat（推荐用于开发）

在 `docker-compose.yml` 中启用 NapCat 服务：

```yaml
  napcat:
    image: napcat/napcat:latest
    container_name: qqbot-napcat
    environment:
      NAPCAT_ADMIN_ENDPOINT: "http://0.0.0.0:3000"
      NAPCAT_WS_ENDPOINT: "ws://0.0.0.0:3001"
    ports:
      - "3000:3000"
      - "3001:3001"
    volumes:
      - napcat_data:/opt/napcat/data
    networks:
      - qqbot_network
    restart: unless-stopped

volumes:
  napcat_data:
    driver: local
```

然后重启服务：

```bash
docker-compose up -d napcat
```

#### 方式B：使用外部 QQ 客户端（推荐用于测试）

如果您有一个运行 NapCat 的本地 QQ 客户端，修改 `.env`：

```env
NAPCAT_HOST=host.docker.internal  # Docker 内部访问宿主机的特殊地址
NAPCAT_PORT=3001
```

### 10. 测试机器人（模拟消息）

由于完整的 QQ 群测试需要真实的机器人账号，这里提供几种测试方法：

#### 方法1：查看日志确认组件就绪

```bash
docker-compose logs -f nonebot | grep -E "插件|监听"

# 预期看到：
# INFO: 声优插件已加载
# INFO: 所有插件加载完成
```

#### 方法2：直接测试数据库查询

```bash
# 进入 MySQL 容器
docker exec -it qqbot-mysql mysql -u qqbot -pqqbot123 qqbot

# 执行查询
SELECT * FROM voice_actors;
SELECT * FROM images LIMIT 5;
SELECT * FROM aliases;
```

#### 方法3：通过 Python 测试业务逻辑

```bash
# 创建测试脚本 test_services.py
# 在项目根目录新建这个文件
```

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'bot'))

from plugins.voice_actor.services import (
    VoiceActorService, ImageService, AliasService, CooldownService
)

# 测试查询声优
actors = VoiceActorService.get_all_voice_actors()
print(f"声优列表: {[a.name for a in actors]}")

# 测试别名解析
if actors:
    actor = AliasService.resolve_alias(actors[0].name)
    print(f"别名解析成功: {actors[0].name} -> {actor.name if actor else 'None'}")

# 测试获取随机图片
if actors:
    image = ImageService.get_random_image(actors[0].id)
    print(f"随机图片: {image.filename if image else 'None'}")

# 测试冷却机制
user_id = 12345
is_cooldown, remaining = CooldownService.check_cooldown(user_id)
print(f"冷却状态: 冷却={is_cooldown}, 剩余={remaining}秒")

# 更新冷却
CooldownService.update_cooldown(user_id)
is_cooldown, remaining = CooldownService.check_cooldown(user_id)
print(f"更新后冷却: 冷却={is_cooldown}, 剩余={remaining}秒")
```

运行测试：

```bash
python test_services.py
```

### 11. 常见问题排查

#### 问题：Docker 容器无法启动

```bash
# 查看详细错误日志
docker-compose logs mysql
docker-compose logs nonebot

# 重启容器
docker-compose restart mysql
```

#### 问题：数据库连接超时

```bash
# 验证数据库是否就绪
docker-compose exec mysql mysql -u root -proot123 -e "SELECT 1;"

# 查看数据库日志
docker-compose logs mysql | tail -50
```

#### 问题：NoneBot 无法加载插件

```bash
# 检查日志
docker-compose logs nonebot | grep -i error

# 检查插件文件
docker exec qqbot-nonebot ls -la /app/bot/plugins/voice_actor/
```

#### 问题：导入图片失败

```bash
# 验证图片格式
file images/*/

# 检查权限
docker exec qqbot-nonebot ls -la /app/images/

# 查看导入日志
docker-compose logs nonebot | grep import
```

## 开发工作流

### 修改代码

修改 `backend/bot/` 下的代码后，需要重新启动 NoneBot 容器：

```bash
# 停止容器
docker-compose stop nonebot

# 启动容器（会重新构建镜像）
docker-compose up -d nonebot

# 查看日志确认重新加载
docker-compose logs -f nonebot
```

### 调试模式

将 `LOG_LEVEL` 改为 `DEBUG` 获取更详细的日志：

```bash
# 编辑 .env 或 .env.local
LOG_LEVEL=DEBUG

# 重启 NoneBot
docker-compose restart nonebot

# 查看日志
docker-compose logs -f nonebot
```

## 清理和重置

### 保留数据的重启

```bash
# 关闭容器（保留数据卷）
docker-compose down

# 重新启动
docker-compose up -d
```

### 完全重置（删除所有数据）

```bash
# 关闭容器并删除卷
docker-compose down -v

# 重新启动（会重新初始化数据库）
docker-compose up -d

# 重新导入数据
docker exec qqbot-nonebot python /app/scripts/import_images.py /app/images
```

### 删除镜像重新构建

```bash
# 删除旧镜像
docker rmi qqbot-nonebot

# 重新构建
docker-compose build --no-cache

# 启动
docker-compose up -d
```

## 性能监控

### 查看资源使用情况

```bash
# 实时监控
docker stats

# 查看容器详情
docker inspect qqbot-mysql
```

### 数据库性能分析

```bash
# 登录数据库
docker exec -it qqbot-mysql mysql -u qqbot -pqqbot123 qqbot

# 查看表大小
SELECT 
  TABLE_NAME,
  ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES 
WHERE table_schema = 'qqbot';

# 查看慢查询
SHOW VARIABLES LIKE 'slow_query%';
SET GLOBAL slow_query_log = 'ON';
```

## 下一步

- 使用真实 QQ 账号和 NapCat 进行完整测试
- 部署到 Ubuntu 云服务器（参考 [DEPLOY.md](DEPLOY.md)）
- 添加更多功能和优化性能

## 支持

如有问题，请查看：
- [README.md](../README.md) - 项目概览
- [DATABASE.md](DATABASE.md) - 数据库设计
- [DEPLOY.md](DEPLOY.md) - 云服务器部署
