#!/usr/bin/env pwsh
# 快速重新打包脚本 - 一键执行

cd c:\Users\i\Desktop\qqbot

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  QQ机器人镜像 - 快速重新打包           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan

# 1. 清理
Write-Host "`n[1/6] 清理旧资源..." -ForegroundColor Green
docker-compose down --volumes --remove-orphans
docker rmi qqbot-nonebot:latest 2>$null
Start-Sleep -Seconds 10

# 2. 构建
Write-Host "[2/6] 重新构建镜像..." -ForegroundColor Green
docker-compose build --no-cache

# 3. 启动
Write-Host "[3/6] 启动服务..." -ForegroundColor Green
docker-compose up -d
Start-Sleep -Seconds 25

# 4. 检查
Write-Host "[4/6] 检查容器状态..." -ForegroundColor Green
docker-compose ps

# 5. 镜像
Write-Host "`n[5/6] 镜像信息..." -ForegroundColor Green
docker images | Select-String qqbot

# 6. 日志
Write-Host "[6/6] 应用日志..." -ForegroundColor Green
docker-compose logs nonebot --tail 20

Write-Host "`n✓ 重新打包完成！" -ForegroundColor Green
