#!/bin/bash
# proxy_curl — 通过随机代理池发送 HTTP 请求
# 用法: proxy_curl [curl_args...] URL
#       proxy_curl -sI https://target.com
#       proxy_curl --refresh -X POST https://target.com/api -d '{}'
#
# 首次使用或加 --refresh 时刷新代理池（约15秒）
# 代理池缓存 /tmp/proxy_pool.txt（10分钟有效）

POOL_CACHE="/tmp/proxy_pool.txt"
POOL_TTL=600  # 10分钟
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# 检查是否需要刷新
need_refresh=false
if [[ "$*" == *"--refresh"* ]]; then
    need_refresh=true
    set -- ${@/--refresh/}
elif [ ! -f "$POOL_CACHE" ] || [ $(($(date +%s) - $(stat -c %Y "$POOL_CACHE" 2>/dev/null || echo 0))) -gt $POOL_TTL ]; then
    need_refresh=true
fi

if $need_refresh; then
    echo "[proxy_curl] 刷新代理池..." >&2
    source ~/.virtualenvs/漏洞挖掘/bin/activate 2>/dev/null
    python3 "$SCRIPT_DIR/proxy_pool.py" > "$POOL_CACHE" 2>/dev/null
    count=$(wc -l < "$POOL_CACHE" 2>/dev/null || echo 0)
    if [ "$count" -eq 0 ]; then
        echo "[proxy_curl] ⚠ 无可用代理，直连" >&2
        curl "$@"
        exit $?
    fi
    echo "[proxy_curl] ✓ 可用代理: $count" >&2
fi

# 通过 proxychains 走代理池
proxychains4 -q -f <(
    echo "strict_chain"
    echo "tcp_read_time_out 15000"
    echo "tcp_connect_time_out 8000"
    echo "[ProxyList]"
    # 随机打乱代理顺序
    shuf "$POOL_CACHE" | head -10
) curl "$@"
