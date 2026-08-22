# 云服务器部署指南（Ubuntu）

> 当前生产 Compose、密钥要求和端口策略见 [`ENVIRONMENTS.md`](ENVIRONMENTS.md)。本文中的旧版 Compose 片段仅供历史参考，请勿直接覆盖现有三环境配置。

本指南将帮助您在 Ubuntu 云服务器上部署 QQ 声优机器人，实现从本地 Windows 开发环境的快速迁移。

## 前置要求

### 云服务器配置

- 操作系统：Ubuntu 20.04 LTS 或更新版本
- CPU：2 核及以上
- 内存：2GB 及以上（推荐 4GB）
- 磁盘：20GB 及以上（根据图片数量调整）
- 网络：能访问互联网，开放必要的端口（3306、8080 等）

### 工具

- SSH 客户端（用于远程连接）
- Git（用于克隆项目）

## 部署步骤

### 1. 连接到云服务器

```bash
# 使用 SSH 连接
ssh root@your_server_ip

# 或使用密钥文件
ssh -i /path/to/key.pem root@your_server_ip
```

### 2. 安装 Docker 和 Docker Compose

#### 安装 Docker

```bash
# 更新系统包
sudo apt-get update
sudo apt-get upgrade -y

# 安装依赖
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# 验证安装
docker --version

# 启用 Docker 服务
sudo systemctl enable docker
sudo systemctl start docker
```

#### 安装 Docker Compose

```bash
# 下载最新版本
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 赋予执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version

# （可选）创建符号链接
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
```

### 3. 克隆项目

```bash
# 进入工作目录
cd /opt

# 克隆项目
git clone <your_repository_url> qqbot

# 进入项目目录
cd qqbot

# 查看目录结构
ls -la
```

### 4. 配置环境变量

```bash
# 复制 .env 模板
cp .env .env.production

# 编辑配置文件
nano .env.production

# 关键配置项：
```

修改以下配置：

```env
# MySQL 配置（生产环境建议使用强密码）
DB_ROOT_PASSWORD=your_strong_root_password
DB_PASSWORD=your_strong_db_password
DB_NAME=qqbot
DB_USER=qqbot
DB_PORT=3306

# NoneBot 配置
NONEBOT_PORT=8080
LOG_LEVEL=INFO

# NapCat 配置（假设 NapCat 在其他服务器或本地 QQ）
NAPCAT_HOST=napcat.your_domain.com
NAPCAT_PORT=3001

# QQ 机器人配置
BOT_QQ=your_bot_qq
GROUP_ID=your_group_id

# 应用设置
COOLDOWN_DURATION=1
IMAGE_FOLDER=/app/images
```

**安全建议**：
- 使用强密码（≥ 16 字符，包含大小写、数字、特殊字符）
- 将 `.env.production` 添加到 `.gitignore`
- 使用数据库备份密码和生产密码不同

### 5. 配置防火墙和端口

```bash
# 检查防火墙状态
sudo ufw status

# 如果启用了防火墙，允许必要的端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 3306/tcp  # MySQL（可选，仅如果需要外部访问）
sudo ufw allow 8080/tcp  # NoneBot（可选）
sudo ufw allow 3001/tcp  # NapCat WebSocket（可选）

# 例如，仅允许本地连接到 MySQL
sudo ufw allow from 127.0.0.1 to any port 3306
```

### 6. 准备数据（从本地迁移）

#### 选项 A：通过 MySQL 转储文件迁移

在本地机器上：

```bash
# 导出本地数据库
docker exec qqbot-mysql mysqldump -u qqbot -pqqbot123 qqbot > backup.sql
```

上传到服务器：

```bash
# 使用 SCP 上传文件
scp -i /path/to/key.pem backup.sql root@your_server_ip:/opt/qqbot/

# 或使用 FTP、云存储等工具
```

在服务器上恢复：

```bash
# 启动 MySQL 容器
docker-compose up -d mysql

# 等待 MySQL 就绪（约 30 秒）
sleep 30

# 恢复数据库
docker exec -i qqbot-mysql mysql -u qqbot -pqqbot123 qqbot < backup.sql

# 验证
docker exec qqbot-mysql mysql -u qqbot -pqqbot123 -e "SELECT COUNT(*) FROM qqbot.voice_actors;"
```

#### 选项 B：通过图片文件和脚本重新导入

在服务器上：

```bash
# 创建图片目录
mkdir -p /opt/qqbot/images

# 上传图片文件到服务器（使用 scp、rsync 或云存储）
rsync -av --progress /local/images/ root@your_server_ip:/opt/qqbot/images/

# 或使用 SCP
scp -r -i /path/to/key.pem /local/images/* root@your_server_ip:/opt/qqbot/images/
```

### 7. 启动应用

```bash
# 进入项目目录
cd /opt/qqbot

# 使用 -f 指定生产环境配置文件（可选）
docker-compose --env-file .env.production up -d

# 或直接使用默认的 .env
docker-compose up -d

# 查看容器状态
docker-compose ps

# 预期输出：
# NAME              SERVICE      STATUS
# qqbot-mysql       mysql        Up ...
# qqbot-nonebot     nonebot      Up ...
```

### 8. 验证部署

