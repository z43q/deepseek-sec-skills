# DeepSeek Security Skills [简体中文](README_zh.md)
> AI-friendly security skills for Kali Linux — powered by deepseek-tui

A curated collection of security research skills designed for terminal-based AI workflows. Built for ethical hacking and authorized security testing.

## Overview

This project provides structured security skills that work with [deepseek-tui](https://github.com/Hmbown/DeepSeek-TUI), a terminal-based AI interface. Each skill covers a specific domain of security research with practical workflows, tool integrations, and actionable commands.

**Target Users:** Security researchers, penetration testers, bug bounty hunters

**Requirements:**
- Kali Linux (or Debian-based distribution)
- [deepseek-tui](https://github.com/Hmbown/DeepSeek-TUI)
- Python 3.11+
- mitmproxy (for traffic analysis skills)

## Skills

| Skill | Description |
|-------|-------------|
| **aimitm** | AI-friendly MITM proxy — structured JSONL traffic output with filtering and request modification |
| **web-vuln-hunting** | Targeted vulnerability hunting methodology — HTTP response inference, not scanner-based |
| **web-crawler** | Directed web crawler for reconnaissance and data collection |
| **security-learning** | Automated security knowledge gathering from public sources |
| **session-collaboration** | Multi-session collaboration framework for team-based security testing |
| **kali-web-pentest** | Kali web penetration testing tools quick reference |
| **zeroday-hunting** | 0day vulnerability discovery paths and fuzzing workflows |


## Project Structure

```
deepseek-sec-skills/
├── skills/                    # Security skill documents
│   ├── aimitm/              # MITM proxy addon + usage guide
│   ├── web-vuln-hunting/   # Vulnerability hunting methodology
│   │   └── references/      # Workflow & installation guides
│   ├── web-crawler/        # Web crawler templates
│   ├── security-learning/  # Knowledge gathering workflows
│   ├── session-collaboration/  # Team collaboration framework
│   ├── kali-web-pentest/   # Kali tools reference
│   └── zeroday-hunting/    # 0day discovery paths
└── tools/                    # Standalone utility scripts
    ├── aimitm.py           # mitmproxy addon
    ├── stealth_pool.py     # Stealth proxy pool
    ├── proxy_pool.py       # Proxy pool manager
    ├── crawler_lostfound.py # Lost-and-found crawler
    ├── whitebox_js.sh      # JS whitebox audit
    └── whitebox_fastapi.sh # FastAPI whitebox audit
```

## Featured Skill: aimitm

AI-friendly MITM proxy with structured JSONL output:

```bash
# Basic usage — filter by host
aimitm -h target.com

# Watch error responses only
aimitm -h target.com -S 400 -n

# Request modification + file output
aimitm -h target.com -r rules.json -o traffic.jsonl
```

Sample JSONL output:
```json
{"id":1,"ts":"2026-05-20T05:03:05.059Z","method":"GET","url":"https://target.com/api/user?id=1","host":"target.com","status":200}
```

### Request Modification Rules

Modify requests on-the-fly with JSON rules:

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

## Featured Skill: web-vuln-hunting

A systematic approach to vulnerability discovery that prioritizes logic flaws over CVE matching:

```
Core Loop:
1. Capture normal HTTP request → browser / MITM proxy
2. Modify parameters → only parameters processed by backend
3. Send + read response → status code / error message / data
4. Infer backend behavior → read processing rules from response
5. Refine payload → adjust based on inference
6. Loop until unexpected behavior → vulnerability
```

### Three Rules of Engagement

| Rule | Description |
|------|-------------|
| **Public endpoints only** | Don't touch authenticated APIs without an account |
| **One parameter at a time** | Modify multiple = don't know which one triggered |
| **Every response line is a clue** | Status code, error codes, response length all matter |

### Attack Surface Priority

| Priority | Feature | Vulnerability Type |
|:--:|---------|---------------------|
| 1 | Search box | Reflected XSS, SQL injection |
| 2 | Register / Password reset | SMS bombing, CAPTCHA bypass |
| 3 | Comments / Feedback | Stored XSS |
| 4 | File upload | Arbitrary upload, path traversal |
| 5 | Short links / Redirects | Open redirect |
| 6 | OAuth callback | redirect_uri bypass |
| 7 | Public API | IDOR, information disclosure |

## Tools

### stealth_pool.py

Stealth proxy rotation for evading IP-based rate limiting:

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

Whitebox JavaScript audit for endpoint and secret extraction:

```bash
./tools/whitebox_js.sh https://target.com/js/app.js
```

Extracts:
- API endpoints
- Base URLs
- Subdomains
- Internal IPs
- Hardcoded secrets

## Contributing

> *"Actions speak louder than words."*
>
> To be honest, I'm still learning — both security research and AI engineering. This project started as my personal notebook, a collection of things I found useful while grinding through penetration testing and bug bounty.
>
> The code isn't perfect. Some skills are shallow. There are probably better ways to do many things.
>
> **That's where you come in.**
>
> If you spot a mistake, know a smarter workflow, or have a different angle on vulnerability hunting — please open an issue or submit a PR. I genuinely want to learn from you.

### What You Can Contribute

- **New skills** — Add a new security domain (e.g., mobile pentest, cloud security, IoT hacking)
- **Improve existing skills** — Better commands, more tool integrations, clearer workflows
- **Tool scripts** — Sharpen the edge tools under `tools/`
- **Real-world case studies** — Share your bug bounty wins using these skills
- **Documentation** — Fix typos, improve translations, add examples

### How to Contribute

1. **Fork** this repo
2. **Create a branch** for your changes: `git checkout -b skill/improve-aimitm`
3. **Make your changes** — add skills, improve docs, or polish scripts
4. **Test locally** with deepseek-tui
5. **Open a Pull Request** with a clear description of what changed and why

### Contribution Guidelines

```
✓ Adding a new skill?     → Follow the skills/*/SKILL.md format
✓ Improving a workflow?   → Test commands before submitting
✓ Fixing documentation?   → Keep it concise and practical
✓ Sharing a case study?   → Add it to skills/*/CASES.md (create if not exists)
✗ Don't submit          → Tools for unauthorized access
✗ Don't remove          → Disclaimer or license headers
```

### Code of Conduct

Be respectful. Focus on practical contributions. No drama.

## Disclaimer

**This project is for authorized security testing and educational purposes only.**

- Always obtain explicit permission before testing any target
- Do not use these skills against systems without proper authorization
- Unauthorized access to computer systems is illegal in most jurisdictions
- The authors are not responsible for misuse of these tools

## License

MIT License — see [LICENSE](LICENSE) for details.
