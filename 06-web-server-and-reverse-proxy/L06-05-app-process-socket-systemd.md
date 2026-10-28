# L06-05 — Application process, port, unix socket ও systemd service

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L06-04 — Reverse proxy](L06-04-reverse-proxy-upstream.md), [L01-10 — systemd service](../01-linux-systems/L01-10-systemd-services.md), [L01-04 — Permission](../01-linux-systems/L01-04-users-permissions.md) |
| **Label** | — |
| **Tested** | `taskflow_serve.py`, `socket_check.py`, unit file: ১০টি test-এর ৮টি পাস, ২টি skip (Python 3.14.5, Windows)। **Skip দুটি:** unix socket ও আসল socket activation (fd ৩ উত্তরাধিকার) — Windows Python-এ AF_UNIX নেই। এ দুটি Ubuntu-তে চলার কথা, কিন্তু **চালানো হয়নি**। `bind_probe.py` দিয়ে Windows-এর bind আচরণ আসলে মাপা হয়েছে (Section 9.1)। `taskflow.service` L01-10-এর `unit_lint.py`-তে পরিষ্কার; ওই tool `.socket` unit বোঝে না (Section 9.4)। systemd-এ কিছু **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Application কোথায় শুনবে: `0.0.0.0` বনাম `127.0.0.1` বনাম `::` বনাম **unix socket** — নিরাপত্তা ও performance।
- Port-এর সংঘাত (`EADDRINUSE`), privileged port, এবং **OS-ভেদে bind-এর ভিন্ন আচরণ**।
- Unix socket-এর permission: socket file **ও** path-এর প্রতিটি directory — `(13: Permission denied)`-এর ক্লাসিক কারণ।
- **systemd socket activation:** systemd socket ধরে রাখে, app restart-এর সময়ও connection হারায় না।
- TaskFlow-কে hardened systemd service + socket হিসেবে চালানো, nginx-কে unix socket-এ যুক্ত করা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L06-04-এর scenario: রাত ২টায় app restart, আর কয়েক সেকেন্ড "Connection refused" ও 502। কারণ, app restart হলে তার listening socket বন্ধ হয়ে নতুন করে খোলে — মাঝের সময় port-এ কেউ নেই।

আরও কিছু সাধারণ সমস্যা:

- App ভুলবশত `0.0.0.0:8000`-এ শুনছে, firewall-এর একটি ভুলে সরাসরি internet থেকে পৌঁছানো যায় — nginx-এর সব সুরক্ষা বাইপাস।
- Unix socket ব্যবহার করতে গিয়ে nginx পাচ্ছে `Permission denied`, অথচ socket নিজে `0777`।
- দুটি app একই port নিতে চায়, এবং একটি নীরবে অন্যটির traffic "চুরি" করে।

## 3. সহজ ভাষায় পরিচয়

| Bind | কে পৌঁছাতে পারে | ব্যবহার |
|---|---|---|
| `0.0.0.0:8000` / `[::]:8000` | সব interface — network থেকেও | Proxy ছাড়া সরাসরি service (সাধারণত নয়) |
| `127.0.0.1:8000` | শুধু এই machine | nginx-এর পেছনে TCP |
| `unix:/run/taskflow/taskflow.sock` | শুধু এই machine, **file permission অনুযায়ী** | nginx-এর পেছনে — সবচেয়ে সংকীর্ণ |

```nginx
upstream taskflow_app {
    server unix:/run/taskflow/taskflow.sock;
    keepalive 16;
}
```

