#!/bin/bash
# 监听 napcat 容器启动事件，自动应用带宽限制
# 作为 systemd 服务运行: napcat-bw-watch.service

CONTAINER="qqbot-napcat"
SCRIPT="/home/ubuntu/data/qqbot/scripts/limit-napcat-bw.sh"
RATE="1mbit"

# 启动时先跑一次
sleep 5
if docker inspect "$CONTAINER" &>/dev/null; then
    bash "$SCRIPT" "$RATE" 2>&1 | systemd-cat -t napcat-bw
fi

# 持续监听 docker start 事件
docker events --filter "container=$CONTAINER" --filter "event=start" --format '{{.Action}}' 2>/dev/null | while read -r action; do
    echo "[$(date)] 检测到容器启动，重新应用限速..." | systemd-cat -t napcat-bw
    sleep 3  # 等容器网络就绪
    bash "$SCRIPT" "$RATE" 2>&1 | systemd-cat -t napcat-bw
done
