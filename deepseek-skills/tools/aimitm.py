#!/usr/bin/env python3
"""
aimitm — AI 友好的 MITM 代理工具
=================================
mitmproxy addon，将 HTTP 流量以结构化 JSON 输出，支持过滤和改包规则。

用法:
  # 基础代理，stdout 输出 JSON 行
  mitmdump -s aimitm.py -p 8080

  # 过滤只输出指定主机
  AIMITM_HOST=target.com mitmdump -s aimitm.py -p 8080

  # 不输出 body
  AIMITM_NO_BODY=1 mitmdump -s aimitm.py -p 8080

  # 加载改包规则
  AIMITM_RULES_FILE=rules.json mitmdump -s aimitm.py -p 8080

  # 静默模式（只输出匹配的流量）
  AIMITM_HOST=target.com AIMITM_QUIET=1 mitmdump -s aimitm.py -p 8080

输出格式 (每行一个 JSON):
{
  "id": 1,
  "ts": "2026-05-20T10:30:01.234",
  "method": "POST",
  "url": "https://target.com/api/login",
  "host": "target.com",
  "path": "/api/login",
  "status": 200,
  "req_headers": {"content-type": "application/json", ...},
  "res_headers": {"server": "nginx", ...},
  "req_body": "{\"user\":\"admin\"}",
  "res_body": "{\"token\":\"...\"}",
  "req_len": 34,
  "res_len": 128,
  "duration_ms": 234,
  "tls": true,
  "alpn": "h2"
}

改包规则格式 (rules.json):
[
  {
    "match": {"host": "target.com", "path_re": "^/api/"},
    "modify": {
      "req_headers": {"X-Forwarded-For": "127.0.0.1"},
      "req_body_replace": {"from": "admin", "to": "superadmin"}
    }
  }
]
"""

import os
import sys
import json
import re
import time
from datetime import datetime, timezone

from mitmproxy import http, ctx


# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════

def _env(key, default=None):
    return os.environ.get(f"AIMITM_{key}", default)

FILTER_HOST = _env("HOST", "")              # 只输出此 host
FILTER_PATH = _env("PATH", "")              # 只输出匹配此路径前缀
FILTER_PATH_RE = _env("PATH_RE", "")        # 正则匹配路径
FILTER_METHOD = _env("METHOD", "")          # 只输出此方法
FILTER_STATUS = _env("STATUS", "")          # 只输出此状态码
FILTER_STATUS_MIN = _env("STATUS_MIN", "")  # 状态码 >=
NO_BODY = bool(_env("NO_BODY"))             # 不输出 body
BODY_MAX = int(_env("BODY_MAX", "5000"))    # body 最大字符数
QUIET = bool(_env("QUIET"))                 # 静默：只输出匹配的
RULES_FILE = _env("RULES_FILE", "")         # 改包规则 JSON 文件
RULES = _env("RULES", "")                   # 改包规则 JSON 字符串
OUTPUT_FILE = _env("OUTPUT", "/tmp/aimitm_output.jsonl")  # 默认输出到文件

# 编译正则
_path_re = re.compile(FILTER_PATH_RE) if FILTER_PATH_RE else None

# 加载改包规则
_modify_rules = []
if RULES:
    try:
        _modify_rules = json.loads(RULES)
    except json.JSONDecodeError:
        ctx.log.error(f"aimitm: 无法解析 AIMITM_RULES: {RULES[:200]}")
elif RULES_FILE:
    try:
        with open(RULES_FILE) as f:
            _modify_rules = json.load(f)
    except Exception as e:
        ctx.log.error(f"aimitm: 无法加载 {RULES_FILE}: {e}")

# 输出文件句柄
_out_fh = None
if OUTPUT_FILE:
    try:
        _out_fh = open(OUTPUT_FILE, "a", buffering=1)  # 行缓冲
    except Exception as e:
        ctx.log.error(f"aimitm: 无法打开输出文件 {OUTPUT_FILE}: {e}")

# 计数器
_counter = 0
_start_time = time.time()


# ═══════════════════════════════════════════════════════
# 过滤逻辑
# ═══════════════════════════════════════════════════════

def _match_filter(flow: http.HTTPFlow) -> bool:
    """返回 True 表示通过过滤，应该输出"""
    if not FILTER_HOST and not FILTER_PATH and not FILTER_PATH_RE and not FILTER_METHOD and not FILTER_STATUS and not FILTER_STATUS_MIN:
        return not QUIET  # 无过滤 + 静默模式 = 不输出

    if FILTER_HOST and flow.request.host != FILTER_HOST:
        return False
    if FILTER_PATH and not flow.request.path.startswith(FILTER_PATH):
        return False
    if _path_re and not _path_re.search(flow.request.path):
        return False
    if FILTER_METHOD and flow.request.method != FILTER_METHOD:
        return False
    if flow.response:
        if FILTER_STATUS and str(flow.response.status_code) != FILTER_STATUS:
            return False
        if FILTER_STATUS_MIN:
            try:
                if flow.response.status_code < int(FILTER_STATUS_MIN):
                    return False
            except ValueError:
                pass
    return True


