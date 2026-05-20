# 工具安装指南

> 环境：Kali Linux / Debian / Ubuntu
> 维护：安装后可通过系统包管理器或 pip 更新

## 一键安装

```bash
#!/bin/bash
# 保存为 install.sh，执行 bash install.sh

echo "[*] 更新系统包"
sudo apt update

echo "[*] 信息收集工具"
sudo apt install -y whatweb nmap gobuster ffuf dirb dnsrecon amass sublist3r theHarvester wafw00f

echo "[*] Web 应用分析"
sudo apt install -y burpsuite sqlmap xsstrike commix wpscan nikto nuclei zaproxy

echo "[*] 页面渲染与 OCR"
sudo apt install -y chromium tesseract-ocr tesseract-ocr-chi-sim

echo "[*] WebSocket"
sudo apt install -y websocat

echo "[*] Python 依赖"
pip install mitmproxy scrapy playwright semgrep bandit hypothesis requests

echo "[*] 安装 Playwright 浏览器"
playwright install chromium

echo "[*] 反序列化工具"
# ysoserial 需从 GitHub 下载
wget -q https://github.com/frohoff/ysoserial/releases/download/v0.0.6/ysoserial-all.jar -O ~/tools/ysoserial.jar 2>/dev/null

echo "[✓] 安装完成"
```

## 分步安装

### 信息收集

| 工具 | 安装命令 | 验证 |
|------|---------|------|
| whatweb | `sudo apt install -y whatweb` | `whatweb --version` |
| nmap | `sudo apt install -y nmap` | `nmap --version` |
| gobuster | `sudo apt install -y gobuster` | `gobuster --help` |
| ffuf | `sudo apt install -y ffuf` | `ffuf -V` |
| dirb | `sudo apt install -y dirb` | `dirb` |
| dnsrecon | `sudo apt install -y dnsrecon` | `dnsrecon -h` |
| amass | `sudo apt install -y amass` | `amass -version` |
| sublist3r | `sudo apt install -y sublist3r` | `sublist3r -h` |
| theHarvester | `sudo apt install -y theHarvester` | `theHarvester -h` |
| wafw00f | `sudo apt install -y wafw00f` | `wafw00f --help` |

### Web 应用分析

| 工具 | 安装命令 | 验证 |
|------|---------|------|
| burpsuite | `sudo apt install -y burpsuite` | `burpsuite --version` |
| sqlmap | `sudo apt install -y sqlmap` | `sqlmap --version` |
| xsstrike | `sudo apt install -y xsstrike` | `xsstrike -h` |
| commix | `sudo apt install -y commix` | `commix -h` |
| wpscan | `sudo apt install -y wpscan` | `wpscan --version` |
| nikto | `sudo apt install -y nikto` | `nikto -Version` |
| nuclei | `sudo apt install -y nuclei` | `nuclei -version` |

### 页面渲染与 OCR（必装）

```bash
sudo apt install -y chromium tesseract-ocr tesseract-ocr-chi-sim
```

验证：
```bash
chromium --version
tesseract --list-langs | grep chi_sim
```

### mitmproxy（代理抓包）

```bash
pip install mitmproxy
mitmdump --version
```

**首次配置 CA 证书**：
```bash
# 1. 启动代理
mitmdump -p 8080

# 2. 浏览器设代理 127.0.0.1:8080，访问 http://mitm.it/
# 3. 下载对应平台的 CA 证书并信任

# 4. Chromium 跳过证书验证（备选）
chromium --ignore-certificate-errors --proxy-server="http://127.0.0.1:8080"
```

### WebSocket 测试

```bash
sudo apt install -y websocat
websocat --version
```

### 爬虫（Scrapy + Playwright）

```bash
pip install scrapy playwright
playwright install chromium
```

验证：
```bash
python3 -c "import scrapy; print(scrapy.__version__)"
python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### SAST / 白盒审计

```bash
pip install semgrep bandit
semgrep --version
bandit --version
```

### 反序列化利用

```bash
# 下载 ysoserial（Java 反序列化 payload 生成器）
wget https://github.com/frohoff/ysoserial/releases/download/v0.0.6/ysoserial-all.jar -O ~/tools/ysoserial.jar

# 列出可用 payload
java -jar ~/tools/ysoserial.jar
```

## 字典库

```bash
# 系统自带
ls /usr/share/wordlists/
ls /usr/share/dirb/wordlists/

# 可选：下载 SecLists
git clone https://github.com/danielmiessler/SecLists.git ~/tools/SecLists

# 可选：下载 PayloadsAllTheThings
git clone https://github.com/swisskyrepo/PayloadsAllTheThings.git ~/tools/PayloadsAllTheThings
```

## 代理池

```bash
pip install requests
# 代理池脚本见配套工具包
python3 proxy_pool.py --test
```

## 环境检查

安装完成后运行以下命令确认所有工具可用：

```bash
echo "=== 信息收集 ===" && whatweb --version && nmap --version && gobuster --help > /dev/null && echo "gobuster OK"
echo "=== Web分析 ===" && sqlmap --version && nuclei -version && echo "nikto OK"
echo "=== 渲染 ===" && chromium --version && tesseract --version
echo "=== 代理 ===" && mitmdump --version
echo "=== 爬虫 ===" && python3 -c "import scrapy; print('scrapy', scrapy.__version__)"
echo "=== SAST ===" && semgrep --version
echo "[✓] 全部检查通过"
```