```ini
# taskflow.socket
[Socket]
ListenStream=/run/taskflow/taskflow.sock
SocketUser=taskflow
SocketGroup=www-data
SocketMode=0660
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের দরজা ও চিঠির বাক্স

- **`0.0.0.0`** = রাস্তার দিকে খোলা দরজা — যে কেউ ঢুকতে পারে।
- **`127.0.0.1`** = ভবনের ভেতরের দরজা — শুধু ভবনের লোক।
- **Unix socket** = নির্দিষ্ট কর্মীর নামে তালাবদ্ধ চিঠির বাক্স। চাবি (file permission) যার আছে, শুধু সে।
- **Socket activation** = অভ্যর্থনা ডেস্ক চিঠি জমা রাখে, আর কর্মী ছুটিতে থাকলেও (restart) চিঠি ফেরত যায় না — কর্মী ফিরলে সব পান।

### Analogy কোথায় মেলে না

- **বাক্সের চাবি থাকলেই হয় না — বাক্স পর্যন্ত পৌঁছানোর প্রতিটি দরজা খোলা থাকতে হয়।** Socket file `0777` হলেও তার ওপরের কোনো directory-তে (যেমন `/home/ana`, `0750`) `x` অনুমতি না থাকলে nginx পৌঁছাতে পারে না। Ubuntu ২১.০৪ থেকে নতুন home directory `0750` — তাই home-এর ভেতরে socket রাখলে এই সমস্যা প্রায় নিশ্চিত (Section 9.3)।
- **ভেতরের দরজা মানে নিরাপদ, সবসময় নয়।** একই machine-এর **যেকোনো** user বা process `127.0.0.1:8000`-এ পৌঁছাতে পারে। Unix socket-এ file permission দিয়ে সেটাও সীমিত করা যায়। আর container বা cloud-এ "একই machine"-এর অর্থ বদলে যায় (Module 10)।
- **দুজন একই দরজা দাবি করলে সবসময় "দুঃখিত, দখল" শোনা যায় না।** এই Windows machine-এ মাপা হয়েছে: একটি process `0.0.0.0:P` ধরে রাখলেও **অন্য একটি process `127.0.0.1:P`-এ bind করতে পেরেছে**। তখন localhost-এর traffic নির্দিষ্টতর bind পায় (Section 9.1)। Linux-এ এখানে `EADDRINUSE` আসার কথা — আচরণ OS-নির্ভর।

## 5. Real-world engineering scenario — "Deploy-এর প্রতিবার ৩ সেকেন্ডের 502"

**পরিস্থিতি:** TaskFlow-এর প্রতিটি deploy-এ `systemctl restart taskflow`। nginx-এর error log-এ প্রতিবার কয়েকটি `connect() failed (111: Connection refused)`, আর user-রা দেখেন 502।

**কারণ:** restart মানে পুরোনো process বন্ধ (socket বন্ধ), নতুন process Python import, database migrate, তারপর bind — মাঝের ~৩ s কেউ শুনছে না।

**সমাধান — socket activation:**

1. `taskflow.socket` unit: systemd নিজে `/run/taskflow/taskflow.sock` বানায় ও **ধরে রাখে**।
2. `taskflow.service` চালু হলে systemd সেই socket fd ৩ হিসেবে দেয় (`LISTEN_FDS=1`, `LISTEN_PID=<pid>`)। `taskflow_serve.py` সেটা ব্যবহার করে, নিজে bind করে না।
3. Restart-এর সময় socket খোলাই থাকে। nginx-এর connect সফল হয় — kernel-এর backlog-এ অপেক্ষা করে, যতক্ষণ না নতুন process `accept()` শুরু করে। ফলে refused নয়, একটু দেরি।

সাথে:

- nginx-এ `server unix:/run/taskflow/taskflow.sock;`।
- Socket `www-data` group-এর জন্য `0660`; TaskFlow-এর `RestrictAddressFamilies=AF_UNIX` — app-এর network-এ কিছু খোলারই ক্ষমতা নেই।

**শিক্ষা:** Zero-downtime শুধু deploy tool-এর বিষয় নয় — socket-এর মালিক কে, সেটাও গুরুত্বপূর্ণ।

## 6. Diagram — TaskFlow-এর চূড়ান্ত বিন্যাস

```text
 internet ──► nginx (www-data)  :80/:443
                 │ upstream: server unix:/run/taskflow/taskflow.sock
                 ▼
 /run/taskflow/            drwxr-xr-x root root           ← www-data-এর 'x' আছে
   taskflow.sock           srw-rw---- taskflow www-data   ← group www-data: 'w' আছে
         ▲  systemd বানায় ও ধরে রাখে (taskflow.socket)
         │  fd 3 হিসেবে দেয় ─► taskflow.service (User=taskflow)
         │                      ExecStart=python3 taskflow_serve.py   (LISTEN_FDS=1)
         │                      RestrictAddressFamilies=AF_UNIX, ProtectSystem=strict
         │                      StateDirectory=taskflow → /var/lib/taskflow/taskflow.db
 restart: service বন্ধ ─► socket খোলা থাকে ─► নতুন connection backlog-এ ─► নতুন process accept
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Bind address | কোন interface-এ socket শোনে |
| Wildcard address | `0.0.0.0` / `::` — সব interface |
| `EADDRINUSE` | Address ইতিমধ্যে ব্যবহৃত (Linux errno ৯৮; Windows ১০০৪৮) |
| Privileged port | ১০২৪-এর নিচে — Linux-এ root বা `CAP_NET_BIND_SERVICE` |
| Unix domain socket | File path দিয়ে চেনা local socket; TCP/IP stack নেই |
| Socket activation | systemd socket বানিয়ে service-কে দেয় |
| `LISTEN_FDS` / `LISTEN_PID` | systemd-এর চুক্তি — কয়টি fd, কোন process-এর জন্য |
| Backlog | Accept-এর অপেক্ষায় থাকা connection-এর queue |
| `RuntimeDirectory` / `StateDirectory` | systemd বানানো `/run/<name>` / `/var/lib/<name>` |
| `SO_REUSEADDR` | TIME_WAIT-এর মধ্যেও আবার bind; OS-ভেদে অর্থ ভিন্ন |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 TCP loopback বনাম unix socket

