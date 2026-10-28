# L06-08 — Linux server hardening

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L06-07 — TLS](L06-07-nginx-tls-certificates.md), [L01-13 — SSH](../01-linux-systems/L01-13-ssh-remote-access.md), [L02-10 — Firewall](../02-computer-networking/L02-10-firewalls.md), [L01-18 — Update ও recovery](../01-linux-systems/L01-18-updates-and-recovery.md) |
| **Label** | 🖥️ VM — নিচের পরিবর্তনগুলো শুধু snapshot-যুক্ত VM-এ করুন; SSH config-এর ভুলে নিজেকে lock out করা সম্ভব |
| **Tested** | `harden_audit.py`: ৬টি test পাস (Python 3.14.5, Windows), হাতে তৈরি `sample-root/` tree-তে। Audit **শুধু পড়ে**, কিছু বদলায় না। লেখার সময় Windows-এর path-এ `\` দেখানোর সমস্যা ঠিক করা হয়েছে। আসল Ubuntu server-এ audit ও Section 9.4-এর পরিবর্তন **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Hardening-এর স্তর: আক্রমণের পৃষ্ঠ কমানো (port, service, user), প্রবেশপথ শক্ত করা (SSH), kernel ও network (sysctl, firewall), আপডেট, নজরদারি।
- **SSH:** key-only login, root login বন্ধ, এবং **sshd-এর "প্রথম মান জেতে" নিয়ম** ও cloud-init drop-in-এর ফাঁদ।
- `sysctl`-এর গুরুত্বপূর্ণ মান, ও কেন `ip_forward` কোথাও কোথাও দরকার।
- কোন port কোথায় শুনছে — database কখনো `0.0.0.0`-এ নয়।
- `unattended-upgrades`, `fail2ban`, nginx-এর `limit_req`, `server_tokens`।
- নিরাপদ পরিবর্তনের পদ্ধতি: snapshot, দ্বিতীয় SSH session, `sshd -t`, ধাপে ধাপে।
- Read-only audit tool — "কী বদলাবো" নয়, "কী অবস্থায় আছে" দিয়ে শুরু।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি নতুন public VM চালু করার কয়েক মিনিটের মধ্যেই internet-এর scanner port ২২-এ password অনুমান শুরু করে — `auth.log`-এ হাজার হাজার লাইন।

TaskFlow-এর server-এ এখন আছে nginx, একটি Python app, এবং (পরে) একটি database। প্রতিটি নতুন অংশ একটি সম্ভাব্য প্রবেশপথ:

- ভুলে খোলা database port।
- Password login চালু SSH।
- পুরোনো kernel।
- Version ফাঁস করা error page।

Hardening মানে প্রতিটি অপ্রয়োজনীয় দরজা বন্ধ করা, এবং প্রয়োজনীয়গুলো শক্ত করা — **কিন্তু নিজেকে বাইরে আটকে না রেখে**।

## 3. সহজ ভাষায় পরিচয়

| এলাকা | ন্যূনতম লক্ষ্য | যাচাই |
|---|---|---|
| SSH | `PasswordAuthentication no`, `PermitRootLogin no`, শুধু key | `sudo sshd -T \| grep -E 'password\|rootlogin'` |
| Port | শুধু 22/80/443 বাইরে; DB, metrics শুধু localhost বা VPN | `ss -ltn` |
| Firewall | Default deny incoming | `ufw status verbose` |
| Update | `unattended-upgrades` চালু; reboot-এর পরিকল্পনা | `/etc/apt/apt.conf.d/20auto-upgrades` |
| Kernel/sysctl | Redirect বন্ধ, syncookies, `kptr_restrict`, `dmesg_restrict` | `sysctl -a` |
| User | Root ছাড়া UID 0 নেই; অপ্রয়োজনীয় account বন্ধ | `/etc/passwd` |
| nginx | `server_tokens off`, rate limit, body/timeout সীমা | config |
| Brute-force | `fail2ban` বা key-only (তখন অনুমান অর্থহীন) | `fail2ban-client status` |

```bash
python3 harden_audit.py            # read-only; Ubuntu-তে আসল system
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### একটি দোকানের নিরাপত্তা

