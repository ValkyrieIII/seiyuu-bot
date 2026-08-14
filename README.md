# 声优图片系统（QQ 群接入 + Web 管理后台）

真实生产运行的双端系统：同一套后端同时支撑 **QQ 群机器人接入** 与 **Web 管理后台**。

- QQ 群接入：基于 NoneBot2 + OneBot v11 + NapCat，群内发送声优名/别名即可匹配并返回随机图片，支持 @机器人 签到、声优列表
- Web 管理后台：管理声优、别名、图片与同步，含概览、声优管理、图片管理、别名管理、图片同步五个模块
- 支持图片目录变更自动监听与数据库增量同步

## 功能列表

**QQ 群接入**

- 群消息图片匹配：群内直接发送声优名/别名，返回随机图片；冷却机制默认开启（按用户维度）
- 签到：`@机器人 签到` 每日随机抽取一位幸运女声优并附上图片，当天重复签到返回相同的幸运声优
- 声优列表：`@机器人 声优列表` 返回当前可用声优与图片数量

**Web 管理后台（五个模块）**

- 概览：请求量、成功率、最近日志
- 声优管理：新增 / 编辑 / 启用停用
- 图片管理：图片查询、上传、删除
- 别名管理：新增 / 删除
- 图片同步：触发扫描并增量更新数据库

**运维能力**

- 文件系统监听（watchdog）：图片目录变更自动触发增量同步

## 技术栈

- 后端：**Python 3.9+ / FastAPI / SQLAlchemy + PyMySQL / MySQL 8.0**
- 前端：**Vue3 + TypeScript + Vite + Element Plus**（Vue Router / Axios）
- 部署：**Docker Compose**

> **QQ 接入层（单独说明）**：NoneBot2 + nonebot-adapter-onebot（OneBot v11 协议）作为机器人服务端，NapCat 作为 OneBot 协议服务（QQ 登录与消息收发），二者共同构成 QQ 群接入层。Web 管理后台与 QQ 接入共用同一 FastAPI 服务与 MySQL 数据库，不依赖 QQ 侧即可独立运行与开发。

## 项目结构

```text
.
├── backend/
│   └── bot/
│       ├── main.py                 # 应用入口
│       ├── config.py               # 配置读取（环境变量）
│       ├── manage.py               # 管理命令（同步图片/目录等）
│       ├── admin/                  # 管理后台（内置面板与 API 路由）
│       ├── monitor/                # 文件监听（watchdog）
│       └── plugins/
│           ├── mention_command/    # @机器人命令
│           └── voice_actor/        # 声优核心逻辑（模型/服务/处理器）
├── frontend/                       # 新 Vue3 管理后台前端（已开发完成，待上线）
│   ├── src/
│   │   ├── api/                    # 接口封装（axios，/admin/api/*）
│   │   ├── layouts/                # AdminLayout 管理后台布局
│   │   ├── router/                 # 路由（hash 模式，五个模块）
│   │   └── views/                  # 概览/声优/图片/别名/同步五个页面
│   ├── mock/                       # 开发期 mock 数据（vite-plugin-mock，仅 serve 生效）
│   ├── vite.config.ts              # 含 /admin → 后端 8080 的开发代理配置
│   └── package.json
├── database/
│   ├── init.sql                    # 建表脚本
│   └── seed.sql                    # 初始数据
├── docs/
│   ├── API.md
│   ├── DATABASE.md
│   └── superpowers/plans/          # 开发计划文档
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
- UID / GID：可选，建议设置为宿主机运行用户的 uid/gid（用于避免容器写入后文件变成 root 属主）

建议在生产环境至少修改：

- ONEBOT_ACCESS_TOKEN
- DB_ROOT_PASSWORD
- DB_PASSWORD


### 3) 挂载图片文件夹
在根目录/images下创建声优文件夹，格式为images/声优名。
在相应声优文件夹下放置图片。

### 4) 启动服务

```bash
docker compose up -d --build
```

### 5) 检查状态

```bash
docker compose ps
docker compose logs -f nonebot
```

看到 NoneBot 正常启动且无持续报错后，可访问管理后台：

- http://localhost:8080/admin

如部署在远程服务器，请将 localhost 替换为服务器地址。
如果服务器没有放通8080端口，可使用本地ssh连接。

## 前端开发（新管理后台）

> **状态说明**：Vue3 前端（`frontend/`）已完成开发、五个页面通过 mock 数据联调，**尚未上线**；生产环境当前仍运行 FastAPI 服务内置的管理面板（http://localhost:8080/admin），切换上线为后续任务。

### 启动

```bash
cd frontend
pnpm install
pnpm dev
```


## 使用说明

### 群消息触发

- 在群里发送“声优名称”或“别名”，机器人会返回随机图片
- 冷却机制默认开启（按用户维度）

### @机器人命令

- `@机器人 签到`：每日签到，随机抽取一位幸运女声优并附上图片；当天重复签到时返回相同的幸运声优
- `@机器人 声优列表`：返回当前可用声优与图片数量

### 管理后台

生产环境通过 /admin 访问内置面板（新 Vue3 前端开发完成、待切换上线），包含五个模块：

- 概览（请求量、成功率、最近日志）
- 声优管理（新增/编辑/启用状态）
- 图片管理（查询/上传/删除）
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


<!-- ## 开发说明

当前项目以容器化运行路径为主。若进行本地开发，建议仍通过 Docker Compose 启动 MySQL 与 NapCat，再将代码目录挂载到 nonebot 容器中调试，避免本地路径与运行路径不一致带来的问题。 -->

## 文档导航

- API 设计与扩展开发：docs/API.md
- 数据库设计：docs/DATABASE.md
- 前端重写开发计划：docs/superpowers/plans/2026-08-14-vue3-frontend-rewrite.md

<!-- ## 许可证

当前仓库未声明开源许可证。如需开源，请补充 LICENSE 文件并在此处声明。 -->