Unix socket kernel-এর ভেতরে সরাসরি data কপি করে — TCP handshake, checksum, routing নেই। তাই latency সামান্য কম, এবং port-এর সংঘাত নেই।

সবচেয়ে বড় সুবিধা: **permission**। File-এর মালিকানা দিয়ে ঠিক করা যায় কে connect করতে পারবে।

সীমাবদ্ধতা:

- শুধু একই machine।
- Container-এ volume share করতে হয় (Module 10)।
- Windows-এ Python-এর `socket.AF_UNIX` নেই (এই lesson-এর test তাই skip)।

### 8.2 Socket-এ connect-এর অনুমতি

Linux-এ unix socket-এ `connect()` করতে লাগে:

- socket file-এ **write** অনুমতি;
- path-এর **প্রতিটি** directory-তে **execute (search)** অনুমতি।

`socket_check.py` ঠিক এই পথ ধরে প্রতিটি অংশ যাচাই করে, `namei -l`-এর মতো।

### 8.3 Socket activation-এর চুক্তি

systemd service চালুর আগে environment-এ বসায়:

- `LISTEN_PID=<service-এর PID>`;
- `LISTEN_FDS=1`;
- এবং socket-কে fd ৩-এ রাখে।

`LISTEN_PID` যাচাই জরুরি — নইলে app-এর চালু করা কোনো child process ভুল করে ওই fd নিজের ভাবতে পারে। ব্যবহারের পরে এই variable-গুলো মুছে ফেলা হয়।

`taskflow_serve.py` `socketserver`-কে `bind_and_activate=False` দিয়ে বানায়, তারপর তার socket-এর জায়গায় systemd-এর দেওয়া socket বসায়।

### 8.4 Unix socket-এর permission bind-এর মুহূর্তেই

নিজে socket বানালে (`--unix`), `bind()` করার আগে `umask` ঠিক করা হয়। ফলে file তৈরির মুহূর্তেই `0660`। Bind-এর পরে `chmod` করলে মাঝের ক্ষণিকের জন্য socket অন্যের কাছে খোলা থাকে (race)।

> **Fedora-তে:** nginx-এর user `nginx`, তাই `SocketGroup=nginx`। SELinux-এ nginx-কে unix socket-এ connect করতে socket-এর context `httpd_var_run_t` বা উপযুক্ত policy লাগে। `ausearch -m avc` দিয়ে denial দেখুন (L01-17)।

## 9. Practical demonstration

Files:

- [`code/L06-05/bind_probe.py`](code/L06-05/bind_probe.py), [`socket_check.py`](code/L06-05/socket_check.py)।
- [`layout-home.json`](code/L06-05/layout-home.json), [`layout-run.json`](code/L06-05/layout-run.json) (হাতে তৈরি বর্ণনা)।
- [`taskflow_serve.py`](code/L06-05/taskflow_serve.py)।
- [`taskflow.socket`](code/L06-05/taskflow.socket), [`taskflow.service`](code/L06-05/taskflow.service)।
- [`test_l06_05.py`](code/L06-05/test_l06_05.py)।

### 9.1 Bind-এর আচরণ — আসল output (Windows)

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-05
python3 bind_probe.py
```

```text
platform: win32 (nt)
  127.0.0.1 then 127.0.0.1                     → second failed: [10048] Only one usage of each socket address (protocol/network address/port) is normally permitted
  0.0.0.0   then 127.0.0.1                     → BOTH BOUND
  127.0.0.1 then 0.0.0.0                       → BOTH BOUND
  0.0.0.0   then 127.0.0.1 (SO_REUSEADDR)      → BOTH BOUND
