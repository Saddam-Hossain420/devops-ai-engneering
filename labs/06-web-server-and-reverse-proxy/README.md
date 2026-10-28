# Module 06 Labs — Web Server and Reverse Proxy

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — Static site ও server block](A-static-site-server-blocks/README.md) | A — Fundamentals | দুটি site + catch-all `default_server` (444) + hidden-file deny; আগে `server_select.py`-তে অনুমান, পরে আসল nginx | ৬০ মিনিট | L06-02, L06-03 |
| [B — TaskFlow: nginx → unix socket → HTTPS](B-taskflow-behind-nginx-tls/README.md) | B — Integrated | systemd socket activation, reverse proxy, lab PKI-তে TLS, HSTS/redirect, restart-এ zero failure | ২.৫–৩ ঘণ্টা | L06-04 – L06-07, L05-13 |
| [C — Upstream, socket ও certificate](C-proxy-socket-cert-failures/README.md) | C — Failure and Recovery | মেয়াদোত্তীর্ণ certificate → ভুল socket নাম (502/2) → socket permission (502/13) — একটির পর একটি | ৬০–৯০ মিনিট | L06-04, L06-05, L06-07 |

**Environment:**

- তিনটি lab-ই Ubuntu VM-এ (nginx, systemd)। Snapshot নিন।
- Lab A ও B-এর checker-এর **offline** অংশ (config lint) যেকোনো OS-এ চলে, এবং Windows-এ যাচাই করা হয়েছে।
- `--live` অংশ ও Lab C-এর break → fix → check **VM-এ চালানো হয়নি**।

**Module 06-এর completion criteria:**

- "Continuous project Nginx + TLS-এর পেছনে চলা" → Lab B।
- "ভুল proxy config থেকে আসা error diagnose" → Lab C ও L06-04-এর `error_explainer.py`।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [06-web-server-and-reverse-proxy/PROGRESS.md](../../06-web-server-and-reverse-proxy/PROGRESS.md)-এর Module assessment table আপডেট করুন।
