# L01-10 — systemd: unit, service, target ও journald

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-09 — CPU, memory ও OOM](L01-09-cpu-memory-oom.md) |
| **Label** | 🖥️ VM (systemd PID 1 দরকার) · ⚠️ service install system বদলায় — cleanup ধাপ আছে |
| **Tested** | ৭টি unit test পাস (Python 3.14, Windows; ResourceWarning-কে error ধরে)। `unit_lint.py` চালানো; test-এ continuation লাইনের একটি bug ধরা পড়ে ঠিক হয়েছে। `hello_service.py` Windows-এ চালিয়ে `curl` দিয়ে `/health` ও `/` যাচাই করা হয়েছে। **systemctl, journalctl, systemd-analyze ও service install Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- **systemd** কী, কেন PID 1, এবং **unit** কী (service, socket, timer, target, mount)।
- Service unit file-এর গঠন: `[Unit]`, `[Service]`, `[Install]`।
- `systemctl` দিয়ে start, stop, restart, reload, enable, status; dependency ও ordering।
- **Restart policy**, resource limit (`MemoryMax=`) ও **sandboxing/hardening**।
- **journald** — log কোথায় যায়, `journalctl` দিয়ে filter।
- **Target** ও boot প্রক্রিয়া।
- নিজের Python HTTP service-কে production-style systemd service হিসেবে চালানো।
- Python দিয়ে unit file lint।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L00-07-এ বলা continuous project-এর v0.3 ধাপের সমস্যা: `python3 app.py` terminal-এ চালালে —

- Terminal বন্ধ = app বন্ধ (SIGHUP, L01-08)।
- Crash করলে কেউ আবার চালু করে না।
- Server reboot-এর পরে app চালু হয় না।
- Log terminal-এ — হারিয়ে যায়।
- App root হিসেবে বা আপনার user হিসেবে চলে — অতিরিক্ত অধিকার।
- Memory leak হলে পুরো server ডুবে যায়।

**systemd** সব একসাথে সমাধান করে: process supervision, auto-restart, boot-এ চালু, log সংগ্রহ, user পরিবর্তন, resource limit ও sandbox — একটি ছোট configuration file দিয়ে। Ubuntu ও Fedora দুটোতেই systemd হলো init system — তাই এই দক্ষতা প্রায় সব আধুনিক Linux server-এ কাজে লাগে।

## 3. সহজ ভাষায় পরিচয়

**systemd** = Linux-এর **PID 1** — kernel boot-এর পরে প্রথম চালু হওয়া user-space process। এর কাজ: বাকি সব service চালু করা, তাদের দেখাশোনা করা, orphan process reap করা (L01-08), এবং shutdown-এ সুশৃঙ্খলভাবে সব বন্ধ করা।

**Unit** = systemd যা পরিচালনা করে তার একটি একক, একটি configuration file দিয়ে বর্ণিত:

| Unit type | উদাহরণ | কী |
|---|---|---|
| `.service` | `nginx.service` | একটি daemon বা কাজ |
| `.socket` | `ssh.socket` | একটি socket, connection এলে service চালু |
| `.timer` | `apt-daily.timer` | নির্দিষ্ট সময়ে service চালানো (L01-11) |
| `.target` | `multi-user.target` | কয়েকটি unit-এর গ্রুপ — "অবস্থা" (যেমন network প্রস্তুত) |
| `.mount` | `boot.mount` | Filesystem mount (`/etc/fstab` থেকে তৈরি হয়) |
| `.slice` | `user.slice` | cgroup-এর resource ভাগ |

**Unit file কোথায়:**

| Path | কে লেখে | অগ্রাধিকার |
|---|---|---|
| `/usr/lib/systemd/system/` (Ubuntu-তে `/lib/systemd/system/` একই জায়গা) | Package | নিম্ন — হাত দেবেন না |
| `/etc/systemd/system/` | Admin (আপনি) | উচ্চ — এখানে লিখুন বা override |
| `/run/systemd/system/` | Runtime | অস্থায়ী |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের নার্সিং সুপারভাইজার

