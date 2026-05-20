---
name: session-collaboration
description: 多会话协作 Skill — 多个安全测试会话间的身份协作、任务分配、工作交接。
metadata:
  short-description: 安全测试多会话协作框架
---

# 多会话协作 Skill

多个测试会话间的角色分工与工作交接。

---

## 角色定义

### Scout (侦察引擎)

```
身份: [scout]
任务: 资产发现、JS下载、API枚举、DNS/端口扫描
产出: 资产清单、JS dump、API列表
```

### Hunter (漏洞猎人)

```
身份: [hunter]
任务: 逐端点漏洞测试、PoC验证、报告撰写
产出: 漏洞确认清单、curl复现命令、提交报告
```

### Researcher (CVE研究员)

```
身份: [researcher]
任务: Nday/CVE匹配、公开exp搜索、0day挖掘
产出: CVE命中列表、exploit测试结果
```

---

## 发言格式

每次指令开头标注身份和接收方：

```
[身份 → 接收方] 内容
```

示例：
```
[scout → hunter]  JS已下载完成, 你可以开始分析
[hunter → scout] 已确认目标端点, 需要你补测子域
[scout → ALL]    资产测绘完成, 14域/96资产
```

---

## 工作模板

### 启动新目标

```
[scout → ALL]
新目标: {厂商名}
1. 我来做资产测绘 (DNS/端口/JS)
2. hunter 准备漏洞检查清单
3. researcher 查已知CVE
预计: 30分钟
```

### 侦察完成

```
[scout → hunter]
资产就绪:
- 域: X个 / IP: X个
- API端点: X个
- JS文件: X个/XMB
请接管
```

### 漏洞确认

```
[hunter → researcher]
已确认:
- VULN-001: 验证码可爆破
- VULN-002: 邮件无频率限制
请查Nday/CVE匹配
```

### 并行工作

```
[scout → ALL]
A线: {目标A} (hunter正在打, 勿动)
B线: {目标B} (我开侦察)
两线独立
```

---

## 规则

1. 同一目标同一时间只由一个会话负责
2. 发现高危漏洞立即 `[→ ALL]` 通知
3. 报告最终版以 curl 最小复现 + CVSS + 修复建议格式提交
4. 提交时始终使用白帽格式
