# QQ声优机器人 - 服务器部署配置总结

**打包日期：** 2026-04-21  
**公网 IP：** 114.132.233.2  
**部署模式：** 所有容器在同一服务器上

---

## ✅ 镜像构建完成

| 属性            | 值                     |
| --------------- | ---------------------- |
| **镜像名称**    | `qqbot-nonebot:latest` |
| **镜像 SHA256** | `eabbc6b97a65`         |
| **镜像大小**    | 689 MB                 |
| **基础镜像**    | python:3.12-slim       |
| **构建时间**    | 113.6 秒               |

### 镜像包含内容
- ✅ 系统依赖: gcc, g++, locales (UTF-8)
- ✅ Python 依赖: NoneBot 2.2.0, FastAPI, SQLAlchemy, PyMySQL
- ✅ 应用代码: bot 核心 + voice_actor 声优插件
- ✅ 配置文件: /app/config
- ✅ 日志目录: /app/logs
- ✅ 图片目录: /app/images

---

## 🔧 配置修改清单

### 1. .env 文件
```env
SERVER_IP=114.132.233.2
```
用于 NoneBot 和 NapCat 的 WebSocket 反向连接地址

### 2. docker-compose.yml - NoneBot 环境变量
```yaml
NONEBOT_ADAPTER_ONEBOT_WS_REVERSE_SERVERS: '["114.132.233.2:8080"]'
```
✅ **验证值：** `["114.132.233.2:8080"]`

### 3. docker-compose.yml - NapCat 环境变量
```yaml
NAPCAT_ONEBOT_V11_REVERSE_WS: "ws://114.132.233.2:8080/onebot/v11/ws"
```
✅ **验证值：** `ws://114.132.233.2:8080/onebot/v11/ws`

### 4. docker-compose.yml - MySQL 端口映射
```yaml
ports:
  - "127.0.0.1:3307:3306"
```
✅ **修改原因：** 限制 MySQL 仅本机访问，增强安全性

---

## 🚀 运行中的服务

### 容器状态
| 容器名            | 镜像                          | 状态      | 端口                    |
| ----------------- | ----------------------------- | --------- | ----------------------- |
| **qqbot-mysql**   | mysql:8.0                     | ✅ Healthy | 127.0.0.1:3307          |
| **qqbot-nonebot** | qqbot-nonebot:latest          | ✅ Up      | 0.0.0.0:8080            |
| **qqbot-napcat**  | mlikiowa/napcat-docker:latest | ✅ Up      | 0.0.0.0:3000-3001, 6099 |

### 网络配置
- **Docker 网络：** qqbot_qqbot_network (bridge)
- **NoneBot WebSocket 监听：** 0.0.0.0:8080
- **NapCat 反向连接地址：** ws://114.132.233.2:8080/onebot/v11/ws
- **数据库连接：** mysql:3306（容器内部）

---

## 📋 服务器部署检查清单

部署到真实服务器时，需要执行以下操作：

### ✅ 必做项

1. **防火墙配置**（以 UFW 为例）
```bash
sudo ufw allow 8080/tcp        # NoneBot WebSocket
sudo ufw allow 3000:3001/tcp   # NapCat 主端口
sudo ufw allow 6099/tcp        # NapCat 其他端口
sudo ufw reload
sudo ufw status
```

2. **Docker 和 Docker Compose 安装**
```bash
docker --version      # 应为 29.3.1 或更高
docker-compose --version  # 应为 v5.1.1 或更高
```

3. **项目文件上传**
上传整个 qqbot 目录到服务器

4. **启动服务**
```bash
cd /path/to/qqbot
docker-compose up -d
docker-compose ps     # 验证所有容器为 Up
```

5. **验证连接**
```bash
# 检查 NoneBot 是否响应
curl http://114.132.233.2:8080/health

# 检查 NapCat 端口
curl http://114.132.233.2:3000/status
```

### ⚠️ 可选项

1. **HTTPS 支持**（推荐用于生产环境）
   - 使用 Nginx/Caddy 作为反向代理
   - 配置 SSL 证书
   - 将 WSS（WebSocket Secure）端口映射到 443

2. **日志管理**
```bash
# 查看实时日志
docker-compose logs -f nonebot

# 导出日志
docker-compose logs nonebot > /backup/nonebot.log
```

3. **数据备份**
```bash
# MySQL 数据备份
docker exec qqbot-mysql mysqldump -u qqbot -pqqbot123 qqbot > /backup/qqbot.sql

# 图片备份
cp -r /path/to/images /backup/images_backup
```

---

## 🔐 安全建议

1. **更改默认凭证**
   - `.env` 中修改 `DB_PASSWORD`，更新 `ONEBOT_ACCESS_TOKEN`
   - 重新启动容器：`docker-compose restart`

2. **限制 MySQL 访问**
   - ✅ 已配置为本机-only：`127.0.0.1:3307:3306`

3. **监控日志**
```bash
# 定期检查错误
docker-compose logs nonebot | grep ERROR
docker-compose logs napcat | grep ERROR
```

---

## 📝 快速命令参考

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启指定服务
docker-compose restart nonebot

# 查看实时日志
docker-compose logs -f nonebot

# 查看容器状态
docker-compose ps

# 进入容器 shell
docker exec -it qqbot-nonebot /bin/bash

# 导入图片
docker exec qqbot-nonebot python /app/scripts/import_images.py /app/images

# 清理所有卷（谨慎！会删除数据）
docker-compose down -v
```

---

## 🎯 部署验证清单

部署完成后，按以下步骤验证：

- [ ] 所有容器状态为 `Up` 或 `Healthy`
- [ ] MySQL 健康检查通过
- [ ] NoneBot 日志显示 "Application startup complete"
- [ ] `curl http://114.132.233.2:8080` 返回响应
- [ ] NapCat 已连接到 WebSocket（可在日志中看到连接日志）
- [ ] 在 QQ 群中测试机器人响应

---

## 📞 故障排查

### 问题：NoneBot 启动失败
```bash
# 查看详细日志
docker-compose logs nonebot | tail -50

# 常见原因：MySQL 未就绪
# 解决方案：等待 MySQL Healthy，或重启 nonebot
docker-compose restart nonebot
```

### 问题：NapCat 无法连接
```bash
# 检查 WebSocket 反向连接地址
docker exec qqbot-nonebot env | grep NAPCAT_ONEBOT_V11_REVERSE_WS

# 应输出：
# NAPCAT_ONEBOT_V11_REVERSE_WS=ws://114.132.233.2:8080/onebot/v11/ws
```

### 问题：防火墙阻止连接
```bash
# 检查防火墙规则
sudo ufw status

# 允许 NoneBot 端口
sudo ufw allow 8080/tcp
sudo ufw reload
```

---

## 📚 文件变更记录

| 文件                 | 变更                                                        | 原因                     |
| -------------------- | ----------------------------------------------------------- | ------------------------ |
| `.env`               | 添加 `SERVER_IP=114.132.233.2`                              | 配置公网 IP              |
| `docker-compose.yml` | 更新 NoneBot 的 `NONEBOT_ADAPTER_ONEBOT_WS_REVERSE_SERVERS` | 使用公网 IP 而非 0.0.0.0 |
| `docker-compose.yml` | 更新 NapCat 的 `NAPCAT_ONEBOT_V11_REVERSE_WS`               | 使用公网 IP 连接 NoneBot |
| `docker-compose.yml` | MySQL 端口改为 `127.0.0.1:3307:3306`                        | 仅本机访问，安全性提升   |

---

**部署状态：✅ 准备就绪**

所有配置已适配服务器部署，可安全上线。
