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

必须填写以下留空项后再启动；Compose 会拒绝缺少这些值的生产配置：

- `DB_ROOT_PASSWORD`
- `DB_PASSWORD`
- `ONEBOT_ACCESS_TOKEN`
- `BOT_QQ`
- `NAPCAT_IMAGE`（填写经过验证的固定版本标签或镜像摘要）

先验证合并后的 Compose 配置：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

再启动：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

默认前端入口绑定到宿主机 `127.0.0.1:80`；启用内置 NapCat 时，其管理端口也只绑定 `127.0.0.1`。MySQL 和 NoneBot 不直接对外开放。推荐在前端入口前部署 Caddy、Nginx 或云负载均衡负责 HTTPS。外部监控可请求前端入口的 `/health`。

内置 NapCat 由 `.env.prod` 中的 `COMPOSE_PROFILES=qq` 启用。若 NapCat 部署在别处，删除该变量或留空，并让外置 NapCat 连接 `wss://你的域名/onebot/v11/ws`，访问令牌必须与 `ONEBOT_ACCESS_TOKEN` 一致。

查看状态和日志：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml logs -f nonebot
```

部署新版本时重新构建并滚动启动：

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
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
