# 🎯 QQ机器人 Docker 镜像 - 重新打包指南

## 📋 快速开始

### 方案 1：使用完整打包脚本（推荐）
包含完整的前置检查、清理、构建、验证和错误处理：

```powershell
# 清理所有数据（新鲜环境）
cd c:\Users\i\Desktop\qqbot
.\repackage.ps1

# 或保留数据库数据
.\repackage.ps1 -KeepData
```

**特点**：
- ✅ 自动检查 Docker 和 Docker Compose
- ✅ 详细的进度提示和错误处理
- ✅ 完整的验证和诊断
- ✅ 彩色输出便于阅读
- ⏱️ 预计耗时：4-5 分钟

### 方案 2：使用快速打包脚本
简化版本，适合已验证过环境的情况：

```powershell
cd c:\Users\i\Desktop\qqbot
.\repackage-quick.ps1
```

**特点**：
- ⚡ 快速执行，无冗余输出
- 🔄 包含清理→构建→启动→验证的完整流程
- ⏱️ 预计耗时：4 分钟

### 方案 3：分步手动执行
需要完全控制每一步：

```powershell
cd c:\Users\i\Desktop\qqbot

# 清理旧资源
docker-compose down --volumes --remove-orphans
docker rmi qqbot-nonebot:latest 2>$null
Start-Sleep -Seconds 10

# 重新构建
docker-compose build --no-cache

# 启动服务
docker-compose up -d
Start-Sleep -Seconds 25

# 验证
docker-compose ps
docker images | Select-String qqbot
docker-compose logs nonebot --tail 20
```

## 🔄 打包流程详解

### 第1步：清理旧资源（3-5 秒）
```powershell
docker-compose down --volumes --remove-orphans
```
- 停止所有运行的容器
- 删除容器创建的卷（MySQL 数据、NapCat 数据）
- 移除孤立的网络

⚠️ **警告**：这会删除 MySQL 数据库！如需保留数据，改用：
```powershell
docker-compose down --remove-orphans
```

### 第2步：删除旧镜像（1-2 秒）
```powershell
docker rmi qqbot-nonebot:latest
```
- 移除旧版本的 NoneBot 镜像
- 确保全新的镜像构建

### 第3步：等待系统清理（10 秒）
```powershell
Start-Sleep -Seconds 10
```
- 让 Docker 完全释放资源
- 避免构建时资源竞争

### 第4步：重新构建镜像（2-3 分钟）
```powershell
docker-compose build --no-cache
```
- 从 Dockerfile 逐行执行
- `--no-cache` 确保不使用缓存，全新构建

**构建步骤**：
1. 拉取 python:3.12-slim 基础镜像（150MB）
2. 安装系统依赖：gcc, g++, locales（50MB）
3. 从清华源安装 14 个 Python 包（300MB）
4. 复制应用代码到 /app/bot（139MB）
5. 复制配置文件到 /app/config
6. 创建日志和图片目录
7. 设置启动命令和健康检查

**预期输出**：
```
[+] Building 2:45.234 
[+] Running 13/13
 ✔ nonebot
Successfully tagged qqbot-nonebot:latest
```

**镜像大小**：~689MB

### 第5步：启动所有服务（30-40 秒）
```powershell
docker-compose up -d
```
启动三个服务（后台模式）：
- **MySQL 8.0**：数据库（会自动运行 init.sql 和 seed.sql）
- **NoneBot**：机器人应用（等待 MySQL 健康后启动）
- **NapCat**：QQ 协议适配（最后启动）

### 第6步：等待初始化（25 秒）
```powershell
Start-Sleep -Seconds 25
```
- MySQL 初始化数据库表（10-15 秒）
- NoneBot 加载插件、启动 Uvicorn 服务器（8-10 秒）
- NapCat 连接 NoneBot 的 WebSocket（5 秒）

### 第7步：验证（10 秒）
```powershell
docker-compose ps
docker-compose logs nonebot --tail 20
```

