---
name: zeroday-hunting
description: 0day 漏洞挖掘 Skill — 未知漏洞发现、模糊测试、代码审计、漏洞利用。用于授权测试。
metadata:
  short-description: 0day漏洞挖掘工具与流程
---

# 0day 漏洞挖掘 Skill

未知漏洞发现方法论，仅用于授权测试。

---

## 挖掘路线

```
目标是什么？
├── Python Web框架(FastAPI/Django) → Hypothesis + Bandit + 手工审计
├── C/C++ 二进制               → AFL++ + Ghidra + pwntools
├── PHP CMS(WordPress/DedeCMS) → Semgrep + 手工diff
├── 固件(IoT/路由器)            → binwalk + Ghidra
├── 协议(HTTP/WebSocket)       → mitmproxy + Wireshark
└── API逻辑                    → mitmproxy + 手工Fuzzing
```

---

## Python 0day 挖掘流程

### 1. Hypothesis 属性测试

```python
from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule

class APIFuzzer(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.token = None
    
    @rule(
        email=st.emails(),
        password=st.text(min_size=1, max_size=50),
    )
    def register(self, email, password):
        resp = requests.post(f"{API}/api/v1/auth/register", json={
            "email": email, "password": password
        })
        assert resp.status_code in (201, 400, 409, 422)
    
    @rule(
        email=st.emails(),
        wrong_password=st.text(min_size=6, max_size=50)
    )
    def login_bruteforce(self, email, wrong_password):
        resp = requests.post(f"{API}/api/v1/auth/login", json={
            "email": email, "password": wrong_password
        })
        assert "Traceback" not in resp.text
        assert "500" not in str(resp.status_code)

TestFuzzer = APIFuzzer.TestCase
```

### 2. Semgrep 自定义规则

```yaml
rules:
  - id: fastapi-mass-assignment
    pattern: |
      def $F(..., body: $MODEL, ...):
          ...
          $OBJ = $MODEL(**body.dict())
    message: "Mass assignment: 用户可控字段未白名单"
    languages: [python]
    severity: WARNING

  - id: jwt-none-algorithm
    patterns:
      - pattern: jwt.decode($TOKEN, $KEY, algorithms=["HS256"])
      - pattern-not: jwt.decode($TOKEN, $KEY, algorithms=[..., "none", ...])
    message: "JWT未禁用none算法"
    languages: [python]
    severity: ERROR
```

```bash
semgrep --config rules.yaml /path/to/target
```

### 3. API 边界测试

```python
PAYLOADS = {
    "id": [None, "", -1, 0, 1, 999999, "1 OR 1=1", "../etc/passwd"],
    "email": [None, "", "a"*1000, "admin@admin.com", "<script>alert(1)</script>"],
    "page": [-1, 0, 1, 999999, "NaN"],
    "limit": [-1, 0, 1, 999999, "NaN"],
}

def fuzz_endpoint(url, method="GET", param_rules=None):
    for param, values in (param_rules or PAYLOADS).items():
        for val in values:
            try:
                if method == "GET":
                    resp = requests.get(url, params={param: val}, timeout=5)
                else:
                    resp = requests.post(url, json={param: val}, timeout=5)
                
                if resp.status_code == 500:
                    print(f"[!] 500 on {param}={val}: {resp.text[:200]}")
                if "Traceback" in resp.text or "Exception" in resp.text:
                    print(f"[!] 错误泄露 on {param}={val}")
            except Exception as e:
                print(f"[!] 连接异常 {param}={val}: {e}")
```

### 4. 依赖CVE扫描

```bash
pip-audit                    # Python依赖CVE
safety check                 # 备选
trivy fs .                   # 通用
```

---

## C/C++ 0day 挖掘流程

### AFL++ 模糊测试

```bash
afl-clang-fast -o target_fuzz target.c
mkdir in out
echo "seed" > in/seed.txt
afl-fuzz -i in -o out ./target_fuzz @@
```

### Ghidra 逆向分析

```bash
ghidraRun
# File → New Project → Import binary
# Analysis → Auto Analyze
# Search → For Strings → 找硬编码密钥/密码
# Window → Decompile → 分析逻辑
```

### radare2 快速分析

```bash
r2 -A target_binary
> afl           # 列出函数
> iz            # 列出字符串
> / password    # 搜索关键字
> VV            # 可视化模式
```

---

## 固件分析流程

```bash
binwalk -Me firmware.bin
cd _firmware.bin.extracted
find . -name "passwd" -o -name "shadow" -o -name "*.conf"
grep -r "password\|secret\|key\|token" . 2>/dev/null
find . -type f -executable | while read bin; do
    file "$bin" | grep -q "ELF" && echo "ELF: $bin"
done
```

---

## 流量分析

### mitmproxy 拦截API

```python
from mitmproxy import http

def response(flow: http.HTTPFlow):
    # 检测信息泄露
    if "password" in flow.response.text.lower():
        print(f"[!] 密码泄露: {flow.request.url}")
    if "SELECT" in flow.response.text or "INSERT" in flow.response.text:
        print(f"[!] SQL泄露: {flow.request.url}")
```

```bash
mitmdump -s analyze.py -p 8080
```

---

## 0day 检查清单

```
□ 依赖CVE（pip-audit / trivy）
□ 硬编码密钥（grep + Ghidra字符串）
□ JWT算法（none算法/弱密钥）
□ 速率限制（可爆破？）
□ 错误信息泄露（堆栈跟踪？）
□ 参数边界（负数/超大值/None）
□ 类型混淆（字符串当整数？）
□ 竞态条件（并发请求？）
□ 身份伪造（IDOR？）
□ 路径穿越（../etc/passwd？）
□ 反序列化（pickle/yaml.load？）
□ SSRF（可控制URL？）
□ XXE（XML解析？）
```

---

## 优先级建议

```
快速出洞:  依赖CVE扫描 + Semgrep自定义规则（1-2天）
中等深度:  API边界测试 + Hypothesis Fuzzing（1周）
深度研究:  AFL++二进制Fuzzing + Ghidra逆向（数周）
```
