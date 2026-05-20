#!/bin/bash
# ~/tools/whitebox_js.sh
# 前端 JS/HTML 白盒快速审计 — grep 模式库
# 用法: whitebox_js.sh /path/to/frontend

PROJECT="${1:-.}"
echo "═══════════════════════════════════"
echo " 前端白盒审计"
echo " 目标: $PROJECT"
echo "═══════════════════════════════════"

fail=0
check() { echo ""; echo "── [$1] ──"; shift; grep -rnI --color=always "$@" "$PROJECT" 2>/dev/null && fail=1 || echo "  未命中 ✓"; }

# === XSS ===
check "innerHTML直接拼接"       '\.innerHTML\s*[+]=]|innerHTML\s*=\s*.*\+'
check "document.write"           'document\.write\s*\('
check "eval执行用户输入"         'eval\s*\(.*(location|search|hash|param|input)'
check "未转义URL参数"            'URLSearchParams.*innerHTML|location\.search.*innerHTML'

# === 敏感数据 ===
check "硬编码API Key"            '(apiKey|api_key|API_KEY)\s*[:=]\s*["'"'"'][A-Za-z0-9_-]{16,}'
check "硬编码Token"              '(token|TOKEN|bearer)\s*[:=]\s*["'"'"'][A-Za-z0-9\._-]{16,}'
check "硬编码密码"               '(password|passwd)\s*[:=]\s*["'"'"'][^"'"'"']{3,}'
check "内网地址"                 '(192\.168\.|10\.\d+\.|172\.1[6-9]\.|172\.2\d\.|172\.3[01]\.)'

# === 不安全配置 ===
check "fetch无credentials"       'fetch\s*\([^)]*\)\s*$' 
check "fetch no-cors"            'mode\s*:\s*["'"'"]no-cors'

# === DOM操作 ===
check "location.href注入"        'location\.href\s*=\s*.*(location\.(search|hash)|param|input)'
check "setTimeout字符串"         'setTimeout\s*\(\s*["'"'"']'

# === 存储 ===
check "localStorage敏感数据"     'localStorage\.setItem\s*\(.*(token|password|key|secret)'
check "sessionStorage敏感"       'sessionStorage\.setItem\s*\(.*(token|password|key|secret)'

# === 第三方 ===
check "http外部脚本"             'src\s*=\s*["'"'"]http://'
check "不安全CDN"                'src\s*=\s*["'"'"']https?://(?!cdn\.|static\.|unpkg\.)[^"'"'"']*\.js'

echo ""
echo "═══════════════════════════════════"
[ $fail -eq 0 ] && echo "  ✓ 快速扫描完成，未发现明显问题" || echo "  ⚠ 发现潜在问题，需人工确认"
echo "═══════════════════════════════════"