```

Windows-এ wildcard ও নির্দিষ্ট address একসাথে bind হয় — অন্য একটি process localhost-এর traffic নিয়ে নিতে পারে। Linux-এ দ্বিতীয় ও তৃতীয় case-এ `[98] Address already in use` আসার কথা। Ubuntu-তে চালিয়ে মিলিয়ে দেখুন (exercise ১)।

### 9.2 TaskFlow-কে ভিন্ন উপায়ে চালানো

```bash
python3 taskflow_serve.py --tcp 127.0.0.1:8000          # যেকোনো OS
python3 taskflow_serve.py --unix /tmp/taskflow.sock      # Linux
```

এই machine-এ `--unix` দিলে, আসল output:

```text
error: unix sockets are not available on this platform (use --tcp)
```

(Crash বা traceback নয়, স্পষ্ট বার্তা।) Test-এ "systemd-এর দেওয়া" socket-এর মতো একটি আগে-বানানো TCP socket দিয়ে server চালানো যাচাই হয়েছে — সব OS-এ।

### 9.3 `Permission denied`-এর নির্ণয় — আসল output

```bash
python3 socket_check.py /home/ana/taskflow/taskflow.sock --fake-fs layout-home.json
python3 socket_check.py /run/taskflow/taskflow.sock --fake-fs layout-run.json
```

```text
  ok  drwxr-xr-x uid=0     gid=0     /                                  needs 'x' as other
  ok  drwxr-xr-x uid=0     gid=0     /home                              needs 'x' as other
  NO  drwxr-x--- uid=1000  gid=1000  /home/ana                          needs 'x' as other
  ok  drwxr-xr-x uid=1000  gid=1000  /home/ana/taskflow                 needs 'x' as other
  ok  srwxrwxrwx uid=1000  gid=1000  /home/ana/taskflow/taskflow.sock   needs 'w' as other
verdict: www-data is blocked at /home/ana — nginx logs '(13: Permission denied)'

  ok  srw-rw---- uid=998   gid=33    /run/taskflow/taskflow.sock        needs 'w' as group
verdict: www-data can connect
```

Socket `0777`, তবুও blocked। "socket-এ chmod 777 দিয়েছি, তবুও কাজ করছে না" — এই অভিযোগের উত্তর এটাই।

Ubuntu-তে `--fake-fs` ছাড়া আসল filesystem দিয়েই চলে: `sudo python3 socket_check.py /run/taskflow/taskflow.sock --user www-data`।

### 9.4 Unit file যাচাই

```bash
python3 ../../../01-linux-systems/code/L01-10/unit_lint.py taskflow.service taskflow.socket
```

```text
taskflow.service: 0 finding(s)
taskflow.socket: 1 finding(s)
  ERROR no [Service] section
```

দ্বিতীয় লাইনটি **tool-এর সীমা, unit-এর ভুল নয়** — L01-10-এর linter শুধু `.service` বোঝে। Socket unit-এর জন্য test আলাদাভাবে `[Socket]`-এর key যাচাই করে। Exercise ৪-এ linter-কে বাড়ান।

### 9.5 Ubuntu-তে পুরো পথ (চালানো হয়নি)

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin taskflow
sudo install -d -o root -g root -m 0755 /opt/taskflow
sudo install -m 0644 ../../../05-python-for-infrastructure/code/L05-13/taskflow_api.py taskflow_serve.py /opt/taskflow/
sudo sed -i 's#parents\[3\] / "05-python-for-infrastructure" / "code" / "L05-13"#parent#' /opt/taskflow/taskflow_serve.py
sudo cp taskflow.socket taskflow.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now taskflow.socket
ls -l /run/taskflow/                                              # srw-rw---- taskflow www-data
sudo -u www-data curl -s --unix-socket /run/taskflow/taskflow.sock http://x/health   # প্রথম connection-এ service চালু
systemctl status taskflow.service --no-pager | head -5
# restart-এর সময় connection হারায় কিনা:
( for i in $(seq 1 50); do sudo -u www-data curl -s -o /dev/null -w '%{http_code} ' \
    --unix-socket /run/taskflow/taskflow.sock http://x/health; sleep 0.1; done ) &
sudo systemctl restart taskflow.service; wait; echo
python3 -m unittest -v            # skip ২টিও এবার চলবে
```

`sed` লাইনটি `/opt/taskflow`-এ দুটি file একসাথে রাখায় import path ঠিক করে। ভালো উপায় হলো package বানানো (L05-13-এর mini-project)।

