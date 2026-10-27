# Dev / Test / Prod 环境说明

项目使用一个基础 Compose 文件和三个覆盖文件。环境差异保留在覆盖文件与各自的环境变量文件中，应用镜像保持一致，便于从本地迁移到 Linux 服务器。

| 环境 | Compose 覆盖文件 | 环境变量模板 | 用途 |
| --- | --- | --- | --- |
| Dev | `docker-compose.dev.yml` | `.env.dev.example` | 热重载、源码挂载、端口仅绑定本机 |
| Test | `docker-compose.test.yml` | `.env.test.example` | 自动化测试、独立数据库、默认不启动 NapCat |
| Prod | `docker-compose.prod.yml` | `.env.prod.example` | 固定运行镜像、最小端口暴露、只读应用文件系统 |

## 共同原则

- `docker-compose.yml` 只描述所有环境共用的服务关系，不直接暴露宿主机端口。
- `COMPOSE_PROJECT_NAME` 为三套环境使用不同的容器、网络和数据卷命名，避免数据串用。
- 密钥只放在未纳入版本控制的 `.env.dev`、`.env.test`、`.env.prod` 中。
- MySQL 初始化脚本使用 `MYSQL_DATABASE` 指定的库名，不写死环境数据库。
- NapCat 使用 `qq` profile。测试环境默认服务集合只有 `mysql` 与 `test`，不依赖 QQ 登录或 NapCat。
- 所有宿主机路径均使用项目相对路径或环境变量，Compose 文件可直接迁移到 Linux 服务器。

## Dev

首次准备配置：

```powershell
Copy-Item .env.dev.example .env.dev
```

Linux/macOS 使用：

```bash
cp .env.dev.example .env.dev
```

启动后端、前端和 MySQL：

```bash
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

需要联调真实 QQ 时再启用 NapCat：

```bash
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml --profile qq up -d --build
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8080/health`
- MySQL：`127.0.0.1:3307`
- NapCat WebUI（启用 `qq` profile 后）：`http://127.0.0.1:6099`

后端源码和前端源码均绑定挂载，Python 文件由 `watchfiles` 自动重启，Vite 负责前端热更新。若只做界面开发，可在 `.env.dev` 中设置 `VITE_USE_MOCK=true`。

停止环境但保留数据库：

```bash
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml down
```

## Test

准备配置：

```powershell
Copy-Item .env.test.example .env.test
```

运行后端测试，并以测试容器退出码作为命令退出码：

```bash
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test test
```

清理测试容器和测试数据库卷：

```bash
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans
```

运行前端构建检查：

```bash
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml --profile frontend run --rm frontend-test
```

测试环境的默认服务可用以下命令确认：

```bash
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml config --services
```

输出应只有 `mysql` 和 `test`。测试夹具位于 `tests/fixtures/`，不要使用生产图片目录或真实 QQ 凭据。

## Prod

在服务器上准备配置：

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

必须填写以下留空项后再启动：

- `DB_ROOT_PASSWORD`
- `DB_PASSWORD`
- `NONEBOT_IMAGE`（生产服务器当前使用的后端镜像与 tag）
- `FRONTEND_IMAGE`（生产服务器当前使用的前端镜像与 tag）

选择 `BOT_PLATFORM=onebot` 时还需要 `ONEBOT_ACCESS_TOKEN`、`BOT_QQ`；如启用内置 NapCat，还必须设置经验证的固定版本 `NAPCAT_IMAGE`。选择 `BOT_PLATFORM=qq_official` 时需要 `QQ_APP_ID`、`QQ_APP_SECRET`，并关闭 `qq` profile。应用启动时按接入方式校验凭据。

官方接入使用 WebSocket，不需要配置公网回调。先在 QQ 开放平台创建机器人、配置群及单聊事件，并在测试群开启接收所有消息；配置不等于权限验证，必须实测免 @ 接收和图片回复。`DRIVER` 如需覆盖，必须同时包含 FastAPI、HTTP 客户端和 WebSocket 客户端，例如 `~fastapi+~aiohttp`。密钥只放在本机未跟踪的环境文件中。

官方图片上传适配固定的 `nonebot-adapter-qq==1.7.3`，为补齐分片合并参数而使用了适配器的内部上传接口。升级适配器时必须重新检查上传实现，并在测试群回归直传、分片、文字与图片的组合回复。消息去重仅在单进程内有效，重启或多实例部署后不能保证去重。

启用官方接入前，先备份数据库并验证备份，再使用与目标环境相同的数据库配置执行 `python -m bot.manage migrate-qq-identities`。该命令显式创建身份映射表；官方模式启动时只读检查迁移是否完成，不会自动修改数据库。旧签到记录继续保留，身份绑定规则尚未确定。官方群成员身份按机器人和群分别隔离，私聊身份也独立；同一人跨群或私聊的签到暂不合并。

先验证合并后的 Compose 配置：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

再启动：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml pull nonebot frontend
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build --no-deps nonebot frontend
```

生产镜像由 CI 推送到腾讯云 TCR。服务器端 `deploy.sh` 接收一个 `sha-<commit>` 参数，并在执行 Compose 命令时设置对应的 `NONEBOT_IMAGE` 与 `FRONTEND_IMAGE`。NapCat 和 MySQL 不属于普通应用发布范围。

默认前端入口绑定到宿主机 `127.0.0.1:80`；启用内置 NapCat 时，其管理端口也只绑定 `127.0.0.1`。MySQL 和 NoneBot 不直接对外开放。推荐在前端入口前部署 Caddy、Nginx 或云负载均衡负责 HTTPS。外部监控可请求前端入口的 `/health`。

内置 NapCat 由 `.env.prod` 中的 `COMPOSE_PROFILES=qq` 启用。未设置 `NAPCAT_IMAGE` 时占位镜像不可用，不能启动 NapCat。若 NapCat 部署在别处，删除该变量或留空，并让外置 NapCat 连接 `wss://你的域名/onebot/v11/ws`，访问令牌必须与 `ONEBOT_ACCESS_TOKEN` 一致。

查看状态和日志：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml logs -f nonebot
```

部署新版本时拉取镜像并更新业务容器：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml pull nonebot frontend
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build --no-deps nonebot frontend
```

不要在生产环境运行 `down -v`，该命令会删除 MySQL 数据卷。

## 镜像源与跨平台构建

Dockerfile 默认使用官方 Python、Node、Nginx 镜像和 PyPI。网络环境需要镜像站时，可通过构建参数覆盖，而不修改 Dockerfile：

```bash
docker compose build nonebot \
  --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

部署前建议在目标架构上构建，或用 `docker buildx` 生成目标平台镜像。运行数据仅保存在 MySQL 数据卷、`images/` 和 `logs/` 中。
