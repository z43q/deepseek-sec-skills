# DeepSeek Security Skills

> 面向 Kali Linux 的 AI 友好安全技能集 — 由 deepseek-tui 驱动

为终端 AI 工作流设计的安全研究技能集合。适用于授权的安全测试和教育研究。

## 简介

本项目提供结构化的安全技能，与 [deepseek-tui](https://github.com/deepseek-ai/deepseek-tui)（终端 AI 交互界面）配合使用。每个技能覆盖安全研究的一个垂直领域，包含可落地的工作流、工具集成和实战命令。

**目标用户：** 安全研究员、渗透测试工程师、SRC 漏洞挖掘者

**环境依赖：**
- Kali Linux（或基于 Debian 的发行版）
- [deepseek-tui](https://github.com/deepseek-ai/deepseek-tui)
- Python 3.11+
- mitmproxy（流量分析类技能需要）

## 技能列表

| 技能 | 说明 |
|------|------|
| **aimitm** | AI 友好 MITM 代理 — 结构化 JSONL 流量输出，支持过滤和请求改包 |
| **web-vuln-hunting** | 定向漏洞挖掘方法论 — 基于 HTTP 响应推理，不依赖扫描器 |
| **web-crawler** | 定向 Web 爬虫，用于侦察和信息收集 |
| **security-learning** | 从公开来源自动采集安全知识 |
| **session-collaboration** | 多会话协作框架，支持团队安全测试分工 |
| **kali-web-pentest** | Kali Web 渗透测试工具速查 |
| **zeroday-hunting** | 0day 漏洞发现路径与模糊测试工作流 |

## 快速上手

### 1. 安装依赖

```bash
# 安装 mitmproxy（流量分析必需）
pip install mitmproxy

# 安装 deepseek-tui
git clone https://github.com/deepseek-ai/deepseek-tui
cd deepseek-tui && ./install.sh
```

### 2. 克隆本项目

```bash
git clone https://github.com/YOUR_USERNAME/deepseek-sec-skills.git
cd deepseek-sec-skills
```

### 3. 加载技能

在 deepseek-tui 中引用技能目录：

```
@skill /path/to/deepseek-sec-skills/skills/aimitm
```

或加载整个技能目录：

```
@skills /path/to/deepseek-sec-skills/skills
```

## 项目结构

```
deepseek-sec-skills/
├── skills/                    # 安全技能文档
│   ├── aimitm/              # MITM 代理插件 + 使用指南
│   ├── web-vuln-hunting/   # 漏洞挖掘方法论
│   │   └── references/      # 工作流与安装指南
│   ├── web-crawler/        # Web 爬虫模板
│   ├── security-learning/  # 知识采集工作流
│   ├── session-collaboration/  # 团队协作框架
│   ├── kali-web-pentest/   # Kali 工具速查
│   └── zeroday-hunting/    # 0day 发现路径
└── tools/                    # 独立工具脚本
    ├── aimitm.py           # mitmproxy 插件
    ├── stealth_pool.py     # 隐蔽代理池
    ├── proxy_pool.py       # 代理池管理器
    ├── crawler_lostfound.py # 丢站爬虫
    ├── whitebox_js.sh      # JS 白盒审计
    └── whitebox_fastapi.sh # FastAPI 白盒审计
```

## 精选技能：aimitm

AI 友好的 MITM 代理，支持结构化 JSONL 输出：

```bash
# 基础用法 — 按主机过滤
aimitm -h target.com

# 仅监控错误响应
aimitm -h target.com -S 400 -n

# 改包 + 文件输出
aimitm -h target.com -r rules.json -o traffic.jsonl
```

JSONL 输出示例：
```json
{"id":1,"ts":"2026-05-20T05:03:05.059Z","method":"GET","url":"https://target.com/api/user?id=1","host":"target.com","status":200}
```

### 请求改包规则

用 JSON 规则实时修改请求：

```json
[
  {
    "match": {"host": "target.com", "path": "/api/login"},
    "modify": {
      "req_headers": {"X-Forwarded-For": "127.0.0.1"},
      "res_body_replace": {"from": "admin", "to": "superadmin"}
    }
  }
]
```

## 精选技能：web-vuln-hunting

系统化漏洞发现方法论，优先挖掘逻辑漏洞而非 CVE 匹配：

```
核心循环：
1. 抓取正常 HTTP 请求 → 浏览器 / MITM 代理
2. 修改参数 → 只改后端会处理的参数
3. 发送 + 读响应 → 状态码 / 错误信息 / 返回数据
4. 推理后端行为 → 从响应中读出处理规则
5. 修正 Payload → 根据推理调整
6. 循环直到触发非预期行为 → 漏洞
```

### 三条铁律

| 规则 | 说明 |
|------|------|
| **只打公开端点** | 没有账号不碰需认证的 API |
| **一次只改一个参数** | 改了多个就不知道是哪个触发的 |
| **响应每行都是线索** | 状态码、错误码、响应长度都有意义 |

### 攻击面优先级

| 优先级 | 功能 | 漏洞类型 |
|:--:|------|---------|
| 1 | 搜索框 | 反射型 XSS、SQL 注入 |
| 2 | 注册 / 找回密码 | 短信轰炸、验证码绕过 |
| 3 | 评论 / 反馈 | 存储型 XSS |
| 4 | 文件上传 | 任意文件上传、路径穿越 |
| 5 | 短链接 / 外部跳转 | Open Redirect |
| 6 | OAuth 回调 | redirect_uri 绕过 |
| 7 | 公开 API | 越权、信息泄露 |

## 工具集

### stealth_pool.py

隐蔽代理轮换，规避 IP 限速：

```python
import stealth_pool

pool = stealth_pool.StealthPool(
    strategy="random",
    check_interval=30,
    rotate_on_block=True
)

pool.add_proxy("http://proxy1:8080")
pool.add_proxy("http://proxy2:8080")

response = pool.request(target_url)
```

### whitebox_js.sh

JS 白盒审计，提取端点和敏感信息：

```bash
./tools/whitebox_js.sh https://target.com/js/app.js
```

提取内容：
- API 端点
- Base URL
- 子域名
- 内网 IP
- 硬编码密钥

## 贡献指南

> *"行动胜于言语。"*
>
> 说实话，我也在学习 — 安全研究和 AI 工程都是。这项目最初只是我的个人笔记，记录我在渗透测试和 SRC 挖坑过程中觉得有用的东西。
>
> 代码不完美，有些技能写得浅，很多事情可能有更好的做法。
>
> **所以我需要你。**
>
> 如果你发现错误、有更聪明的工作流、或者对漏洞挖掘有不同的思路 — 请开 issue 或提交 PR。我真心想向你学习。

### 你可以贡献什么

- **新技能** — 新增安全领域（如移动端、云安全、IoT 破解）
- **完善现有技能** — 更精准的命令、更丰富的工具集成、更清晰的工作流
- **工具脚本** — 打磨 `tools/` 下的边缘工具
- **实战案例** — 分享你用这些技能挖到的漏洞
- **文档优化** — 修错字、翻译、补充示例

### 如何贡献

1. **Fork** 本仓库
2. **创建分支**：`git checkout -b skill/improve-aimitm`
3. **完成修改** — 新增技能、优化文档、改进脚本
4. **本地测试** — 用 deepseek-tui 验证
5. **提交 PR** — 写清楚改了什么、为什么改

### 贡献规范

```
✓ 新增技能？      → 遵循 skills/*/SKILL.md 格式
✓ 改进工作流？    → 提交前先本地测试命令
✓ 修复文档？      → 保持简洁、注重实用
✓ 分享案例？      → 新建 skills/*/CASES.md（不存在则创建）
✗ 不要提交       → 用于未授权访问的工具
✗ 不要删除       → 免责声明或协议头部
```

### 行为准则

尊重他人，专注于实际贡献，不搞对立。

## 免责声明

**本项目仅用于授权的安全测试和教育研究。**

- 测试任何目标前必须获得明确授权
- 禁止对未授权系统使用这些技能
- 在大多数司法管辖区，未经授权访问计算机系统是违法行为
- 作者不对这些工具的滥用承担任何责任

## 许可证

MIT 许可证 — 详见 [LICENSE](LICENSE)
