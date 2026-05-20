#!/bin/bash
# ~/tools/whitebox_fastapi.sh
# FastAPI 白盒快速审计 — grep 模式库
# 用法: whitebox_fastapi.sh /path/to/project

PROJECT="${1:-.}"
echo "═══════════════════════════════════"
echo " FastAPI 白盒审计"
echo " 目标: $PROJECT"
echo "═══════════════════════════════════"

fail=0
check() { echo ""; echo "── [$1] ──"; shift; grep -rnI --color=always "$@" "$PROJECT" 2>/dev/null && fail=1 || echo "  未命中 ✓"; }

# === 认证/授权 ===
check "无认证路由"              '@app\.(get|post|put|delete).*dependencies=\[\]'
check "缺少Depends认证"         '@app\.(get|post|put|delete).*\)$' 
check "硬编码密钥"              '(secret_key|SECRET_KEY|api_key|API_KEY)\s*=\s*["'"'"'][^"'"'"']{8,}'
check "JWT密钥硬编码"           '(JWT_SECRET|jwt_secret)\s*=\s*["'"'"'][^"'"'"']{8,}'

# === 注入 ===
check "字符串拼接SQL"           'execute\s*\(\s*["'"'"'].*%s|execute\s*\(\s*f["'"'"']'
check "f-string SQL注入"        'execute\s*\(\s*f["'"'"']'
check "裸execute变量"           '\.execute\s*\([^)]*\bf\{'
check "raw SQL拼接"             'text\s*\(\s*["'"'"'].*\+|text\s*\(\s*f["'"'"']'
check "OS命令注入"              'os\.system\s*\(|subprocess\.call\s*\(.*shell=True'
check "eval/exec"               '\beval\s*\(|\bexec\s*\(.*\bf'

# === 文件操作 ===
check "路径穿越"                'os\.path\.join\s*\(.*request|open\s*\(.*request\.(args|form|json)'
check "任意文件读取"            'FileResponse\s*\(.*request|return\s+FileResponse.*path'
check "文件上传未校验"          'UploadFile.*\)\s*:' 

# === 密码/凭据 ===
check "明文密码"                '(password|passwd|pwd)\s*[=:]\s*["'"'"'][^"'"'"']{3,}'
check "数据库密码"              '(DATABASE_URL|DB_PASSWORD|MONGO_URI).*=.*[@:]'

# === CORS配置 ===
check "CORS全开"                'allow_origins=\[.*\*.*\]|allow_origins=\["\*"\]'
check "CORS credentials+*"     'allow_credentials=True.*allow_origins.*\*'

# === 日志/调试 ===
check "调试模式开启"            'debug\s*=\s*True'
check "print泄露"               '\bprint\s*\(.*(password|token|secret|key)'
check "异常信息泄露"            'raise\s+\w+Error\s*\(.*\bf\b'

# === 依赖 ===
check "requirements.txt"        'requirements\.txt'

echo ""
echo "═══════════════════════════════════"
[ $fail -eq 0 ] && echo "  ✓ 快速扫描完成，未发现明显问题" || echo "  ⚠ 发现潜在问题，需人工确认"
echo "═══════════════════════════════════"
