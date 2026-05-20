---
name: aimitm
description: AI 友好 MITM 代理 — 结构化 JSON 流量输出、过滤、改包。用于 SRC 挖洞中的流量分析、API 枚举、参数篡改。触发词：aimitm、mitm、抓包、改包、代理、proxy、流量分析、中间人、拦截。
metadata:
  short-description: AI MITM 代理 — JSON 输出 + 过滤 + 改包
---

# aimitm — AI 友好 MITM 代理

mitmproxy addon，将 HTTP 流量以结构化 JSONL 输出到 stdout，支持过滤和改包规则。替代 Burp 的 AI 友好 CLI 方案。

## 安装

```bash
pip install mitmproxy        # 已装 12.2.3
chmod +x ~/tools/aimitm      # CLI 包装器
```

## 基础用法

```bash
# 方式 1：CLI 包装器（推荐）
aimitm -h target.com                          # 只输出目标主机
aimitm -h target.com -S 400 -n                # 只看 4xx/5xx，无 body
aimitm -h target.com -r rules.json -o out.jsonl  # 改包 + 文件输出

# 方式 2：直接 mitmdump（更多控制）
AIMITM_HOST=target.com AIMITM_NO_BODY=1 \
  mitmdump -s ~/tools/aimitm.py -p 8080
```

## 选项速查

| 选项 | 环境变量 | 作用 |
|------|---------|------|
| `-h HOST` | `AIMITM_HOST` | 只输出此主机 |
| `-P PATH` | `AIMITM_PATH` | 路径前缀过滤 |
| `-R RE` | `AIMITM_PATH_RE` | 正则匹配路径 |
| `-m METHOD` | `AIMITM_METHOD` | HTTP 方法过滤 |
| `-s STATUS` | `AIMITM_STATUS` | 精确状态码 |
| `-S N` | `AIMITM_STATUS_MIN` | 状态码 ≥ N |
| `-n` | `AIMITM_NO_BODY=1` | 不输出 body |
| `-q` | `AIMITM_QUIET=1` | 无过滤时不输出 |
| `-r FILE` | `AIMITM_RULES_FILE` | 改包规则文件 |
| `-o FILE` | `AIMITM_OUTPUT` | 输出到文件 |

## JSON 输出格式

每行一个 JSON 对象，可直接管道消费：

```json
{
  "id": 1, "ts": "2026-05-20T05:03:05.059Z",
  "method": "GET", "url": "http://httpbin.org/get?x=1",
  "host": "httpbin.org", "port": 80, "path": "/get?x=1",
  "scheme": "http", "http_version": "HTTP/1.1", "tls": false,
  "req_headers": {"Host": "...", "User-Agent": "...", ...},
  "res_headers": {"Server": "nginx", "Content-Type": "...", ...},
  "req_body": null, "res_body": null,
  "req_len": 0, "res_len": 314,
  "duration_ms": 234.5, "status": 200
}
```

## 改包规则

### 规则格式

```json
[
  {
    "match": {
      "host": "target.com",
      "path": "/api/login",
      "path_re": "^/api/",
      "method": "POST"
    },
    "modify": {
      "req_headers": {"X-Forwarded-For": "127.0.0.1"},
      "res_headers": {"X-Debug": "true"},
      "req_body_replace": {"from": "旧值", "to": "新值"},
      "res_body_replace": {"from": "admin", "to": "superadmin"}
    }
  }
]
```

### 实战规则示例

**绕过 IP 限制：**
```json
{"match":{"host":"target.com"},"modify":{"req_headers":{"X-Forwarded-For":"127.0.0.1"}}}
```

**测试 IDOR（替换用户 ID）：**
```json
{"match":{"host":"target.com","path_re":"^/api/user/"},
 "modify":{"req_body_replace":{"from":"\"id\":123","to":"\"id\":1"}}}
```

**绕过前端验证（改响应）：**
```json
{"match":{"host":"target.com","path":"/api/auth"},
 "modify":{"res_body_replace":{"from":"\"role\":\"user\"","to":"\"role\":\"admin\""}}}
```

## AI 管道消费模式

```bash
# 实时提取 URL 列表
aimitm -h target.com | jq -r '"\(.method) \(.url) → \(.status)"'

# 只看带参数的 API 请求
aimitm -h target.com | jq 'select(.path | contains("?")) | {method,path,status}'

# 提取所有 Set-Cookie
aimitm -h target.com | jq -r '.res_headers["set-cookie"] // empty'

# 监控异常状态码
aimitm -h target.com -S 400 -n | jq '{ts,method,url,status}'

# 保存 + 实时分析
aimitm -h target.com -o traffic.jsonl &
tail -f traffic.jsonl | jq 'select(.res_body | contains("error")) | .url'
```

## SRC 挖洞集成

### 标准流程

```
启动代理 → 浏览器配置代理 → 浏览目标 → stdout 观察 JSONL
```

### 与侦察工具配合

```bash
# 1. 代理启动
aimitm -h target.com -o ~/文档/traffic_target.jsonl &

# 2. 浏览器走代理访问目标（手动登录、点功能）

# 3. 提取 API 端点
jq -r '.path' ~/文档/traffic_target.jsonl | sort -u | grep '/api/'

# 4. 查找无认证请求
jq 'select(.status != 401 and .status != 403 and .path | startswith("/api/")) 
    | {method,path,status}' ~/文档/traffic_target.jsonl

# 5. 提取 JWT/Token
jq -r '(.req_headers.authorization // .res_body | select(.))' ~/文档/traffic_target.jsonl

# 6. 匹配已知漏洞特征
jq 'select(.res_headers.server | test("Apache/2\\.2"))' ~/文档/traffic_target.jsonl
```

### 自动化改包攻击链

```bash
# 链1: WAF绕过 — 改 X-Forwarded-For
echo '[{"match":{"host":"target.com"},"modify":{"req_headers":{"X-Forwarded-For":"127.0.0.1"}}}]' > /tmp/waf_bypass.json
aimitm -h target.com -r /tmp/waf_bypass.json -o ~/文档/waf_test.jsonl &

# 链2: IDOR枚举 — 替换用户ID
echo '[{"match":{"host":"target.com","path_re":"^/api/user/\\d+"},
  "modify":{"req_body_replace":{"from":"\"id\":123","to":"\"id\":{{ID}}"}}}]' > /tmp/idor.json
# 手动用 sed 替换 {{ID}} 后投递
```

## 注意事项

- 首次使用需安装 mitmproxy CA 证书：`mitmdump` 启动后访问 `mitm.it` 下载
- HTTPS 流量需要客户端信任 mitmproxy 根证书
- 长期运行用 `-o` 输出到文件，防止 stdout 缓冲区问题
- Body 默认截断 5000 字符，改 `AIMITM_BODY_MAX` 调整
- 改包规则支持 `path_re` 正则，但 `req_body_replace` 是纯文本替换，非正则
