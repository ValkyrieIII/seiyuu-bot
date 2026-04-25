# QQ 声优机器人

基于 NoneBot2 + OneBot v11 + NapCat + MySQL 的群聊声优图片机器人。

- 群消息直接匹配声优名/别名并返回随机图片
- 支持 @机器人 命令：声优列表
- 提供管理后台（/admin）进行声优、别名和图片同步管理
- 支持图片目录变更自动监听与数据库增量同步

## 技术栈

- Python 3.9+
- NoneBot2 + nonebot-adapter-onebot
- FastAPI（NoneBot 驱动层）
- SQLAlchemy + PyMySQL
- MySQL 8.0
- NapCat（OneBot 协议服务）
- Docker / Docker Compose

## 项目结构

```text
.
├── backend/
│   └── bot/
│       ├── main.py                 # 应用入口
│       ├── config.py               # 配置读取（环境变量）
│       ├── manage.py               # 管理命令（同步图片/目录等）
│       ├── admin/                  # 管理后台与路由
│       ├── monitor/                # 文件监听（watchdog）
│       └── plugins/
│           ├── mention_command/    # @机器人命令
│           └── voice_actor/        # 声优核心逻辑（模型/服务/处理器）
├── database/
│   ├── init.sql                    # 建表脚本
│   └── seed.sql                    # 初始数据
├── docs/
│   ├── API.md
│   └── DATABASE.md
├── images/                         # 声优图片目录（按声优名分文件夹）
├── logs/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 快速开始（Docker Compose，推荐）

### 1) 前置准备

- 已安装 Docker 与 Docker Compose
- 服务器或本机可访问端口：8080（NoneBot）、6099（NapCat WebUI）、3307（MySQL 映射）
- 具备可用 QQ 账号用于 NapCat 登录

### 2) 配置环境变量

在项目根目录创建.env 文件，按实际环境修改关键项：

- SERVER_IP：NapCat 回连 NoneBot 的主机地址（非常关键）
- ONEBOT_ACCESS_TOKEN：OneBot 访问令牌（需与 NapCat 侧保持一致）
- DB_ROOT_PASSWORD / DB_NAME / DB_USER / DB_PASSWORD：数据库配置
- BOT_QQ：机器人 QQ 号
- GROUP_ID：可选，限制群使用

建议在生产环境至少修改：

- ONEBOT_ACCESS_TOKEN
- DB_ROOT_PASSWORD
- DB_PASSWORD

### 3) 启动服务

```bash
docker compose up -d --build
```

### 4) 检查状态

```bash
docker compose ps
docker compose logs -f nonebot
```

看到 NoneBot 正常启动且无持续报错后，可访问管理后台：

- http://localhost:8080/admin

如部署在远程服务器，请将 localhost 替换为服务器地址。
如果服务器没有放通8080端口，可使用本地ssh连接。

## 使用说明

### 群消息触发

- 在群里发送“声优名称”或“别名”，机器人会返回随机图片
- 冷却机制默认开启（按用户维度）

### @机器人命令

- @机器人 后发送：声优列表
- 返回当前可用声优与图片数量

### 管理后台

访问 /admin 可进行：

- 概览查看（请求量、成功率、最近日志）
- 声优管理（新增/更新启用状态）
- 别名管理（新增/删除）
- 图片同步（触发扫描并更新数据库）

<!-- ## 运维与管理命令

以下命令在 nonebot 容器内执行：

```bash
# 查看可用命令
docker compose exec nonebot python /app/bot/manage.py help

# 扫描图片目录并同步数据库（推荐）
docker compose exec nonebot python /app/bot/manage.py sync-database

# 初始化图片命名并重建图片记录
docker compose exec nonebot python /app/bot/manage.py init-images-db

# 列出声优目录状态
docker compose exec nonebot python /app/bot/manage.py list-folders

# 重新创建声优文件夹
docker compose exec nonebot python /app/bot/manage.py reinit-folders
```

别名批量/手工管理脚本（在仓库根目录运行）：

```bash
python3 scripts/manage_aliases.py list
python3 scripts/manage_aliases.py add 贵贵 中岛由贵 --priority 10
python3 scripts/manage_aliases.py remove 贵贵
``` -->

## 图片目录约定

- 每位声优一个同名目录，位于 images 下
- 支持在运行时增删图片
- 插件启动时会执行一次扫描
- 文件系统监听器会在目录变更后自动触发增量同步

## 常见问题

### 1) 机器人不回图

优先检查：

- 目标声优目录是否存在有效图片
- 别名是否正确映射到声优
- 图片是否已执行同步（sync-database）
- nonebot 日志是否有 file_missing/no_image 错误

### 2) NapCat 连不上 NoneBot

重点检查：

- napcat webui中的网络配置
- ONEBOT_ACCESS_TOKEN 两侧是否一致

### 3) 管理后台打不开

重点检查：

- nonebot 容器是否健康运行
- 8080 端口映射是否被占用
- 访问地址是否正确（/admin）

<!-- ## 开发说明

当前项目以容器化运行路径为主。若进行本地开发，建议仍通过 Docker Compose 启动 MySQL 与 NapCat，再将代码目录挂载到 nonebot 容器中调试，避免本地路径与运行路径不一致带来的问题。

## 文档导航

- API 设计与扩展开发：docs/API.md
- 数据库设计：docs/DATABASE.md -->

<!-- ## 许可证

当前仓库未声明开源许可证。如需开源，请补充 LICENSE 文件并在此处声明。 -->
