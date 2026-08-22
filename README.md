# QQ 声优机器人

基于 NoneBot2 + OneBot v11 + NapCat + MySQL 的群聊声优图片机器人。

- 群消息直接匹配声优名/别名并返回随机图片
- 支持 @机器人 命令：签到、声优列表
- 提供管理后台（/admin）进行声优、别名和图片同步管理
- 支持图片目录变更自动监听与数据库增量同步

## 技术栈

- Python 3.9+
- NoneBot2 + nonebot-adapter-onebot
- FastAPI（NoneBot 驱动层）
- SQLAlchemy + PyMySQL
- MySQL 8.0
- NapCat（OneBot 协议服务）
- Vue3 + TypeScript + Vite + Element Plus（管理后台前端）
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
├── frontend/                       # 管理后台前端（Vue3 + TypeScript + Element Plus）
│   ├── src/
│   │   ├── api/                    # 接口封装（axios，/admin/api/*）
│   │   ├── layouts/                # 管理后台布局
│   │   ├── router/                 # 路由（五个模块）
│   │   └── views/                  # 概览/声优/图片/别名/同步五个页面
│   ├── mock/                       # 开发期 mock 数据（无后端联调用）
│   ├── vite.config.ts              # 含 /admin 开发代理配置
│   └── package.json
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

## 环境与快速开始

项目使用基础 Compose 文件叠加环境覆盖文件，提供彼此隔离的 Dev / Test / Prod 三套环境：

- Dev：源码挂载与热重载，可选启用 NapCat。
- Test：独立 MySQL 数据卷和测试夹具，默认完全不启动 NapCat。
- Prod：只读应用文件系统、日志轮转，MySQL 与 NoneBot 不直接暴露宿主机端口。

本地开发：

```powershell
Copy-Item .env.dev.example .env.dev
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

自动化测试：

```powershell
Copy-Item .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test test
```

生产部署前复制 `.env.prod.example` 为 `.env.prod`，填写全部留空密钥并固定 NapCat 镜像版本。所有命令、端口和迁移说明见 [Dev / Test / Prod 环境文档](docs/ENVIRONMENTS.md)。

## 使用说明

### 群消息触发

- 在群里发送“声优名称”或“别名”，机器人会返回随机图片
- 冷却机制默认开启（按用户维度）

### @机器人命令

- `@机器人 签到`：每日签到，随机抽取一位幸运女声优并附上图片；当天重复签到时返回相同的幸运声优
- `@机器人 声优列表`：返回当前可用声优与图片数量

### 管理后台

管理后台前端位于 `frontend/`（Vue3 + TypeScript + Element Plus），本地开发：

```bash
cd frontend
pnpm install
pnpm dev
```

开发环境默认连接真实后端；将 `.env.dev` 中的 `VITE_USE_MOCK` 改为 `true` 可切换到 mock 数据。开发代理会把 `/admin` 请求转发到 NoneBot。

生产环境访问 /admin 可进行：

- 概览查看（请求量、成功率、最近日志）
- 声优管理（新增/更新启用状态）
- 图片管理（查询/上传/删除）
- 别名管理（新增/删除）
- 图片同步（触发扫描并更新数据库）

### 前端部署

生产镜像会执行 `pnpm build`，由 Nginx 托管静态文件，并将 `/admin`、`/health` 与可选的 OneBot WebSocket 转发到 NoneBot。

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


<!-- ## 开发说明

当前项目以容器化运行路径为主。若进行本地开发，建议仍通过 Docker Compose 启动 MySQL 与 NapCat，再将代码目录挂载到 nonebot 容器中调试，避免本地路径与运行路径不一致带来的问题。

## 文档导航

- API 设计与扩展开发：docs/API.md
- 数据库设计：docs/DATABASE.md -->

<!-- ## 许可证

当前仓库未声明开源许可证。如需开源，请补充 LICENSE 文件并在此处声明。 -->
