# Lab 06-B — TaskFlow: nginx → unix socket (systemd) → HTTPS

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ২.৫–৩ ঘণ্টা |
| **Environment** | Ubuntu VM (nginx, systemd, openssl, python3) |
| **Label** | 🖥️ VM — system user, systemd unit, `/etc/nginx` বদলায়; snapshot নিন |
| **Tested** | `check_b.py`-এর offline অংশ Windows-এ যাচাই করা হয়েছে: module-এর `taskflow-tls.conf`-এ ALL PASS, broken ও TLS-হীন config-এ FAIL। একটি vacuous PASS ধরা ও ঠিক করা হয়েছে (TLS server না থাকলেও HSTS check পাস করছিল)। **VM-এ `--live` সহ পুরো lab চালানো হয়নি।** |

## Objective

Module 05-এর TaskFlow-কে production-ধাঁচে চালানো — এটাই Module 06-এর completion criterion "Continuous project Nginx + TLS-এর পেছনে চলা":

```text
client ──HTTPS (lab PKI)──► nginx :443 ──► unix:/run/taskflow/taskflow.sock ──► TaskFlow (systemd socket activation)
        http :80 ── 301 ──┘
```

## Prerequisites

- [L06-04](../../../06-web-server-and-reverse-proxy/L06-04-reverse-proxy-upstream.md), [L06-05](../../../06-web-server-and-reverse-proxy/L06-05-app-process-socket-systemd.md), [L06-07](../../../06-web-server-and-reverse-proxy/L06-07-nginx-tls-certificates.md)
- [L05-13](../../../05-python-for-infrastructure/L05-13-taskflow-api-v01.md)

## Environment setup

```bash
REPO=~/devops-ai-engineering
mkdir -p ~/lab06b
python3 $REPO/06-web-server-and-reverse-proxy/code/L06-07/pki_lab.py create --out ~/lab06b/pki
echo "127.0.0.1 taskflow.example.com" | sudo tee -a /etc/hosts      # শুধু lab VM-এ; cleanup-এ মুছুন
```

File: [`check_b.py`](check_b.py)।

## Steps

### Part 1 — TaskFlow as a systemd service (৪৫ মিনিট)

L06-05-এর Section 9.5 অনুসরণ করুন:

- `taskflow` system user।
- `/opt/taskflow`-এ `taskflow_api.py` ও `taskflow_serve.py`।
- `taskflow.socket` + `taskflow.service`।

যাচাই:

```bash
ls -l /run/taskflow/taskflow.sock                 # srw-rw---- taskflow www-data
sudo -u www-data curl -s --unix-socket /run/taskflow/taskflow.sock http://x/health
python3 $REPO/06-web-server-and-reverse-proxy/code/L06-05/socket_check.py /run/taskflow/taskflow.sock --user www-data
```

### Part 2 — nginx reverse proxy (৪৫ মিনিট)

L06-07-এর `taskflow-tls.conf` থেকে শুরু করে নিজের `/etc/nginx/sites-available/taskflow.conf` লিখুন:

- Certificate: `/etc/nginx/tls/fullchain.pem` ও `/etc/nginx/tls/server.key` (`~/lab06b/pki` থেকে; key `0600`, owner root)।
- ACME location লাগবে না (lab PKI) — কিন্তু redirect রাখুন।

```bash
python3 check_b.py /etc/nginx/sites-available/taskflow.conf      # offline — ALL PASS হওয়া পর্যন্ত ঠিক করুন
sudo ln -s /etc/nginx/sites-available/taskflow.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Part 3 — যাচাই ও পরিমাপ (৩০ মিনিট)

```bash
python3 check_b.py /etc/nginx/sites-available/taskflow.conf --live --cafile ~/lab06b/pki/root.crt
curl -s --cacert ~/lab06b/pki/root.crt https://taskflow.example.com/tasks | head -c 200; echo
tail -3 /var/log/nginx/access.log
```

L06-04-এর `upstream_timing` log format যোগ করে `urt`/`uct` দেখুন। Keepalive কাজ করছে কিনা (`uct` প্রায় ০)?

### Part 4 — restart-এর সময় কোনো ব্যর্থতা নয় (২০ মিনিট)

```bash
( for i in $(seq 1 100); do curl -s -o /dev/null -w '%{http_code} ' --cacert ~/lab06b/pki/root.crt \
    https://taskflow.example.com/health; sleep 0.05; done; echo ) &
sudo systemctl restart taskflow.service; wait
```

সব 200 এলো? Socket activation না থাকলে (L06-05 exercise ২) কী হতো?

## Expected behavior

- `check_b.py --live`: সব PASS।
- `http://` → 301 `https://…`।
- App শুধু unix socket-এ — `127.0.0.1:8000`-এ কিছু নেই।
- Restart-এ ১০০টির মধ্যে ০টি non-200।

## Verification

```bash
python3 check_b.py /etc/nginx/sites-available/taskflow.conf --live --cafile ~/lab06b/pki/root.crt; echo "exit=$?"
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ | Lesson |
|---|---|---|
| 502, `(13: Permission denied)` | Socket-এর group/mode বা path-এর directory | L06-05 (`socket_check.py`) |
| 502, `(2: No such file)` | Socket path অমিল, socket unit চালু নয় | L06-05 |
| `unable to get local issuer certificate` | `ssl_certificate`-এ শুধু leaf | L06-07 |
| `nginx -t`: `key values mismatch` | Chain-এর ক্রম বা ভুল key | L06-07 |
| App-এ Host/IP ভুল | `proxy_set_header` inheritance | L06-04 |
| Restart-এ কিছু 502 | Socket activation নয় | L06-05 |

L06-04-এর `error_explainer.py`-তে `sudo tail -20 /var/log/nginx/error.log` পাঠান।

## Cleanup / reset

```bash
sudo rm -f /etc/nginx/sites-enabled/taskflow.conf /etc/nginx/sites-available/taskflow.conf
sudo rm -rf /etc/nginx/tls && sudo nginx -t && sudo systemctl reload nginx
sudo systemctl disable --now taskflow.socket taskflow.service
sudo rm -f /etc/systemd/system/taskflow.socket /etc/systemd/system/taskflow.service && sudo systemctl daemon-reload
sudo sed -i '/^127.0.0.1 taskflow.example.com$/d' /etc/hosts
rm -rf ~/lab06b                                    # lab PKI-র key সহ
```

## Assessment

1. একটি request-এর পুরো পথ আঁকুন: DNS (`/etc/hosts`) → TLS → server block → location → upstream → socket → process।
2. Part 3-এ `urt`, `uct`, `rt`-এর মান কত? কোনটি nginx-এর নিজের সময়?
3. Part 4-এর ফল ব্যাখ্যা করুন। Socket activation কীভাবে zero-downtime দিল?
4. Lab PKI-এর বদলে আসল domain-এ Let's Encrypt ব্যবহার করলে কী কী বদলাত (ACME location, renewal, monitoring)?