**预期输出**：
```
NAME            IMAGE                      STATUS
qqbot-mysql     mysql:8.0                  Up (healthy)
qqbot-nonebot   qqbot-nonebot:latest       Up
qqbot-napcat    mlikiowa/napcat-docker     Up

=== 日志 ===
04-21 XX:XX:XX [SUCCESS] nonebot | 🚀 Running NoneBot...
04-21 XX:XX:XX [INFO] uvicorn | Application startup complete.
04-21 XX:XX:XX [INFO] uvicorn | Uvicorn running on http://0.0.0.0:8080
```

## ⏱️ 耗时估计

| 步骤 | 耗时 | 说明 |
|-----|------|------|
| 1. 清理 | 3-5 秒 | 停止和删除容器 |
| 2. 删除镜像 | 1-2 秒 | 删除旧镜像 |
| 3. 等待 | 10 秒 | 资源释放 |
| 4. 构建 | 2-3 分钟 | 完整镜像编译 |
| 5. 启动 | 30-40 秒 | 拉取镜像、启动容器 |
| 6. 初始化 | 25 秒 | 数据库和应用初始化 |
| 7. 验证 | 10 秒 | 状态检查和日志查看 |
| **总计** | **4-5 分钟** | |

## 🚨 常见问题

### Q: 构建过程中网络超时
**A**: 镜像需要从清华 PyPI 源下载 Python 包。解决方法：
1. 检查网络连接
2. 等待 30 秒后重试
3. 如多次失败，检查 Docker 代理设置

### Q: 磁盘空间不足
**A**: 清理 Docker 系统：
```powershell
docker system prune -a --volumes
```

### Q: 容器启动失败
**A**: 检查日志：
```powershell
docker-compose logs
```

### Q: MySQL 连接失败
**A**: 等待 MySQL 完全初始化（30 秒），然后检查：
```powershell
docker-compose logs mysql --tail 20
```

### Q: 想要保留数据库数据
**A**: 不使用 `--volumes` 参数：
```powershell
docker-compose down --remove-orphans  # 不删除卷
docker-compose build --no-cache
docker-compose up -d
```

## 📊 验证清单

打包完成后，检查以下项目：

```powershell
# 1. 所有容器在运行
docker-compose ps
# 预期：3 个 Up 状态的容器

# 2. 镜像已构建
docker images | Select-String qqbot
# 预期：qqbot-nonebot:latest 689MB

# 3. NoneBot 应用正常启动
docker-compose logs nonebot --tail 5 | Select-String "startup complete"
# 预期：看到 "Application startup complete"

# 4. MySQL 健康
docker-compose logs mysql --tail 5 | Select-String "ready for connections"
# 预期：看到 "ready for connections"

# 5. NapCat 已连接
docker-compose logs napcat --tail 10
# 预期：看到连接成功的日志
```

## 📦 下一步：上传到服务器

镜像打包完成后，可以上传到 Ubuntu 服务器：

```powershell
# 1. 导出镜像
docker save qqbot-nonebot:latest -o qqbot-nonebot.tar

# 2. 上传到服务器（使用 WinSCP 或 SCP）
# 服务器地址：114.132.233.2
# 上传目标：/opt/qqbot/qqbot-nonebot.tar
```

服务器端导入：
```bash
# SSH 进入服务器
ssh root@114.132.233.2

# 进入项目目录
cd /opt/qqbot

# 导入镜像
docker load -i qqbot-nonebot.tar

# 启动服务
docker-compose up -d

# 验证
docker-compose ps
docker-compose logs nonebot --tail 20
```

## 🔧 脚本参数

### repackage.ps1 参数

```powershell
# 清理所有数据（默认）
.\repackage.ps1

# 保留数据库数据
.\repackage.ps1 -KeepData

# 详细输出（默认启用）
.\repackage.ps1 -Verbose:$true

# 简化输出
.\repackage.ps1 -Verbose:$false
```

## 📝 调试建议

如果打包失败，使用完整脚本会显示详细错误信息。手动分步执行时：

```powershell
# 检查 Docker 状态
docker info

# 查看系统资源
docker system df

# 构建时显示详细日志
docker-compose build --no-cache --progress=plain

# 查看所有日志（不只是最后 20 行）
docker-compose logs

# 进入容器进行调试
docker-compose exec nonebot bash
docker-compose exec mysql bash
```

---

**选择推荐方案**：首次打包用完整脚本 `.\repackage.ps1`，之后可用快速脚本 `.\repackage-quick.ps1`。