# ═══════════════════════════════════════════════════════
# 改包逻辑
# ═══════════════════════════════════════════════════════

def _match_rule(rule: dict, flow: http.HTTPFlow) -> bool:
    """检查改包规则是否匹配当前流量"""
    m = rule.get("match", {})
    if "host" in m and flow.request.host != m["host"]:
        return False
    if "path" in m and flow.request.path != m["path"]:
        return False
    if "path_re" in m and not re.search(m["path_re"], flow.request.path):
        return False
    if "method" in m and flow.request.method != m["method"]:
        return False
    return True


def _apply_modify(modify: dict, flow: http.HTTPFlow, direction: str):
    """应用改包规则
    direction: "request" 或 "response"
    """
    # 修改请求头
    if direction == "request" and "req_headers" in modify:
        for k, v in modify["req_headers"].items():
            flow.request.headers[k] = v

    # 修改响应头
    if direction == "response" and "res_headers" in modify:
        for k, v in modify["res_headers"].items():
            flow.response.headers[k] = v

    # 替换请求体
    if direction == "request" and "req_body_replace" in modify:
        r = modify["req_body_replace"]
        old = r["from"]
        new = r["to"]
        body = flow.request.get_text()
        if old in body:
            flow.request.set_text(body.replace(old, new))

    # 替换响应体
    if direction == "response" and "res_body_replace" in modify:
        r = modify["res_body_replace"]
        old = r["from"]
        new = r["to"]
        body = flow.response.get_text()
        if body and old in body:
            flow.response.set_text(body.replace(old, new))


# ═══════════════════════════════════════════════════════
# 安全截断
# ═══════════════════════════════════════════════════════

def _safe_body(body: str | None) -> str | None:
    """安全截断 body，过长时加 '[TRUNCATED]' 标记"""
    if body is None:
        return None
    if len(body) > BODY_MAX:
        return body[:BODY_MAX] + f"\n...[TRUNCATED {len(body)} total chars]"
    return body


def _safe_headers(headers) -> dict:
    """安全转换 headers 为 dict，过滤敏感值"""
    d = dict(headers)
    # 可选：脱敏 Authorization / Cookie
    if _env("REDACT", ""):
        for k in d:
            if k.lower() in ("authorization", "cookie", "set-cookie"):
                d[k] = f"[{len(d[k])} chars redacted]"
    return d


# ═══════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════

def _emit(record: dict):
    """输出一条记录"""
    global _counter
    _counter += 1
    record["id"] = _counter

    line = json.dumps(record, ensure_ascii=False, default=str)

    # 输出到文件或 stdout
    if _out_fh:
        _out_fh.write(line + "\n")
    else:
        print(line, flush=True)


def _build_record(flow: http.HTTPFlow) -> dict:
    """从 flow 构建 JSON 记录"""
    req = flow.request
    res = flow.response

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "method": req.method,
        "url": req.pretty_url,
        "host": req.host,
        "port": req.port,
        "path": req.path,
        "scheme": req.scheme,
        "http_version": req.http_version,
        "tls": req.scheme == "https",
        "alpn": getattr(flow, "alpn", None),
        "req_headers": _safe_headers(req.headers),
        "req_len": len(req.get_content(strict=False) or b""),
        "duration_ms": 0,
    }

    if not NO_BODY:
        record["req_body"] = _safe_body(req.get_text())

    if res:
        record.update({
            "status": res.status_code,
            "reason": res.reason,
            "res_headers": _safe_headers(res.headers),
            "res_len": len(res.get_content(strict=False) or b""),
        })
        if not NO_BODY:
            record["res_body"] = _safe_body(res.get_text())

        # 计算延迟
        if hasattr(res, "timestamp_start") and hasattr(req, "timestamp_start"):
            record["duration_ms"] = round(
                (res.timestamp_start - req.timestamp_start) * 1000, 1
            )

    return record


# ═══════════════════════════════════════════════════════
# mitmproxy Addon
# ═══════════════════════════════════════════════════════

class AiMitm:
    """AI 友好的 MITM 代理 addon"""

    def request(self, flow: http.HTTPFlow):
        # 应用请求阶段改包规则
        for rule in _modify_rules:
            if _match_rule(rule, flow):
                _apply_modify(rule.get("modify", {}), flow, "request")

    def response(self, flow: http.HTTPFlow):
        # 应用响应阶段改包规则
        for rule in _modify_rules:
            if _match_rule(rule, flow):
                _apply_modify(rule.get("modify", {}), flow, "response")

        # 过滤与输出
        if _match_filter(flow):
            _emit(_build_record(flow))

    def done(self):
        # 代理结束时输出统计
        if _out_fh:
            _out_fh.close()
        elapsed = time.time() - _start_time
        ctx.log.info(
            f"aimitm: 捕获 {_counter} 条流量, "
            f"耗时 {elapsed:.0f}s, "
            f"过滤: host={FILTER_HOST or '*'}, path={FILTER_PATH or '*'}"
        )


addons = [AiMitm()]