- **আক্রমণের পৃষ্ঠ কমানো** = ব্যবহার হয় না এমন পেছনের দরজা স্থায়ীভাবে বন্ধ।
- **SSH key** = চাবি, যা কপি করা কঠিন; password = সংখ্যার তালা, যা অনুমান করা যায়।
- **Firewall** = বাইরের দেয়াল — শুধু সামনের দরজা খোলা।
- **আপডেট** = তালার কোম্পানি দুর্বলতা জানালে তালা বদলানো।
- **Audit** = রাতে একবার ঘুরে দেখা কোন দরজা খোলা রয়ে গেছে।

### Analogy কোথায় মেলে না

- **দরজায় "বন্ধ" লেখা থাকলেই বন্ধ নয়।** sshd-এর config-এ `PasswordAuthentication no` লেখা থাকলেও effective মান `yes` হতে পারে। sshd প্রতিটি keyword-এর **প্রথম** পাওয়া মান নেয়, আর Ubuntu-র `sshd_config`-এর একদম শুরুতে `Include /etc/ssh/sshd_config.d/*.conf`। ফলে cloud-init-এর drop-in-এর `yes` আগে পড়া হয় এবং জেতে (Section 5)। file পড়ে নয়, `sshd -T` বা audit দিয়ে **effective** মান দেখুন।
- **দোকানের দরজা বন্ধ করলে মালিক চাবি দিয়ে ঢোকেন।** Remote server-এ SSH ভুল config করে reload দিলে আপনি নিজেই বাইরে আটকে যেতে পারেন, এবং "চাবি" (console) হয়তো cloud provider-এর web console বা আদৌ নেই। তাই সবসময় একটি পুরোনো session খোলা রেখে পরিবর্তন করুন, আর `sshd -t` দিয়ে যাচাই।
- **একবার তালা লাগালে কাজ শেষ।** Hardening একটি **অবস্থা**, যা সময়ের সাথে ক্ষয়ে যায় — নতুন package নতুন port খোলে, কেউ debug-এর জন্য `0.0.0.0` করে ভুলে যায়। তাই audit নিয়মিত চালাতে হয় (configuration drift — Module 13)।

## 5. Real-world engineering scenario — "Hardening করেছিলাম, তবুও password login চলছিল"

**পরিস্থিতি:** একজন engineer নতুন Ubuntu VM-এর `/etc/ssh/sshd_config`-এ `PasswordAuthentication no` লিখে `systemctl reload ssh` করলেন, এবং ticket বন্ধ করলেন। দুই মাস পরে penetration test-এ দেখা গেল: server-এ password দিয়ে login সম্ভব, এবং একটি দুর্বল password-এর account সত্যিই compromised।

**কারণ:** cloud image-এর cloud-init `/etc/ssh/sshd_config.d/50-cloud-init.conf`-এ `PasswordAuthentication yes` লিখেছিল। Main file-এর প্রথম লাইনের `Include` সেটা আগে পড়ায়, আর sshd-এর নিয়মে প্রথম মান জেতে।

`harden_audit.py` নমুনা tree-তে (হুবহু এই বিন্যাস), আসল output:

```text
ok   sshd     permitrootlogin                        no  ← etc/ssh/sshd_config:4
CRIT sshd     passwordauthentication                 yes  ← etc/ssh/sshd_config.d/50-cloud-init.conf:2
```

মান **কোন file-এর কোন লাইন থেকে এসেছে**, সেটাই মূল তথ্য।

**সমাধান:**

- `/etc/ssh/sshd_config.d/00-hardening.conf`-এ (বর্ণানুক্রমে আগে) `PasswordAuthentication no` ইত্যাদি।
- অথবা cloud-init-এ `ssh_pwauth: false`।
- তারপর `sudo sshd -t && sudo sshd -T | grep passwordauthentication` দিয়ে effective মান যাচাই।

**শিক্ষা:** Configuration file নয়, **চলমান system-এর effective অবস্থা** যাচাই করুন। Hardening ticket বন্ধ হয় audit-এর ফলে, পরিবর্তন লেখায় নয়।

## 6. Diagram — স্তরে স্তরে সুরক্ষা

