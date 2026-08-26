#!/usr/bin/env bash
# ============================================================
# qqbot 生产部署脚本（由 GitHub Actions 通过 SSH 调用）
# 用法: bash deploy.sh sha-<commit>
# 只更新 nonebot / frontend，绝不触碰 napcat / mysql
# 失败时回滚到部署前的镜像 tag
# ============================================================
set -euo pipefail

TAG="${1:?用法: deploy.sh sha-<commit>}"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DEPLOY_DIR"

TCR_REGISTRY="crpi-ioxf08nbxutvou03.cn-guangzhou.personal.cr.aliyuncs.com"
TCR_NAMESPACE="qqbot_01093724"
TCR_REPOSITORY="seiyuu-bot"

COMPOSE_BASE="docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml"

# ---------- 读取当前 .env.prod 中的镜像（用于回滚） ----------
OLD_NONEBOT_IMAGE="$(grep -E '^NONEBOT_IMAGE=' .env.prod | tail -1 | cut -d= -f2- || true)"
OLD_FRONTEND_IMAGE="$(grep -E '^FRONTEND_IMAGE=' .env.prod | tail -1 | cut -d= -f2- || true)"
echo "==> 当前 NONEBOT_IMAGE: ${OLD_NONEBOT_IMAGE:-<未设置>}"
echo "==> 当前 FRONTEND_IMAGE: ${OLD_FRONTEND_IMAGE:-<未设置>}"

NEW_NONEBOT_IMAGE="${TCR_REGISTRY}/${TCR_NAMESPACE}/${TCR_REPOSITORY}-nonebot:${TAG}"
NEW_FRONTEND_IMAGE="${TCR_REGISTRY}/${TCR_NAMESPACE}/${TCR_REPOSITORY}-frontend:${TAG}"

# ---------- 设置目标镜像（shell 环境变量优先级高于 .env.prod） ----------
export NONEBOT_IMAGE="${NEW_NONEBOT_IMAGE}"
export FRONTEND_IMAGE="${NEW_FRONTEND_IMAGE}"

echo "==> 目标 NONEBOT_IMAGE: ${NONEBOT_IMAGE}"
echo "==> 目标 FRONTEND_IMAGE: ${FRONTEND_IMAGE}"

rollback() {
    local reason="$1"
    echo "❌ 部署失败: ${reason}" >&2
    if [[ -n "${OLD_NONEBOT_IMAGE}" && -n "${OLD_FRONTEND_IMAGE}" ]]; then
        echo "==> 回滚到旧镜像"
        export NONEBOT_IMAGE="${OLD_NONEBOT_IMAGE}"
        export FRONTEND_IMAGE="${OLD_FRONTEND_IMAGE}"
        eval "${COMPOSE_BASE} up -d --no-build --no-deps nonebot frontend" || echo "⚠️ 回滚失败，请人工介入" >&2
    else
        echo "⚠️ 无旧镜像可回滚，请人工介入" >&2
    fi
    exit 1
}

# ---------- 拉取镜像 ----------
echo "==> 拉取镜像 ${TAG}"
if ! eval "${COMPOSE_BASE} pull nonebot frontend"; then
    rollback "镜像拉取失败 ${TAG}"
fi

# ---------- 更新容器 ----------
echo "==> 更新 nonebot / frontend 容器"
if ! eval "${COMPOSE_BASE} up -d --no-build --no-deps nonebot frontend"; then
    rollback "容器更新失败"
fi

# ---------- 健康检查 ----------
echo "==> 等待容器健康（最多 90s）"
HEALTHY=0
for i in $(seq 1 18); do
    sleep 5
    NB_STATUS="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' qqbot-nonebot-1 2>/dev/null || echo down)"
    echo "    [${i}] nonebot: ${NB_STATUS}"
    if [[ "${NB_STATUS}" == "healthy" ]]; then
        HEALTHY=1
        break
    fi
    if [[ "${NB_STATUS}" == "down" || "${NB_STATUS}" == "unhealthy" ]]; then
        break
    fi
done

if [[ "${HEALTHY}" != "1" ]]; then
    rollback "nonebot 未通过健康检查（状态: ${NB_STATUS}）"
fi

# ---------- 业务就绪检查 ----------
echo "==> 检查 /health"
if ! curl -fsS -m 10 http://127.0.0.1:5173/health >/dev/null 2>&1; then
    rollback "/health 不可用"
fi

echo "==> 检查 readiness（数据库 + OneBot 连接）"
if ! curl -fsS -m 15 http://127.0.0.1:5173/admin/api/readiness >/dev/null 2>&1; then
    rollback "readiness 检查失败（可能是 OneBot 重连中，若 30 秒内恢复可忽略）"
fi

# ---------- 记录已部署版本 ----------
echo "==> 更新 .env.prod 中镜像引用（部署完成）"
sed -i "s|^NONEBOT_IMAGE=.*|NONEBOT_IMAGE=${NEW_NONEBOT_IMAGE}|" .env.prod
sed -i "s|^FRONTEND_IMAGE=.*|FRONTEND_IMAGE=${NEW_FRONTEND_IMAGE}|" .env.prod
grep -E '^(NONEBOT_IMAGE|FRONTEND_IMAGE)=' .env.prod || true

echo "✅ 部署完成: ${TAG}"