- **systemd** = নার্সিং সুপারভাইজার, যিনি শিফট শুরুর সময় (boot) সঠিক ক্রমে সব বিভাগ চালু করেন: আগে বিদ্যুৎ ও পানি (network, filesystem), তারপর রোগী ভর্তি (application)।
- **Unit file** = প্রতিটি বিভাগের লিখিত নির্দেশিকা: কে চালাবে (`User=`), কীভাবে শুরু (`ExecStart=`), কার আগে/পরে (`After=`), অসুস্থ হলে কী (`Restart=`), কতটা resource (`MemoryMax=`)।
- **journald** = কেন্দ্রীয় রেজিস্টার, যেখানে প্রতিটি বিভাগের প্রতিটি ঘটনা সময়সহ লেখা হয়।
- **Target** = "ICU প্রস্তুত", "জরুরি বিভাগ প্রস্তুত" — কয়েকটি বিভাগ মিলে একটি অবস্থা।

### Analogy কোথায় মেলে না

- সুপারভাইজার বিবেচনা করে ক্রম বদলান। systemd **dependency graph** থেকে যান্ত্রিকভাবে ক্রম বের করে এবং যা সম্ভব **একসাথে** (parallel) চালু করে — তাই boot দ্রুত। ভুল `After=`/`Requires=` দিলে ক্রম ভুল হয়, systemd "বুঝে নেয় না"।
- নার্স অসুস্থ হলে সুপারভাইজার কারণ খোঁজেন। `Restart=on-failure` শুধু আবার চালু করে — কারণ খোঁজে না। বারবার crash হলে systemd একটি সীমার পরে হাল ছেড়ে দেয় (start limit) — আপনাকে journal পড়ে কারণ খুঁজতে হবে।
- রেজিস্টার কাগজে চিরকাল থাকে। journald-এর log default-ভাবে আকারে সীমিত, এবং কিছু configuration-এ reboot-এ মুছে যায় (Section 8.4)।

## 5. Real-world engineering scenario — "reboot-এর পরে site down"

**পরিস্থিতি:** Kernel security update-এর পরে রাতে automatic reboot। সকালে site down। App server-এ `ps`-এ app process নেই।

**Diagnosis:**

```bash
systemctl status taskflow
```

উদাহরণ output:

```text
○ taskflow.service - TaskFlow API
     Loaded: loaded (/etc/systemd/system/taskflow.service; disabled; preset: enabled)
     Active: inactive (dead)
```

**`disabled`** — কেউ `systemctl start` করেছিলেন কিন্তু `enable` করেননি। `start` = এখন চালাও; `enable` = boot-এ চালাও। দুটো আলাদা।

**দ্বিতীয় ধরন (অন্য দিন):** enabled, তবু ব্যর্থ:

```text
× taskflow.service - TaskFlow API
     Active: failed (Result: exit-code)
    Process: 812 ExecStart=/usr/bin/python3 /opt/taskflow/app.py (code=exited, status=1/FAILURE)
```

```bash
journalctl -u taskflow -b --no-pager | tail -20
```

→ `could not connect to database at 10.0.0.5:5432` — app database-এর আগে চালু হয়েছে, network তখনো প্রস্তুত ছিল না, এবং `Restart=` ছিল না বলে আর চেষ্টা করেনি।

**সমাধান:** `systemctl enable`; `After=network-online.target` + `Wants=network-online.target`; `Restart=on-failure` ও `RestartSec=`; এবং app-কে startup-এ dependency-র জন্য retry করতে শেখানো (Module 05)।

**শিক্ষা:** "চালু আছে" আর "reboot-এর পরেও চালু থাকবে" আলাদা। প্রতিটি deploy-এর পরে একবার reboot test (VM-এ) সস্তা বীমা।

## 6. Diagram

### Boot ও target

```text
 firmware ─► bootloader (GRUB) ─► kernel ─► systemd (PID 1)
                                               │
          sysinit.target  (filesystem, swap, udev)
                 │
          basic.target
                 │
          network.target ─── network-online.target (সত্যিই connectivity আছে)
                 │
          multi-user.target  ◄── সাধারণ server (text mode); আপনার service WantedBy=এখানে
                 │
          graphical.target   ◄── desktop
```

### Service lifecycle