```text
 internet
   │  ── cloud security group / ufw: শুধু 22, 80, 443 ─────────────────── (L02-10, Module 08)
   ▼
 ┌─ server ───────────────────────────────────────────────────────────────┐
 │ :22  sshd   key-only, no root, MaxAuthTries 3, fail2ban                │
 │ :80/:443 nginx  TLS (L06-07), server_tokens off, limit_req, body/timeouts│
 │        └─► unix socket ─► TaskFlow (unprivileged, systemd sandbox — L06-05)│
 │ 127.0.0.1:5432 postgres (Module 20) — কখনো 0.0.0.0 নয়                    │
 │ kernel: sysctl (redirect বন্ধ, syncookies, kptr/dmesg restrict)          │
 │ OS: unattended-upgrades, AppArmor (L01-17), auditd/journald (L01-14)     │
 └─────────────────────────────────────────────────────────────────────────┘
   ▲
 harden_audit.py — প্রতি রাতে read-only যাচাই → monitoring (exit 0/1/2)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Attack surface | আক্রমণের সম্ভাব্য সব প্রবেশপথ |
| Defense in depth | একাধিক স্বাধীন স্তরের সুরক্ষা |
| Least privilege | প্রয়োজনের ন্যূনতম অনুমতি |
| Effective configuration | চলমান program আসলে যে মান ব্যবহার করছে |
| Drop-in config | `*.d/` directory-র আলাদা file, main config-এর সাথে যুক্ত |
| `sshd -T` | sshd-এর effective config দেখায় |
| `unattended-upgrades` | Security update স্বয়ংক্রিয়ভাবে install |
| `fail2ban` | Log দেখে বারবার ব্যর্থ IP block |
| CIS Benchmark | Hardening-এর প্রচলিত checklist |
| Configuration drift | সময়ের সাথে আসল অবস্থা লক্ষ্য থেকে সরে যাওয়া |
| Break-glass access | জরুরি প্রবেশের বিকল্প পথ (console, আলাদা key) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 sshd-এর config-এর নিয়ম

`man sshd_config` অনুযায়ী, বেশিরভাগ keyword-এর ক্ষেত্রে **প্রথম পাওয়া মান ব্যবহার হয়**। `Include` যেখানে লেখা, সেখানেই file-গুলো (বর্ণানুক্রমে) পড়া হয়।

`Match` block-এর পরের লাইনগুলো শর্তসাপেক্ষ — শুধু মিলে যাওয়া user/address-এ প্রযোজ্য। তাই audit global মান হিসাবে `Match`-এর পরে থামে।

**সবচেয়ে নির্ভরযোগ্য উৎস:** `sudo sshd -T` — sshd নিজে সব নিয়ম মেনে চূড়ান্ত মান দেখায়। `harden_audit.py`-এর sshd অংশ একই নিয়ম অনুকরণ করে, যাতে **কোন file থেকে** মান এসেছে তা দেখানো যায়।

### 8.2 sysctl

`sysctl --system` `/etc/sysctl.conf` ও `/etc/sysctl.d/*.conf` ক্রমানুসারে পড়ে — এখানে **পরের মান জেতে** (sshd-এর উল্টো!)। চলমান মান `/proc/sys/...`-এ।

**গুরুত্বপূর্ণ:**

- `accept_redirects=0`, `send_redirects=0` — ICMP redirect দিয়ে route বদলানো ঠেকানো।
- `rp_filter` — নকল source address।
- `tcp_syncookies=1` — SYN flood।
- `kptr_restrict`, `dmesg_restrict` — kernel-এর তথ্য ফাঁস কমানো।
- `ip_forward=0` — router নয় এমন server-এ। **কিন্তু** Docker, Kubernetes, VPN gateway-তে `1` দরকার। Audit "warning" দেয়, "critical" নয় — প্রসঙ্গ বুঝে সিদ্ধান্ত।

### 8.3 Port ও bind

`ss -ltn`-এর Local Address কলামের `0.0.0.0` বা `[::]` মানে সব interface। Database (5432, 3306, 6379, 27017), Elasticsearch (9200), memcached (11211) এভাবে খোলা থাকলে audit "critical" দেয় — internet-এ এগুলো প্রতিদিন scan ও লুট হয়। Metrics exporter (9100) "warning": firewall থাকলে ঠিক আছে, কিন্তু দেয়ালের ওপর নির্ভর করা ঝুঁকি।

### 8.4 নিরাপদ পরিবর্তনের পদ্ধতি

1. Snapshot (VM) বা backup।
2. **দ্বিতীয় SSH session খোলা রাখুন** — পুরোনো session reload-এ কাটে না।
3. Config বদলান → `sudo sshd -t` (syntax) → `sudo systemctl reload ssh`।
4. **নতুন** terminal থেকে login পরীক্ষা করুন। ব্যর্থ হলে পুরোনো session-এ ফিরিয়ে দিন।
5. Firewall-এ আগে allow, তারপর enable (`ufw allow OpenSSH` → `ufw enable`)।

> **Fedora-তে:** `dnf-automatic` (unattended-upgrades-এর বদলে), `firewalld` (`firewall-cmd`) ufw-এর বদলে, SSH service-এর নাম `sshd` (Ubuntu-তে `ssh`), এবং SELinux enforcing default। `sshd_config.d`-এর Include রীতি একই রকম, তাই Section 5-এর ফাঁদ এখানেও সম্ভব।

## 9. Practical demonstration

Files: [`code/L06-08/harden_audit.py`](code/L06-08/harden_audit.py), [`sample-root/`](code/L06-08/sample-root/etc/ssh/sshd_config) (হাতে তৈরি নমুনা tree — sshd, cloud-init drop-in, sysctl, passwd, apt, nginx, `ss` output), [`test_l06_08.py`](code/L06-08/test_l06_08.py)।

### 9.1 নমুনা tree-তে audit — আসল output

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-08
python3 harden_audit.py --root sample-root; echo "exit=$?"
```

```text
ok   sshd     permitrootlogin                        no  ← etc/ssh/sshd_config:4
CRIT sshd     passwordauthentication                 yes  ← etc/ssh/sshd_config.d/50-cloud-init.conf:2
ok   sshd     kbdinteractiveauthentication           no  ← etc/ssh/sshd_config:6
WARN sshd     x11forwarding                          yes  ← etc/ssh/sshd_config:7
ok   sshd     permitemptypasswords                   no  ← built-in default
WARN sshd     maxauthtries                           6  ← built-in default
…
WARN sysctl   kernel.dmesg_restrict                  not set (want 1; kernel default applies)
WARN sysctl   net.ipv4.ip_forward                    1 (want 0)  ← etc/sysctl.d/99-lab.conf:9
ok   ports    0.0.0.0:22                             expected
CRIT ports    0.0.0.0:5432                           listening on all interfaces — bind to 127.0.0.1 or firewall it
ok   ports    127.0.0.1:8000                         local only
ok   ports    127.0.0.53%lo:53                       local only
WARN ports    [::]:9100                              listening on all interfaces — bind to 127.0.0.1 or firewall it
CRIT users    uid0                                   UID 0 besides root: backup2
ok   updates  unattended-upgrades                    enabled
WARN nginx    server_tokens                          not 'off' — version shown in errors/headers
WARN nginx    limit_req_zone                         no rate limiting (login/API abuse)
summary: 3 critical, 7 warning, 17 ok
exit=2
```

- **তিনটি critical:** password login (cloud-init drop-in), সবার জন্য খোলা PostgreSQL, এবং একটি পুরোনো `backup2` account-এর UID 0 (আসলে দ্বিতীয় root — একটি প্রচলিত backdoor-এর রূপও)।
- **nginx-এর `server_tokens`:** নমুনায় লাইনটি comment-করা (`# server_tokens off;`)। Audit comment বাদ দিয়ে পড়ে, তাই "not off" — চোখে দেখলে মনে হতো আছে।
- **Exit ২** — monitoring-এ CRITICAL (L05-08-এর রীতি)।

### 9.2 লেখার সময়

Windows-এ প্রথম run-এ মানের উৎস দেখাচ্ছিল `etc\ssh\sshd_config.d\50-cloud-init.conf:2` — `Path`-এর OS-নির্ভর separator। Linux path বোঝাতে এখন `as_posix()`। Test-এ এই রূপটি হুবহু যাচাই হয়, তাই Windows-এ ধরা পড়েছে।

একটি সংশোধন প্রথমবার প্রয়োগই হয়নি: heredoc-এর ভেতরে Python string-এ `"\n"` থাকায় shell-এর escaping-এ replace ব্যর্থ হয়েছিল, এবং test সেটা দেখিয়ে দিল — L04-এর শিক্ষা আবার।

### 9.3 আসল Ubuntu-তে audit (চালানো হয়নি)

```bash
python3 harden_audit.py                       # sudo ছাড়াই বেশিরভাগ (sshd_config সাধারণত পড়া যায়)
sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin|kbdinteractiveauthentication|x11forwarding|maxauthtries) '
```

দুটোর মান মিলছে কিনা দেখুন। না মিললে audit-এর অনুকরণে একটি ফাঁক পেয়েছেন — `sshd -T` সবসময় সঠিক।

### 9.4 Hardening-এর পরিবর্তন (🖥️ শুধু VM-এ, snapshot-এর পরে — চালানো হয়নি)

```bash
# ০. দ্বিতীয় SSH session খোলা রাখুন, এবং key-login কাজ করে নিশ্চিত হন
sudo tee /etc/ssh/sshd_config.d/00-hardening.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
X11Forwarding no
MaxAuthTries 3
EOF
sudo sshd -t && sudo systemctl reload ssh       # তারপর নতুন terminal থেকে login পরীক্ষা

sudo ufw default deny incoming && sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
sudo tee /etc/sysctl.d/60-hardening.conf >/dev/null <<'EOF'
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.tcp_syncookies = 1
kernel.kptr_restrict = 1
kernel.dmesg_restrict = 1
EOF
sudo sysctl --system
sudo apt install unattended-upgrades fail2ban && sudo dpkg-reconfigure -plow unattended-upgrades
# nginx: http { server_tokens off; limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s; }
#        location / { limit_req zone=api burst=20 nodelay; … }
python3 harden_audit.py; echo "exit=$?"         # আগে-পরে তুলনা
```

### 9.5 Test

```bash
python3 -m unittest -v
```

৬টি test:

- Include-এর মাধ্যমে প্রথম মান জেতে (file:line সহ)।
- `Match` block global নয়; built-in default।
- sysctl।
- Port-এর শ্রেণি (database critical, `%lo` local)।
- User, update, nginx (comment-করা লাইন গোনা নয়)।
- CLI-এর exit = সবচেয়ে খারাপ।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `sshd_effective` — `setdefault` | প্রথম মান রাখা | sshd-এর নিয়ম |
| Include-এ recursion, অবস্থানেই | Drop-in-এর ক্রম | Section 5 |
| `Match`-এ থামা | শর্তসাপেক্ষ মান global নয় | ভুল OK এড়ানো |
| `SSHD_DEFAULTS` | লেখা না থাকলে built-in মান | `PasswordAuthentication`-এর default `yes`! |
| sysctl — পরের file জেতে | `sysctl --system`-এর ক্রম | sshd-এর উল্টো নিয়ম |
| `live` হলে `/proc/sys` | চলমান মান | File বদলালেও apply না-ও হতে পারে |
| Port-এর শ্রেণি | DB = critical | Internet-এ নিয়মিত লুট |
| `--root` | যেকোনো tree | Test, container image, offline audit |
| Exit = worst | Monitoring | Nightly timer + alert |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `harden_audit.py --root sample-root` | ৩ critical, ৭ warning, exit ২ |
| passwordauthentication-এর উৎস | `50-cloud-init.conf:2` |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `no` লিখলাম, তবুও password login চলে | Drop-in আগে পড়া হয় | `00-*.conf`; `sshd -T` |
| Reload-এর পরে login করা যাচ্ছে না | ভুল config, key নেই | পুরোনো session থেকে ফেরান; console; snapshot |
| `ufw enable`-এর পরে SSH কেটে গেল | 22 allow করার আগে enable | আগে `ufw allow OpenSSH` |
| sysctl বদলালাম, কিছু হয়নি | Apply হয়নি | `sysctl --system`; `/proc/sys` দেখুন |
| Docker-এর পরে network ভাঙল | `ip_forward=0` জোর করে | Container host-এ `1` দরকার |
| `unattended-upgrades`-এর পরে service-এর পুরোনো library | Restart হয়নি | `needrestart`; reboot-এর পরিকল্পনা |
| fail2ban নিজের IP block করেছে | ভুল password পরীক্ষা | `ignoreip`; `fail2ban-client unban` |
| `ss`-এ `0.0.0.0:5432` | Postgres-এর `listen_addresses='*'` | `localhost` (Module 20) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Key-only SSH-এ password brute-force অর্থহীন হয়ে যায় — সবচেয়ে বড় একক জয়।
  - Defense in depth: cloud firewall + host firewall + bind address।
  - Audit-এর ফল নিজেই সংবেদনশীল (কোন দরজা খোলা) — শুধু আপনার monitoring-এ রাখুন।
  - Break-glass পথ নথিভুক্ত রাখুন (console access কার আছে)।
- **Performance:**
  - Hardening-এর বেশিরভাগই খরচহীন।
  - `limit_req` ভুল মানে আসল user-দের 503 দিতে পারে — burst ও log দেখে ঠিক করুন।
  - `fail2ban` বড় log-এ CPU নেয়।
- **Cost:**
  - একটি compromised server-এর খরচ: crypto mining-এর বিল, data breach, পুনর্নির্মাণ।
  - Automation (Ansible — Module 13) দিয়ে hardening পুনরাবৃত্তিযোগ্য করলে প্রতিটি নতুন server-এ হাতে কাজ লাগে না।

## 14. Hands-on exercise

1. Ubuntu VM-এ snapshot নিয়ে Section 9.3 চালান: audit ও `sshd -T` মেলে কি?
2. Section 9.4-এর পরিবর্তন করে আবার audit চালান — critical/warning কত কমল? যা রয়ে গেল, কেন?
3. `harden_audit.py`-এ নতুন check যোগ করুন: `/etc/shadow` পড়া যায় এমন user (root ছাড়া), এবং world-writable file `/etc`-এ।
4. `fail2ban` চালু করে অন্য machine থেকে ৫ বার ভুল password দিন (password login সাময়িকভাবে চালু রেখে, lab VM-এ)। `fail2ban-client status sshd` দেখুন, তারপর unban করুন।
5. Audit-কে systemd timer-এ (দৈনিক) বসিয়ে JSON output `/var/log/harden-audit/`-এ রাখুন, এবং L05-12-এর মতো exit code দিয়ে alert।

## 15. Mini-project — Hardening baseline-as-code

- একটি `baseline.json`: প্রতিটি check-এর প্রত্যাশিত মান ও ব্যতিক্রম (যেমন Docker host-এ `ip_forward=1` ঠিক আছে)।
- `harden_audit.py --baseline baseline.json` শুধু baseline থেকে বিচ্যুতি দেখায়।
- নতুন server-এ প্রথম দিনের ফল ও এক মাস পরের ফলের diff — drift।

Module 13-এ Ansible এই baseline প্রয়োগ করবে, এবং audit যাচাই করবে।

## 16. Interview প্রশ্ন

1. নতুন Linux server-এ প্রথম ৩০ মিনিটে কোন hardening করবেন?
2. SSH config-এ `PasswordAuthentication no` থাকলেও password login কীভাবে চলতে পারে?
3. Remote server-এ SSH config বদলানোর নিরাপদ পদ্ধতি কী?
4. `ss -ltn`-এ `0.0.0.0:6379` দেখলে কী করবেন?
5. Defense in depth বলতে কী বোঝায়? উদাহরণ দিন।
6. Hardening-এর ফল কীভাবে টেকসই রাখবেন (drift)?

## 17. Self-assessment প্রশ্ন

1. দোকানের analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ password login কেন চালু ছিল?
3. sshd ও sysctl-এ "কোন মান জেতে"-র নিয়মে পার্থক্য কী?
4. `ip_forward=1` কেন শুধু warning?
5. নমুনায় `server_tokens` কেন "not off"?

## 18. সংক্ষিপ্ত সারাংশ

- Effective অবস্থা যাচাই করুন (`sshd -T`, `/proc/sys`, `ss`), config file নয়।
- SSH: key-only, no root, `00-*.conf` drop-in; পরিবর্তনে দ্বিতীয় session ও `sshd -t`।
- শুধু 22/80/443 বাইরে; database কখনো `0.0.0.0` নয়; firewall-এ আগে allow, পরে enable।
- sysctl, unattended-upgrades, nginx `server_tokens off` ও rate limit।
- Read-only audit নিয়মিত চালান; hardening একটি অবস্থা, একবারের কাজ নয়।

## 19. Completion checklist

- [ ] নমুনা audit-এর প্রতিটি critical ব্যাখ্যা করতে পারি
- [ ] (VM) Section 9.4 করে audit-এর আগে-পরে তুলনা করেছি, নিজেকে lock out না করে
- [ ] `sshd -T` ও audit-এর মান মিলিয়েছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- OpenBSD/OpenSSH — `sshd_config(5)`: https://man.openbsd.org/sshd_config
- Ubuntu Server documentation — Security: https://documentation.ubuntu.com/server/explanation/intro-to/security/
- Ubuntu — Automatic updates (unattended-upgrades): https://documentation.ubuntu.com/server/how-to/software/automatic-updates/
- Linux kernel — `/proc/sys/net/ipv4/*` (ip-sysctl): https://docs.kernel.org/networking/ip-sysctl.html
- nginx — `ngx_http_limit_req_module`: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- CIS Benchmarks: https://www.cisecurity.org/cis-benchmarks
- Fail2Ban: https://github.com/fail2ban/fail2ban

---

**পরের lesson:** L06-09 — PHP-FPM ও WordPress deployment
