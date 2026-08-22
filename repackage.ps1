# QQ机器人 Docker 镜像完整重新打包脚本
# 功能：清理旧镜像 → 重新构建 → 启动服务 → 验证

param(
    [switch]$KeepData = $false,  # 保留数据库数据
    [switch]$Verbose = $true     # 详细输出
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $colors = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "ERROR"   = "Red"
        "WARNING" = "Yellow"
    }
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [$Status] $Message" -ForegroundColor $colors[$Status]
}

function Test-Prerequisites {
    Write-Status "检查前置条件..." "INFO"
    
    # 检查 Docker
    try {
        $dockerVersion = docker --version
        Write-Status "Docker: $dockerVersion" "SUCCESS"
    }
    catch {
        Write-Status "Docker 未安装或未运行" "ERROR"
        exit 1
    }
    
    # 检查 Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Status "Docker Compose: $composeVersion" "SUCCESS"
    }
    catch {
        Write-Status "Docker Compose 未安装" "ERROR"
        exit 1
    }
    
    # 检查项目文件
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Status "docker-compose.yml 不存在" "ERROR"
        exit 1
    }
    Write-Status "✓ 所有前置条件检查完成" "SUCCESS"
}

function Cleanup-Resources {
    Write-Status "清理旧资源..." "INFO"
    
    # 停止容器
    Write-Status "[1/4] 停止并移除容器..." "INFO"
    if ($KeepData) {
        docker-compose down --remove-orphans
    }
    else {
        docker-compose down --volumes --remove-orphans
        Write-Status "已删除所有卷（数据库数据）" "WARNING"
    }
    
    # 删除旧镜像
    Write-Status "[2/4] 删除旧镜像..." "INFO"
    docker rmi qqbot-nonebot:latest 2>$null -ErrorAction SilentlyContinue
    
    # 清理 Docker 系统
    Write-Status "[3/4] 清理未使用的 Docker 资源..." "INFO"
    docker system prune -f --volumes 2>$null -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 10
    Write-Status "✓ 资源清理完成" "SUCCESS"
}

function Build-Image {
    Write-Status "重新构建镜像（耗时 2-3 分钟）..." "INFO"
    
    $buildStart = Get-Date
    docker-compose build --no-cache
    
    if ($LASTEXITCODE -ne 0) {
        Write-Status "✗ 镜像构建失败" "ERROR"
        exit 1
    }
    
    $buildTime = (Get-Date) - $buildStart
    Write-Status "✓ 镜像构建完成 (耗时: $($buildTime.Minutes)m $($buildTime.Seconds)s)" "SUCCESS"
}

function Start-Services {
    Write-Status "启动服务..." "INFO"
    
    docker-compose up -d
    Write-Status "等待服务初始化（25 秒）..." "INFO"
    Start-Sleep -Seconds 25
    
    Write-Status "✓ 服务启动完成" "SUCCESS"
}

function Verify-Setup {
    Write-Status "验证部署..." "INFO"
    
    # 检查容器状态
    Write-Status "`n=== 容器状态 ===" "INFO"
    $psOutput = docker-compose ps
    Write-Host $psOutput
    
    # 检查镜像
    Write-Status "`n=== 构建的镜像 ===" "INFO"
    $imageInfo = docker images | Select-String "qqbot"
    if ($imageInfo) {
        Write-Host $imageInfo
        Write-Status "✓ 镜像已成功构建" "SUCCESS"
    }
    else {
        Write-Status "✗ 镜像未找到" "ERROR"
        exit 1
    }
    
    # 检查应用日志
    Write-Status "`n=== NoneBot 应用日志 ===" "INFO"
    $logs = docker-compose logs nonebot --tail 20
    Write-Host $logs
    
    # 检查是否有关键错误
    if ($logs -match "ERROR" -or $logs -match "Exception") {
        Write-Status "⚠ 应用日志中发现错误，请检查" "WARNING"
    }
    elseif ($logs -match "Application startup complete") {
        Write-Status "✓ 应用已正常启动" "SUCCESS"
    }
    
    # 检查 MySQL 健康状态
    Write-Status "`n=== MySQL 健康检查 ===" "INFO"
    $mysqlLogs = docker-compose logs mysql --tail 10
    if ($mysqlLogs -match "ready for connections") {
        Write-Status "✓ MySQL 已就绪" "SUCCESS"
    }
    
    # 检查 NapCat 状态
    Write-Status "`n=== NapCat 日志 ===" "INFO"
    $napcatLogs = docker-compose logs napcat --tail 10
    Write-Host $napcatLogs
}

function Show-Summary {
    $totalTime = (Get-Date) - $startTime
    
    Write-Status "`n╔════════════════════════════════════════╗" "INFO"
    Write-Status "║  重新打包完成！                        ║" "SUCCESS"
    Write-Status "╚════════════════════════════════════════╝" "INFO"
    
    Write-Status "总耗时: $($totalTime.Minutes)m $($totalTime.Seconds)s" "SUCCESS"
    Write-Status "`n后续步骤：" "INFO"
    Write-Host "1. 验证所有容器是否处于 'Up' 状态"
    Write-Host "2. 上传镜像到服务器：docker save qqbot-nonebot:latest -o qqbot-nonebot.tar"
    Write-Host "3. 在服务器上导入镜像：docker load -i qqbot-nonebot.tar"
    Write-Host "4. 启动服务：docker-compose up -d"
    Write-Host "5. 上传语音演员图片到 images/ 目录"
}

# === 主执行流程 ===
try {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  QQ机器人 Docker 镜像重新打包脚本      ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    
    if ($KeepData) {
        Write-Status "⚠ 运行模式：保留数据库数据" "WARNING"
    }
    else {
        Write-Status "⚠ 运行模式：清理所有数据和卷" "WARNING"
    }
    
    Test-Prerequisites
    Cleanup-Resources
    Build-Image
    Start-Services
    Verify-Setup
    Show-Summary
}
catch {
    Write-Status "✗ 脚本执行出错: $_" "ERROR"
    exit 1
}
