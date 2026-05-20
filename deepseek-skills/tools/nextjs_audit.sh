#!/bin/bash
# ~/tools/nextjs_audit.sh — Next.js 0day 快速审计
TARGET="${1:-.}"

echo "══════════════════════════════════════"
echo " Next.js 0day 审计"
echo " 目标: $TARGET"
echo "══════════════════════════════════════"

fail=0
check() { echo ""; echo "── [$1] ──"; shift; grep -rnI --color=always "$@" "$TARGET" --include="*.ts" --include="*.tsx" --include="*.js" 2>/dev/null && fail=1 || echo "  未命中 ✓"; }

# 1. Middleware
echo ""; echo "=== Middleware 文件 ==="
find "$TARGET" -name "middleware.*" -not -path "*/node_modules/*" 2>/dev/null

# 2. API Routes 无鉴权
echo ""; echo "=== API Routes 无鉴权 ==="
for f in $(find "$TARGET" -name "route.ts" -o -name "route.js" 2>/dev/null | grep -v node_modules); do
  if ! grep -q 'getServerSession\|getToken\|auth()\|withAuth' "$f" 2>/dev/null; then
    echo "  ⚠ 可能无鉴权: $f"
    fail=1
  fi
done

# 3. 敏感关键词
check "硬编码密钥"      '"(sk-|sk-or-|Bearer [A-Za-z0-9_-]{20,})"'
check "Next.js内部头"    'x-middleware|x-nextjs|x-vercel'
check "SSRF风险"        'fetch\s*\(\s*`\$\{|fetch\s*\(\s*request\.'

# 4. Server Actions
echo ""; echo "=== Server Actions ==="
grep -rn "'use server'" "$TARGET" --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v node_modules

# 5. Image Optimization
check "Image SSRF"       'src=\$\{.*url\}|next/image.*src='

# 6. ISR Revalidate
check "Revalidate端点"   'revalidateTag|res\.revalidate|revalidatePath'

echo ""
echo "══════════════════════════════════════"
[ $fail -eq 0 ] && echo "  ✓ 未发现明显问题" || echo "  ⚠ 发现潜在问题"
echo "══════════════════════════════════════"
