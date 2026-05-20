#!/bin/bash
# ~/tools/security_crawler.sh
# 安全知识批量采集 — 搜索关键词 → 抓取文章 → 保存为Markdown
# 用法:
#   security_crawler.sh "SRC 漏洞挖掘 复盘" 5      # 搜索并抓取前5篇
#   security_crawler.sh --topic logic-flaw          # 使用预制主题

set -e

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
OUTPUT_DIR="$HOME/文档/security_learning"
mkdir -p "$OUTPUT_DIR"

# 预制主题
declare -A TOPICS
TOPICS[logic-flaw]="逻辑漏洞 实战 案例 SRC"
TOPICS[api-auth]="API 未授权访问 漏洞 复盘"
TOPICS[oauth]="OAuth 2.0 漏洞 案例分析"
TOPICS[waf-bypass]="WAF bypass 2025 实战"
TOPICS[cloud]="OSS Bucket 泄露 案例"
TOPICS[ai-security]="LLM 安全 漏洞 prompt injection"
TOPICS[web-top]="2025 Web漏洞 TOP10 复盘"
TOPICS[xss-skill]="XSS 绕过 实战 案例 SRC"
TOPICS[ssrf]="SSRF 漏洞 实战 案例"
TOPICS[rce-chain]="RCE 攻击链 分析 Web安全"
TOPICS[edusrc]="EDU SRC 漏洞 复盘 经验"
TOPICS[commercial-src]="商业SRC 漏洞挖掘 案例分析"
TOPICS[hacktivity]="site:hackerone.com disclosed 漏洞 赏金"
TOPICS[ctf-web]="CTF writeup Web 解题 RCE SSRF"
TOPICS[orange-tsai]="site:blog.orange.tw 漏洞 分析"
TOPICS[project-zero]="site:googleprojectzero.blogspot.com 漏洞"
TOPICS[shodan]="site:blog.shodan.io 2025"
TOPICS[rapid7]="site:blog.rapid7.com metasploit"

usage() {
    echo "安全知识采集器"
    echo "用法: $0 [关键词] [数量]"
    echo "      $0 --topic <主题名>"
    echo ""
    echo "预制主题:"
    for k in "${!TOPICS[@]}"; do
        echo "  $k: ${TOPICS[$k]}"
    done
    exit 0
}

# 参数解析
if [ $# -eq 0 ]; then
    usage
fi

if [ "$1" = "--topic" ]; then
    TOPIC="${TOPICS[$2]}"
    if [ -z "$TOPIC" ]; then
        echo "未知主题: $2"
        usage
    fi
    QUERY="$TOPIC"
    LIMIT=5
elif [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
else
    QUERY="$1"
    LIMIT="${2:-5}"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M)
OUTPUT_FILE="$OUTPUT_DIR/${TIMESTAMP}_$(echo "$QUERY" | tr ' ' '_' | head -c 40).md"

echo "═══════════════════════════════════════"
echo "  安全知识采集"
echo "═══════════════════════════════════════"
echo "  关键词: $QUERY"
echo "  目标数: $LIMIT"
echo "  输出:   $OUTPUT_FILE"
echo "═══════════════════════════════════════"
echo ""

# 搜索（使用 DuckDuckGo HTML）
echo "[1/3] 搜索中..."
SEARCH_URL="https://html.duckduckgo.com/html/?q=$(echo "$QUERY" | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read().strip()))')"

RESULTS=$(curl -s --connect-timeout 10 -H "User-Agent: Mozilla/5.0" "$SEARCH_URL" 2>/dev/null | \
    grep -oP 'class="result__url"[^>]*>\s*\K[^<]+|class="result__snippet"[^>]*>\s*\K[^<]+' | \
    head -$((LIMIT * 2)))

URLS=$(echo "$RESULTS" | grep -E '^https?://' | head -"$LIMIT")
SNIPPETS=$(echo "$RESULTS" | grep -vE '^https?://')

# 写文件头
cat > "$OUTPUT_FILE" << EOF
# 安全学习笔记

> 采集时间: $(date '+%Y-%m-%d %H:%M')
> 关键词: $QUERY
> 来源: DuckDuckGo 搜索

---

EOF

# 逐个抓取
echo "[2/3] 抓取文章中..."
COUNT=0
echo "$URLS" | while IFS= read -r url; do
    [ -z "$url" ] && continue
    COUNT=$((COUNT + 1))
    echo "  [$COUNT/$LIMIT] $url"
    
    # 抓取内容
    CONTENT=$(curl -sL --connect-timeout 10 -H "User-Agent: Mozilla/5.0" "$url" 2>/dev/null | \
        python3 -c "
import sys, re
html = sys.stdin.read()
# 提取文字内容
html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
html = re.sub(r'<[^>]+>', ' ', html)
html = re.sub(r'\s+', ' ', html)
print(html[:3000])
" 2>/dev/null)
    
    if [ -z "$CONTENT" ]; then
        echo "    ⚠ 抓取失败"
        continue
    fi
    
    # 提取标题
    TITLE=$(echo "$CONTENT" | head -1 | cut -c1-80)
    
    cat >> "$OUTPUT_FILE" << EOF

---

### $COUNT. $TITLE

**URL**: $url

\`\`\`
$CONTENT
\`\`\`

EOF
    
    sleep 2  # 避免被封
done

echo ""
echo "[3/3] ✅ 完成"
echo "  输出文件: $OUTPUT_FILE"
echo "  文件大小: $(wc -c < "$OUTPUT_FILE") bytes"
echo ""
echo "下一步: 在 DeepSeek TUI 中说 '加载 $OUTPUT_FILE 分析其中的攻击链'"