```bash
# 查看容器日志
docker-compose logs nonebot

# 预期看到：
# INFO: 声优插件已加载
# INFO: 所有插件加载完成

# 测试数据库连接
docker-compose exec mysql mysql -u qqbot -pqqbot123 -e "SELECT COUNT(*) FROM voice_actors;"

# 测试 NoneBot 端口
curl http://localhost:8080

# 查看资源使用情况
docker stats
```

### 9. 导入图片数据（如果使用选项 B）

```bash
# 启动应用后导入图片
docker-compose exec nonebot python /app/scripts/import_images.py /app/images

# 添加别名
docker-compose exec nonebot python /app/scripts/manage_aliases.py add "别名1" "声优名称"
```

### 10. 配置日志和监控

#### 配置日志输出

```bash
# 查看实时日志
docker-compose logs -f

# 查看特定容器日志
docker-compose logs -f nonebot

# 查看日期范围内的日志
docker-compose logs --since 2024-01-15T10:00:00Z
```

#### 配置日志持久化

编辑 `docker-compose.yml`，为 nonebot 服务添加日志配置：

```yaml
services:
  nonebot:
    ...
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

#### 安装 Portainer（可选 Web 管理面板）

```bash
# 启动 Portainer
docker run -d -p 9000:9000 -p 8000:8000 \
  --name portainer \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# 访问 http://your_server_ip:9000
```

## 后续维护

### 数据备份

#### 自动备份脚本

创建 `/opt/qqbot/backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR="/opt/qqbot/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="qqbot"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker exec qqbot-mysql mysqldump -u qqbot -pqqbot123 $DB_NAME \
  | gzip > $BACKUP_DIR/qqbot_$TIMESTAMP.sql.gz

# 清理 7 天前的备份
find $BACKUP_DIR -name "qqbot_*.sql.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR/qqbot_$TIMESTAMP.sql.gz"
```

设置定时备份（cron）：

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 2 点备份
0 2 * * * bash /opt/qqbot/backup.sh
```

### 监控和告警

#### 使用 Prometheus + Grafana（可选）

```yaml
# docker-compose.yml 中添加
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
```

### 更新应用

```bash
# 拉取最新代码
cd /opt/qqbot
git pull origin main

# 重新构建镜像
docker-compose build --no-cache nonebot

# 重启服务
docker-compose up -d nonebot

# 查看日志确认更新成功
docker-compose logs -f nonebot
```

### 清理磁盘空间

```bash
# 查看 Docker 磁盘使用
docker system df

# 清理未使用的镜像和容器
docker system prune -a

# 清理日志文件
docker exec qqbot-mysql mysql -u qqbot -pqqbot123 -e \
  "DELETE FROM request_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);"
```

## 扩展和优化

### 数据库优化

```bash
# 连接到数据库
docker exec -it qqbot-mysql mysql -u qqbot -pqqbot123 qqbot

# 查看表大小
SELECT TABLE_NAME, ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb 
FROM information_schema.TABLES 
WHERE table_schema = 'qqbot' 
ORDER BY size_mb DESC;

# 优化表
OPTIMIZE TABLE voice_actors, images, aliases, user_cooldowns;
```

### 性能调优

```bash
# 查看慢查询日志
docker exec qqbot-mysql mysql -u qqbot -pqqbot123 -e \
  "SHOW VARIABLES LIKE 'long_query_time';"

# 设置更严格的阈值
docker exec qqbot-mysql mysql -u qqbot -pqqbot123 -e \
  "SET GLOBAL long_query_time = 0.5;"
```

### 扩展到多个机器人实例

```yaml
# docker-compose.yml
services:
  nonebot-instance1:
    # ... 配置
    environment:
      BOT_QQ: 123456789
      
  nonebot-instance2:
    # ... 配置
    environment:
      BOT_QQ: 987654321
```

## 故障排查

### 常见问题

#### 问题：容器无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查端口是否被占用
sudo netstat -tlnp | grep :3306
sudo netstat -tlnp | grep :8080

# 释放被占用的端口
sudo fuser -k 3306/tcp
```

#### 问题：数据库连接失败

```bash
# 检查 MySQL 容器状态
docker-compose logs mysql

# 验证网络连接
docker network ls
docker network inspect qqbot_qqbot_network

# 测试 MySQL 连接
docker run --rm --network qqbot_qqbot_network mysql:8.0 \
  mysql -h mysql -u qqbot -pqqbot123 -e "SELECT 1;"
```

#### 问题：磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 查看大文件
find /opt/qqbot -size +100M

# 清理旧日志
docker system prune --volumes -f

# 清理 MySQL 日志
docker exec qqbot-mysql mysql -u root -proot123 -e \
  "PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);"
```

## 性能基准

在标准配置下（2 核 2GB 内存）的预期性能：

| 指标         | 性能                     |
| ------------ | ------------------------ |
| 并发用户     | 100+                     |
| 平均响应时间 | < 200ms                  |
| 内存使用     | ~400MB (MySQL + NoneBot) |
| 磁盘读写     | < 10 IOPS                |

## 高可用部署（可选）

对于生产环境，考虑以下改进：

1. **数据库主从复制** - 提高数据安全性
2. **负载均衡** - 支持多实例
3. **CDN** - 加速图片分发
4. **消息队列** - 异步处理请求
5. **缓存层** - Redis 加速查询

详情请参考运维团队的最佳实践。

## 支持

- 遇到问题？检查 [SETUP.md](SETUP.md)
- 查看项目日志：`docker-compose logs`
- 阅读 [README.md](../README.md) 了解更多信息