### 9.6 Test

```bash
python3 -m unittest -v
```

১০টি test:

- `LISTEN_PID` যাচাই।
- আগে-বানানো socket-এ server।
- Unix socket-এর mode `0660` ও request *(POSIX)*।
- **আসল socket activation** — launcher fd ৩-এ socket বসিয়ে `LISTEN_*` set করে, তারপর `exec` *(POSIX)*।
- Home directory-র ফাঁদ।
- Socket unit-এর বিন্যাস (www-data পারে, nobody পারে না, অনুপস্থিত)।
- Permission bit (owner আগে মেলে)।
- Space-যুক্ত path।
- Socket unit-এর key।
- Service unit + L01-10-এর linter।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `listen_fds(environ, pid)` | `LISTEN_PID` মিললেই শুধু | Child-এ ভুল fd নয় |
| `socket.socket(fileno=3)` | systemd-এর socket নেওয়া | নিজে bind নয় |
| `bind_and_activate=False` + socket বদল | `socketserver`-কে দেওয়া socket দেওয়া | Library-র নিজের bind এড়ানো |
| `LISTEN_*` মুছে ফেলা | Env পরিষ্কার | Subprocess-এ ছড়াবে না |
| `os.umask(0o777 & ~mode)` bind-এর আগে | তৈরির মুহূর্তে সঠিক permission | chmod-এর race নয় |
| পুরোনো socket file মোছা (শুধু socket হলে) | `Address already in use` (unix) এড়ানো | ভুল করে সাধারণ file মোছে না |
| `socket_check` — owner → group → other ক্রম | Linux-এর নিয়ম | Owner হলে group bit দেখা হয় না |
| `RestrictAddressFamilies=AF_UNIX` | App-এর network socket খোলা নিষেধ | Compromise হলেও বাইরে connect নয় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `bind_probe.py` | Windows: BOTH BOUND; Linux: EADDRINUSE (যাচাই বাকি) |
| `socket_check.py … layout-home.json` | blocked at /home/ana, exit ১ |
| `unit_lint.py taskflow.service` | ০ finding |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK` (Windows-এ skip ২) |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `connect() to unix:… failed (13)` | Directory-র x বা socket-এর w নেই | `socket_check.py`; `namei -l`; socket `/run`-এ |
| `connect() to unix:… failed (2)` | Socket নেই | Service চলছে? Path একই? `systemctl status taskflow.socket` |
| `bind() … (98: Address already in use)` | Port-এ অন্য process | `ss -ltnp 'sport = :8000'` |
| Unix socket-এ `Address already in use` | আগের run-এর পুরোনো file | Bind-এর আগে মুছুন (শুধু socket হলে); বা socket activation |
| Restart-এ 502 | Process-এর নিজের socket | Socket activation |
| App internet থেকে পৌঁছানো যায় | `0.0.0.0`-এ bind | `127.0.0.1` বা unix socket; firewall (L02-10) |
| `ProtectSystem=strict`-এ DB লেখা যায় না | `/var/lib`-এ লেখার অনুমতি নেই | `StateDirectory=` |
| `RestrictAddressFamilies`-এ app শুরু হয় না | App নিজে TCP-তে bind করতে চায় | socket activation, বা `AF_INET` যোগ |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Unix socket + `0660` + group `www-data` — শুধু nginx পৌঁছাতে পারে।
  - App-এর `RestrictAddressFamilies=AF_UNIX`, খালি `CapabilityBoundingSet=`, `ProtectSystem=strict`।
  - App কখনো root নয়; port ৮০/৪৪৩ nginx-এর।
  - Windows-এর bind আচরণ মনে রাখুন — সেখানে "port দখল" মানে একচেটিয়া নয়।
- **Performance:**
  - Unix socket loopback TCP-এর চেয়ে কিছুটা দ্রুত (Ubuntu-তে মাপুন — exercise ৩)।
  - Socket activation-এ boot দ্রুত হয় (service প্রয়োজনে চালু)।
  - `Backlog=` restart-এর সময় অপেক্ষমাণ connection ধরে রাখে।
- **Cost:** সরাসরি খরচ নেই। কিন্তু zero-downtime deploy-এ maintenance window-এর দরকার কমে, ফলে দিনের বেলাতেই নিরাপদে deploy করা যায়।

## 14. Hands-on exercise

1. Ubuntu-তে `bind_probe.py` চালিয়ে Windows-এর ফলের সাথে তুলনা করুন। কোন case-এ পার্থক্য?
2. Section 9.5 চালান। Restart-এর সময় ৫০টি request-এর কোনোটি ব্যর্থ হলো কি? Socket activation ছাড়া (`--unix`-এ সরাসরি) একই পরীক্ষা করুন।
3. TCP (`127.0.0.1:8000`) বনাম unix socket-এ ১০০০টি request-এর সময় মাপুন (`keepalive_bench.py`-এর মতো, keep-alive ছাড়া)।
4. L01-10-এর `unit_lint.py`-কে `.socket` unit বুঝতে শেখান: `[Socket]` section, `ListenStream`, `SocketMode` বেশি খোলা (`0666`) হলে সতর্কতা।
5. `socket_check.py`-এ POSIX ACL (`getfacl`) বিবেচনা যোগ করুন — ACL থাকলে mode bit যথেষ্ট নয় (L01-05)।

## 15. Mini-project — Deploy script

`deploy_taskflow.sh` (L04-এর নিয়ম মেনে):

- নতুন version `/opt/taskflow/releases/<ts>`-এ।
- `current` symlink atomic-ভাবে বদলানো (L05-03)।
- `systemctl restart taskflow.service` (socket activation-এর কারণে refused নেই)।
- `/health` যাচাই (L05-12) — ব্যর্থ হলে আগের release-এ symlink ফেরত।
- শেষ ৩টি release রাখা।

Module 11-এর CI/CD pipeline এই script ডাকবে।

## 16. Interview প্রশ্ন

1. Application `0.0.0.0` না `127.0.0.1`-এ bind করবে — কখন কোনটা?
2. Unix socket ও TCP socket-এর পার্থক্য কী? কখন unix socket?
3. nginx unix socket-এ `Permission denied` দিচ্ছে — কীভাবে debug করবেন?
4. systemd socket activation কী, এবং কী সমস্যার সমাধান করে?
5. Port ৮০-তে root ছাড়া কীভাবে শোনা যায়?
6. `EADDRINUSE` কেন হয়? `SO_REUSEADDR` কী করে?

## 17. Self-assessment প্রশ্ন

1. দরজা ও চিঠির বাক্স analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ restart-এ 502 কেন হতো, এবং socket activation কীভাবে ঠেকায়?
3. Socket `0777` হলেও `/home/ana`-র কারণে কেন blocked?
4. `LISTEN_PID` কেন যাচাই করা হয়?
5. Windows-এর bind আচরণ কোন নিরাপত্তা ঝুঁকি তৈরি করে?

## 18. সংক্ষিপ্ত সারাংশ

- App nginx-এর পেছনে: `127.0.0.1` বা (ভালো) unix socket; কখনো `0.0.0.0` নয়।
- Unix socket-এ লাগে socket-এ `w` + path-এর প্রতিটি directory-তে `x`; socket `/run`-এ, home-এ নয়।
- Socket activation: systemd socket ধরে রাখে → restart-এ refused নয়।
- Hardened unit: unprivileged user, `StateDirectory`, `ProtectSystem=strict`, `RestrictAddressFamilies=AF_UNIX`।
- Bind-এর আচরণ OS-ভেদে ভিন্ন — অনুমান নয়, মাপুন।

## 19. Completion checklist

- [ ] `bind_probe.py` দুই OS-এ চালিয়ে পার্থক্য দেখেছি
- [ ] `socket_check.py` দিয়ে home-directory ফাঁদ ব্যাখ্যা করতে পারি
- [ ] (Ubuntu) TaskFlow socket activation-এ চালিয়ে restart-এ ০টি ব্যর্থতা দেখেছি
- [ ] `python3 -m unittest -v`-এ সব test পাস (Ubuntu-তে skip ০)
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- systemd — `systemd.socket`: https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html
- systemd — `sd_listen_fds` (activation protocol): https://www.freedesktop.org/software/systemd/man/latest/sd_listen_fds.html
- systemd — `systemd.exec` (StateDirectory, RestrictAddressFamilies): https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- Linux man page — `unix(7)`: https://man7.org/linux/man-pages/man7/unix.7.html
- nginx — `upstream` `server unix:`: https://nginx.org/en/docs/http/ngx_http_upstream_module.html#server
- Python — `socketserver`: https://docs.python.org/3/library/socketserver.html
- Microsoft Learn — Using SO_REUSEADDR and SO_EXCLUSIVEADDRUSE: https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse

---

**পরের lesson:** L06-06 — Nginx caching ও compression