```text
 systemctl start ─► activating ─► active (running) ──► process crash
        ▲                               │                    │ Restart=on-failure
        │                               │ systemctl stop     ▼
        │                               ▼               activating (RestartSec পরে)
        │                         deactivating:              │ বারবার? StartLimitBurst ছাড়ালে
        │                     SIGTERM ─(TimeoutStopSec)─► SIGKILL      ▼
        │                               │                         failed
        └──────── inactive (dead) ◄─────┘
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| systemd | Linux-এর init system ও service manager (PID 1) |
| Unit | systemd-পরিচালিত বস্তু (service, timer, target ...) |
| `systemctl` | systemd নিয়ন্ত্রণের command |
| `journald` / `journalctl` | systemd-এর log service / log পড়ার command |
| `ExecStart=` | Service চালানোর command (absolute path) |
| `Type=` | Process "প্রস্তুত" কখন: `simple`, `exec`, `notify`, `forking`, `oneshot` |
| `Restart=` | কখন আবার চালু: `no`, `on-failure`, `always` ... |
| `After=` / `Before=` | শুধু **ক্রম** — নির্ভরতা নয় |
| `Wants=` / `Requires=` | **নির্ভরতা** — সাথে চালু করো (Requires: সেটি ব্যর্থ হলে এটিও) |
| `WantedBy=` | `enable` করলে কোন target-এর সাথে চালু হবে |
| `daemon-reload` | Unit file বদলানোর পরে systemd-কে আবার পড়তে বলা |
| Drop-in / override | `/etc/systemd/system/X.service.d/*.conf` — মূল file না বদলে অংশবিশেষ বদলানো |
| Sandboxing | `ProtectSystem=`, `PrivateTmp=` ইত্যাদি দিয়ে service-এর অধিকার সীমিত |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 systemd service চালায় কীভাবে

1. Unit-এর জন্য একটি **cgroup** তৈরি (L01-09) — সব child process সেখানে থাকে; তাই `stop` করলে সব child-ও বন্ধ হয় (`KillMode=control-group` default)।
2. `User=`, `Group=`, `WorkingDirectory=`, `Environment=`, `UMask=`, সীমা ও sandbox প্রয়োগ।
3. `ExecStart` চালায়; stdout/stderr journald-এ যুক্ত।
4. Main process দেখাশোনা করে; মরলে `Restart=` অনুযায়ী সিদ্ধান্ত।
5. `stop`-এ `KillSignal=` (default SIGTERM) → `TimeoutStopSec=` অপেক্ষা → SIGKILL (L01-08)।

### 8.2 `Type=` কেন গুরুত্বপূর্ণ

- `simple` (default): process চালু হলেই "active" — আসলে প্রস্তুত না হলেও। আধুনিক app-এর জন্য সাধারণত ঠিক।
- `exec`: `execve` সফল হলে active — binary না পেলে `start` সঙ্গে সঙ্গে ব্যর্থ দেখায় (simple-এর চেয়ে স্পষ্ট)।
- `notify`: app নিজে `sd_notify("READY=1")` পাঠালে active — সবচেয়ে সঠিক, app-এর সমর্থন লাগে।
- `forking`: পুরোনো daemon যারা নিজেরা background-এ যায় — `PIDFile=` দরকার।
- `oneshot`: একবার চলে শেষ হয় (script) — timer-এর সাথে (L01-11)।

### 8.3 Hardening option (এই lesson-এর unit-এ ব্যবহৃত)

| Option | কী করে |
|---|---|
| `User=taskflow` | Root নয়, নিজস্ব system user |
| `NoNewPrivileges=true` | setuid দিয়ে অধিকার বাড়ানো বন্ধ (L01-04) |
| `PrivateTmp=true` | নিজস্ব `/tmp` — symlink attack ও data ফাঁস কমায় |
| `ProtectSystem=strict` | পুরো filesystem read-only, শুধু নির্দিষ্ট জায়গা লেখা যায় (`ReadWritePaths=`, `StateDirectory=`) |
| `ProtectHome=true` | `/home`, `/root` অদৃশ্য |
| `ProtectKernelTunables=true` | `/proc/sys` ইত্যাদি read-only |
| `RestrictAddressFamilies=` | শুধু অনুমোদিত socket ধরন |
| `MemoryMax=`, `CPUQuota=` | cgroup সীমা (L01-09) |

`systemd-analyze security <unit>` প্রতিটি service-এর একটি "exposure" score দেয় — hardening-এর অগ্রগতি মাপতে।

### 8.4 journald

- Service-এর stdout/stderr, kernel log, syslog — সব structured আকারে (প্রতিটি entry-তে unit, PID, priority, boot ID ইত্যাদি field)।
- Storage: `/var/log/journal/` থাকলে স্থায়ী, না থাকলে `/run/log/journal/` (reboot-এ মুছে)। Ubuntu 24.04 ও Fedora-তে সাধারণত স্থায়ী।
- আকারের সীমা `/etc/systemd/journald.conf` (`SystemMaxUse=`)।
- Application-এর উচিত **stdout-এ log** করা (Twelve-Factor) — নিজে file ও rotation সামলাতে না হয়; এই lesson-এর `hello_service.py` তাই করে, এবং timestamp যোগ করে না কারণ journald নিজেই যোগ করে।

## 9. Practical demonstration (Ubuntu VM — systemd PID 1)

### 9.1 পর্যবেক্ষণ (read-only)

```bash
systemctl status                         # সামগ্রিক অবস্থা
systemctl list-units --type=service --state=running
systemctl --failed                       # ব্যর্থ unit
systemctl cat ssh                        # একটি unit-এর file (Fedora-তে: sshd)
systemctl list-dependencies multi-user.target | head
systemd-analyze blame | head             # boot-এ কোন service কত সময় নিল
journalctl -b -p warning --no-pager | tail     # এই boot-এর warning ও বেশি
journalctl -u ssh --since "1 hour ago"
```

> **Fedora-তে:** SSH service-এর নাম `sshd` (Ubuntu-তে `ssh`); বাকি command একই।

### 9.2 নিজের service চালান

Files: [`code/L01-10/hello_service.py`](code/L01-10/hello_service.py), [`code/L01-10/taskflow-demo.service`](code/L01-10/taskflow-demo.service)

**প্রথমে terminal-এ যাচাই (systemd ছাড়া):**

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-10
python3 hello_service.py --port 8080 &
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/
kill %1
```

**এই repository-তে (Windows-এ, port 18080) চালিয়ে আসল ফল:** `/health` → `ok`, `/` → `hello`; service log:

```text
INFO listening on 127.0.0.1:18080 (pid 26184)
INFO 127.0.0.1 "GET /health HTTP/1.1" 200 -
INFO 127.0.0.1 "GET / HTTP/1.1" 200 -
```

(Windows-এ `kill` POSIX SIGTERM পাঠায় না, তাই "received SIGTERM" লাইন সেখানে দেখা যায়নি — Ubuntu-তে দেখা যাওয়া উচিত।)

**Install (⚠️ system বদলায়):**

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin taskflow
sudo mkdir -p /opt/taskflow-demo
sudo install -m 0644 hello_service.py /opt/taskflow-demo/
sudo install -m 0644 taskflow-demo.service /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/taskflow-demo.service   # syntax যাচাই
sudo systemctl daemon-reload
sudo systemctl enable --now taskflow-demo                                # enable + start
systemctl status taskflow-demo --no-pager
curl -s http://127.0.0.1:8080/                                          # hello-from-systemd
```

`install -m 0644` = copy + permission একসাথে। `--now` = enable-এর সাথে এখনই start।

**Log দেখুন:**

```bash
journalctl -u taskflow-demo -f            # -f = follow (Ctrl+C দিয়ে বের হন)
```

**Graceful stop দেখুন:**

```bash
sudo systemctl stop taskflow-demo
journalctl -u taskflow-demo -n 5 --no-pager    # "received SIGTERM, shutting down" ও "stopped cleanly"
sudo systemctl start taskflow-demo
```

### 9.3 Failure ও auto-restart (Level C-ধরনের পরীক্ষা)

```bash
PID=$(systemctl show -p MainPID --value taskflow-demo)
sudo kill -KILL "$PID"                    # crash simulate
sleep 3
systemctl status taskflow-demo --no-pager | head -5    # নতুন PID — restart হয়েছে
systemctl show -p NRestarts taskflow-demo
journalctl -u taskflow-demo -n 10 --no-pager
```

প্রত্যাশিত journal (উদাহরণ): `Main process exited, code=killed, status=9/KILL` → `Scheduled restart job, restart counter is at 1.` → `Started taskflow-demo.service`।

**Sandbox পরীক্ষা:** service user হিসেবে লেখা নিষেধ জায়গায় লেখার চেষ্টা — `ProtectSystem=strict` কাজ করছে কিনা:

```bash
sudo systemd-run --uid=taskflow -p ProtectSystem=strict -p ProtectHome=true --pty \
  /bin/sh -c 'touch /etc/x; touch /opt/taskflow-demo/x; ls /home'
```

প্রত্যাশিত: `Read-only file system` error ও খালি/অপ্রাপ্য `/home`।

### 9.4 Override (drop-in) — মূল file না বদলে

```bash
sudo systemctl edit taskflow-demo
```

Editor-এ:

```ini
[Service]
Environment=GREETING=hello-from-override
```

Save করলে `/etc/systemd/system/taskflow-demo.service.d/override.conf` তৈরি হয় এবং systemd নিজে reload করে। তারপর:

```bash
sudo systemctl restart taskflow-demo && curl -s http://127.0.0.1:8080/
systemctl cat taskflow-demo                # মূল + override দুটোই দেখায়
```

Package-এর unit (যেমন nginx) বদলাতে **সবসময়** এই পদ্ধতি — package update-এ আপনার পরিবর্তন হারায় না।

### 9.5 Unit lint — Python

File: [`code/L01-10/unit_lint.py`](code/L01-10/unit_lint.py)

```bash
python3 unit_lint.py taskflow-demo.service; echo "exit=$?"
printf '[Service]\nExecStart=python3 app.py\n' > /tmp/bad.service
python3 unit_lint.py /tmp/bad.service; echo "exit=$?"
```

**আসল output (repository-তে চালানো):**

```text
taskflow-demo.service: 0 finding(s)
exit=0
bad.service: 10 finding(s)
  WARN  [Unit] Description missing — systemctl status-এ অর্থবহ নাম দেখায় না
  WARN  ExecStart uses relative program 'python3' — absolute path দিন
  WARN  no User= — service root হিসেবে চলবে
  WARN  Restart= not set — crash-এর পরে service নিজে চালু হবে না
  INFO  no MemoryMax= — একটি leak পুরো server-এর memory নিতে পারে (L01-09)
  INFO  consider NoNewPrivileges= — setuid দিয়ে privilege বাড়ানো বন্ধ করে
  INFO  consider PrivateTmp= — নিজস্ব /tmp — অন্যদের file দেখা/বদলানো যায় না
  INFO  consider ProtectSystem= — /usr, /etc read-only (strict হলে প্রায় সব)
  INFO  consider ProtectHome= — /home ও /root লুকানো
  WARN  [Install] WantedBy missing — systemctl enable কাজ করবে না
exit=1
```

তারপর native tool দিয়ে তুলনা (Ubuntu-তে):

```bash
systemd-analyze security taskflow-demo --no-pager | tail -3     # exposure score
```

### 9.6 Cleanup (⚠️)

```bash
sudo systemctl disable --now taskflow-demo
sudo rm -f /etc/systemd/system/taskflow-demo.service
sudo rm -rf /etc/systemd/system/taskflow-demo.service.d      # override না করলে এটি নেই — -f তাই error দেয় না
sudo systemctl daemon-reload
sudo rm -r /opt/taskflow-demo
sudo userdel taskflow
rm -f /tmp/bad.service
```

### 9.7 Test

```bash
python3 -m unittest -v
```

[`test_l01_10.py`](code/L01-10/test_l01_10.py)-এর ৭টি test: একই key একাধিকবার ও continuation লাইন (এখানে "double space" bug ধরা পড়েছিল), section-ছাড়া লাইন প্রত্যাখ্যান, ভালো unit-এ শূন্য finding, খারাপ unit-এর সব finding, `exec` ছাড়া shell wrapper, CLI exit code, এবং আসল HTTP server চালিয়ে `/health` = 200 ও অজানা path = 404।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `hello_service`: `logging` → `sys.stdout` | Log stdout-এ | journald ধরবে; file ও rotation নিজে সামলাতে হয় না |
| Format-এ timestamp নেই | | journald প্রতিটি লাইনে সময় দেয় — দ্বিগুণ timestamp এড়ানো |
| `server.shutdown()` আলাদা thread-এ | | `shutdown()` `serve_forever`-এর শেষের অপেক্ষা করে; signal handler থেকে সরাসরি ডাকলে deadlock |
| `--host 127.0.0.1` default | Loopback | Nginx-এর পেছনে চলবে (Module 06); সরাসরি internet-এ নয় |
| `parse_unit`: value list | `Environment=` একাধিক | systemd-এ অনেক key বারবার আসে |
| `last()` | শেষ মান | বেশিরভাগ key-তে পরের মান জেতে (drop-in override-এর মূলনীতি) |
| `exec_start.lstrip("-@:+!")` | systemd-এর বিশেষ prefix বাদ | যেমন `-` = ব্যর্থ হলেও উপেক্ষা |
| Shell wrapper check | `bash -c` + `exec` নেই | L01-08-এর SIGTERM সমস্যা |

**সীমাবদ্ধতা:** এটি শেখার জন্য ছোট checklist — syntax বা সব semantic যাচাই করে না (`systemd-analyze verify`), এবং exposure score দেয় না (`systemd-analyze security`)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `systemctl is-enabled taskflow-demo` | `enabled` |
| `systemctl is-active taskflow-demo` | `active` |
| `curl 127.0.0.1:8080/` | `hello-from-systemd` (override-এর পরে `hello-from-override`) |
| `kill -9 MainPID` | কয়েক সেকেন্ডে নতুন PID, `NRestarts` বাড়ে |
| `stop`-এর journal | "received SIGTERM" ও "stopped cleanly" |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| File বদলালাম, প্রভাব নেই | `daemon-reload` হয়নি | `systemctl status`-এ "changed on disk" warning | `sudo systemctl daemon-reload` তারপর restart |
| Reboot-এর পরে চালু হয় না | `enable` হয়নি | `systemctl is-enabled` | `enable` |
| `status=203/EXEC` | ExecStart-এর program নেই বা execute করা যায় না | Path ও permission | Absolute path, `ls -l` |
| `status=217/USER` | `User=`-এর user নেই | `id taskflow` | User তৈরি |
| `status=200/CHDIR` | WorkingDirectory নেই | `ls -ld` | Directory তৈরি |
| `start request repeated too quickly` | বারবার crash, start limit | `journalctl -u` | কারণ ঠিক করুন; তারপর `systemctl reset-failed` |
| Service লিখতে পারছে না | `ProtectSystem=strict` | journal-এ `Read-only file system` | `StateDirectory=` বা `ReadWritePaths=` |
| Stop-এ দীর্ঘ অপেক্ষা, তারপর KILL | SIGTERM handle হয় না | journal-এ "timed out" | App-এ handler (L01-08) |
| `systemctl: System has not been booted with systemd` | WSL/container-এ systemd নেই | `ps -p 1 -o comm=` | L00-07 Section 8.3, বা VM |

> **Fedora-তে:** SELinux service-কে আটকালে journal-এ সাধারণ "Permission denied" দেখায় — `sudo ausearch -m avc -ts recent` দিয়ে নিশ্চিত হোন (L01-17)।

## 13. Security, performance ও cost বিবেচনা

- **Security:** প্রতিটি service আলাদা non-root user; hardening option ও `systemd-analyze security` দিয়ে মাপা; secret `Environment=`-এ নয় (unit file সবাই পড়তে পারে এবং `systemctl show`-এ দেখা যায়) — `EnvironmentFile=` (root-only permission) বা `LoadCredential=`।
- **Performance:** `systemd-analyze blame`/`critical-chain` দিয়ে ধীর boot খোঁজা; অপ্রয়োজনীয় service বন্ধ।
- **Cost:** `MemoryMax=`/`CPUQuota=` দিয়ে একই server-এ একাধিক service নিরাপদে চালানো — কম server, কম খরচ।

## 14. Hands-on exercise

1. Unit-এ `Restart=on-failure` সরিয়ে `kill -9` করুন — কী হয়? তারপর ফিরিয়ে দিন।
2. `hello_service.py`-তে একটি bug রাখুন যাতে startup-এই exit 1 হয়। `systemctl status` ও journal-এ কী দেখেন? কতবার retry-র পরে systemd থামে? (`StartLimitBurst`, `StartLimitIntervalSec`)
3. `systemd-analyze security taskflow-demo`-এর score নোট করুন; `ProtectSystem` ও `PrivateTmp` সরিয়ে আবার দেখুন — score কীভাবে বদলায়?
4. `unit_lint.py`-তে নতুন নিয়ম: `Environment=`-এ `PASSWORD`/`SECRET`/`TOKEN` থাকলে WARN (`EnvironmentFile=` পরামর্শ)। Test লিখুন।
5. `journalctl -u taskflow-demo -o json-pretty -n 1` দেখুন — কোন কোন field আছে? L01-07-এর `jq` দিয়ে শুধু `MESSAGE` বের করুন।

## 15. Mini-project — Project 1-এর প্রথম service

Project 1 (Linux ops toolkit)-এর জন্য:

1. L01-09-এর `mem_report.py`-কে `--json` output দিতে বাড়ান।
2. একটি `Type=oneshot` service (`ops-memcheck.service`) লিখুন যা এটি চালায়, hardening সহ, এবং output journal-এ যায়।
3. `unit_lint.py`-তে শূন্য WARN পান এবং `systemd-analyze security`-এর score notebook-এ লিখুন।
4. পরের lesson (L01-11)-এ এটিকে timer দিয়ে প্রতি ৫ মিনিটে চালাবেন।

## 16. Interview প্রশ্ন

1. systemd কী এবং PID 1-এর দায়িত্ব কী?
2. `start` ও `enable`-এর পার্থক্য কী?
3. `After=` ও `Requires=`-এর পার্থক্য কী?
4. Unit file বদলানোর পরে কী করতে হয়?
5. Package-এর unit কীভাবে নিরাপদে customize করবেন?
6. Service বারবার crash করছে — কোন ক্রমে তদন্ত করবেন?
7. একটি service-কে কীভাবে harden করবেন? তিনটি option বলুন।
8. Application নিজে log file না লিখে stdout-এ লিখলে সুবিধা কী?

## 17. Self-assessment প্রশ্ন

1. সুপারভাইজার analogy কোথায় মেলে না?
2. Section 5-এর দুটি ব্যর্থতার কারণ ও সমাধান।
3. `Type=simple` ও `Type=notify`-এর পার্থক্য।
4. `stop` থেকে process মৃত্যু পর্যন্ত ধাপ (signal ও timeout সহ)।
5. `ProtectSystem=strict` থাকলে service কোথায় লিখতে পারে?
6. Unit lint test কোন bug ধরেছিল?

## 18. সংক্ষিপ্ত সারাংশ

- **systemd** = PID 1; service supervise, boot-এ চালু, cgroup-এ রাখে, journald-এ log।
- **Unit file**: `[Unit]` (বিবরণ, ক্রম, নির্ভরতা), `[Service]` (কীভাবে চালাবে, কে, সীমা, sandbox), `[Install]` (কোন target-এ)।
- `start` ≠ `enable`; বদলের পরে `daemon-reload`; customize `systemctl edit` (drop-in)।
- `Restart=on-failure`, `MemoryMax=`, non-root `User=`, hardening — production-এর ন্যূনতম।
- App stdout-এ log করুক; `journalctl -u ... -b -f` দিয়ে পড়ুন।

## 19. Completion checklist

- [ ] `systemctl status/list-units/--failed`, `systemd-analyze blame`, `journalctl -u/-b/-p` চালিয়েছি
- [ ] `taskflow-demo` install, enable, curl দিয়ে যাচাই
- [ ] Graceful stop journal-এ দেখেছি
- [ ] `kill -9` দিয়ে auto-restart যাচাই (`NRestarts`)
- [ ] Drop-in override দিয়ে GREETING বদলেছি
- [ ] `systemd-analyze security` score নোট করেছি
- [ ] Cleanup সম্পন্ন
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- systemd documentation index: https://www.freedesktop.org/software/systemd/man/latest/
- `systemd.service(5)`: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- `systemd.unit(5)` (`After=`, `Wants=`, `WantedBy=`): https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html
- `systemd.exec(5)` (User, Environment, sandboxing): https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- `journalctl(1)`: https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- `systemd-analyze(1)` (verify, security, blame): https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html
- Ubuntu Server — systemd ও service management: https://documentation.ubuntu.com/server/

---

**পরের lesson:** L01-11 — cron বনাম systemd timer
