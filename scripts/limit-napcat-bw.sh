#!/bin/bash
# 限制 napcat 容器带宽 (上传+下载)
# 用法: ./limit-napcat-bw.sh [rate]  默认 1mbit
#        ./limit-napcat-bw.sh clear   清除规则

set -e

RATE="${1:-1mbit}"
CONTAINER="qqbot-napcat"

# 获取网络信息
get_network_info() {
    NET_NAME=$(docker inspect "$CONTAINER" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null)
    NET_ID=$(docker network inspect "$NET_NAME" --format '{{slice .Id 0 12}}' 2>/dev/null)
    BRIDGE="br-${NET_ID}"
    NAP_IP=$(docker inspect "$CONTAINER" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
}

# 清除旧规则
clear_rules() {
    echo "[*] 清除限速规则..."
    get_network_info 2>/dev/null || true

    # 清除 iptables (循环删除所有 napcat-bw-limit 规则)
    while iptables -t mangle -L POSTROUTING -n 2>/dev/null | grep -q "napcat-bw-limit.*MARK set 0xa"; do
        num=$(iptables -t mangle -L POSTROUTING -n --line-numbers 2>/dev/null | grep "napcat-bw-limit.*MARK set 0xa" | head -1 | awk '{print $1}')
        [ -n "$num" ] && iptables -t mangle -D POSTROUTING "$num" 2>/dev/null || break
    done
    while iptables -t mangle -L PREROUTING -n 2>/dev/null | grep -q "napcat-bw-limit.*MARK set 0xb"; do
        num=$(iptables -t mangle -L PREROUTING -n --line-numbers 2>/dev/null | grep "napcat-bw-limit.*MARK set 0xb" | head -1 | awk '{print $1}')
        [ -n "$num" ] && iptables -t mangle -D PREROUTING "$num" 2>/dev/null || break
    done

    # 清除 bridge tc
    if [ -n "$BRIDGE" ]; then
        tc qdisc del dev "$BRIDGE" root   2>/dev/null || true
        tc qdisc del dev "$BRIDGE" ingress 2>/dev/null || true
    fi

    # 清除 ifb
    tc qdisc del dev ifb0 root 2>/dev/null || true
    ip link set ifb0 down 2>/dev/null || true
    ip link delete ifb0 2>/dev/null || true
}

if [ "$RATE" = "clear" ]; then
    clear_rules
    echo "[+] 已清除"
    exit 0
fi

clear_rules

# 重新获取网络信息 (清除后容器状态不变, 但以防万一)
get_network_info

if [ -z "$NAP_IP" ] || [ -z "$BRIDGE" ]; then
    echo "[-] 找不到容器 $CONTAINER 或其网络"
    exit 1
fi

echo "[*] 容器 IP: $NAP_IP"
echo "[*] 桥接口: $BRIDGE"
echo "[*] 限速: $RATE"

# === 上传限速 (容器 → 外网) ===
iptables -t mangle -A POSTROUTING -s "$NAP_IP" -m comment --comment "napcat-bw-limit" -j MARK --set-mark 0xa

tc qdisc add dev "$BRIDGE" root handle 1: htb default 20
tc class add dev "$BRIDGE" parent 1: classid 1:10 htb rate "$RATE" ceil "$RATE"
tc class add dev "$BRIDGE" parent 1: classid 1:20 htb rate 100mbit ceil 100mbit
tc filter add dev "$BRIDGE" parent 1: protocol ip prio 1 handle 0xa fw flowid 1:10

# === 下载限速 (外网 → 容器) ===
iptables -t mangle -A PREROUTING -d "$NAP_IP" -m comment --comment "napcat-bw-limit" -j MARK --set-mark 0xb

modprobe ifb 2>/dev/null || true
ip link add ifb0 type ifb 2>/dev/null || true
ip link set ifb0 up

tc qdisc add dev "$BRIDGE" ingress
tc filter add dev "$BRIDGE" parent ffff: protocol ip prio 1 handle 0xb fw action mirred egress redirect dev ifb0

tc qdisc add dev ifb0 root handle 1: htb default 20
tc class add dev ifb0 parent 1: classid 1:10 htb rate "$RATE" ceil "$RATE"
tc class add dev ifb0 parent 1: classid 1:20 htb rate 100mbit ceil 100mbit
tc filter add dev ifb0 parent 1: protocol ip prio 1 handle 0xb fw flowid 1:10

echo "[+] 已限制 $CONTAINER 带宽为 $RATE (上传+下载)"
echo ""
echo "=== 规则摘要 ==="
echo "--- iptables ---"
iptables -t mangle -L POSTROUTING -n -v 2>/dev/null | grep -E "napcat|Chain" || true
iptables -t mangle -L PREROUTING -n -v 2>/dev/null | grep -E "napcat|Chain" || true
echo "--- tc ---"
tc qdisc show dev "$BRIDGE" 2>/dev/null || true
tc qdisc show dev ifb0 2>/dev/null || true
