# 快速启动

项目已拆分为 Dev / Test / Prod 三套 Compose 环境。完整说明见 [`docs/ENVIRONMENTS.md`](docs/ENVIRONMENTS.md)。

## 本地开发

```powershell
Copy-Item .env.dev.example .env.dev
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

如需真实 QQ 联调，在启动命令中加入 `--profile qq`。不启用该 profile 时，开发环境只启动 MySQL、NoneBot 和前端。

访问：

- 前端：`http://127.0.0.1:5173`
- 健康检查：`http://127.0.0.1:8080/health`

## 自动化测试

```powershell
Copy-Item .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test test
docker compose --env-file .env.test -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans
```

测试默认只启动 MySQL 和测试容器，不启动、不连接 NapCat。

## 生产部署

```bash
cp .env.prod.example .env.prod
# 编辑 .env.prod，填写所有留空密钥并固定 NapCat 镜像版本
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

生产环境的业务入口只在 `127.0.0.1:80` 暴露，适合接到服务器上的 HTTPS 反向代理后面；MySQL 和 NoneBot 不直接映射宿主机端口。
