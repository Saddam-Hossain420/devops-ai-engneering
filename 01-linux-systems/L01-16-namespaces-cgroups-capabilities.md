# L01-16 — Namespace, cgroup ও Linux capability

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Advanced |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-15 — Performance](L01-15-performance-profiling.md); [L01-09 — cgroup memory](L01-09-cpu-memory-oom.md); [L01-08 — process](L01-08-processes-signals.md) |
| **Label** | 🖥️ VM (`unshare` ও cgroup experiment-এ sudo) |
| **Tested** | `caps_ns.py`: ৬টি test পাস; `00000000a80425fb` decode করে **Docker-এর documented ১৪টি default capability**-র সাথে হুবহু মিলেছে (স্বাধীন যাচাই)। নমুনা `/proc/PID/status`, `ns`, `cgroup` হাতে তৈরি (আসল format অনুসরণে)। `unshare`, `nsenter`, `capsh`, `systemd-cgls` **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- **Container আসলে কী:** কোনো একক "container" kernel feature নেই — namespace + cgroup + capability + seccomp + layered filesystem-এর সমন্বয়।
- **Namespace** — একটি process কী **দেখতে** পায় (PID, network, mount, hostname, IPC, user, cgroup, time)।
- **cgroup** — একটি process কতটা **ব্যবহার** করতে পারে (CPU, memory, I/O, process সংখ্যা)।
- **Capability** — root-এর ক্ষমতা ভেঙে ছোট অংশে; কোন process কোন বিশেষ অধিকার **করতে** পারে।
- `unshare`, `nsenter`, `/proc/PID/ns`, `/sys/fs/cgroup`, `capsh`, systemd-এর resource ও capability option।
- Python দিয়ে capability decode, namespace তুলনা ও cgroup path।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি server-এ অনেক application একসাথে চালাতে চাই — কিন্তু:

- একটি app অন্যটির process বা file দেখুক না (isolation)।
- একটির memory leak বাকিদের ডুবিয়ে না দিক (resource limit)।
- Port ৮০ খুলতে root লাগে বলে পুরো app root হিসেবে না চলুক (least privilege)।

VM এগুলো দেয়, কিন্তু প্রতিটি VM-এ পূর্ণ OS — ভারী ও ধীর। Linux kernel-এর এই তিনটি feature একই kernel-এর ভেতরেই হালকা isolation দেয় — **এটাই Docker, Podman ও Kubernetes-এর ভিত্তি** (Module 09, 14)। এগুলো বুঝলে container "জাদু" নয়, এবং container-এর security সীমাও বোঝা যায় (L01-01: container একই kernel share করে)।

## 3. সহজ ভাষায় পরিচয়

| Feature | প্রশ্ন | উদাহরণ |
|---|---|---|
| **Namespace** | কী **দেখতে** পায়? | Container-এর ভেতরে `ps` শুধু নিজের process দেখায়, নিজের PID 1 |
| **cgroup** | কতটা **ব্যবহার** করতে পারে? | `MemoryMax=256M` — বেশি চাইলে OOM (L01-09) |
| **Capability** | কী **করতে** পারে? | `CAP_NET_BIND_SERVICE` — root ছাড়াই port ৮০ |

**Namespace-এর ধরন:**

| Namespace | আলাদা করে |
|---|---|
| `pid` | Process ID — ভেতরে নিজস্ব PID 1 |
| `net` | Network interface, IP, routing, port, firewall |
| `mnt` | Mount point — নিজস্ব filesystem দৃশ্য |
| `uts` | Hostname |
| `ipc` | Shared memory, message queue |
| `user` | UID/GID mapping — ভেতরে root, বাইরে সাধারণ user |
| `cgroup` | cgroup tree-এর দৃশ্য |
| `time` | কিছু clock (boot time) |

**Capability:** ঐতিহাসিকভাবে root (UID 0) সব পারত। Linux root-এর ক্ষমতাকে ~৪১টি আলাদা capability-তে ভাগ করেছে (যেমন `CAP_NET_ADMIN` network configure, `CAP_SYS_ADMIN` অনেক কিছু)। একটি process-কে শুধু দরকারিগুলো দেওয়া যায় — root হলেও কম।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অ্যাপার্টমেন্ট ভবন

- **Kernel** = ভবনের ভিত্তি, বিদ্যুৎ ও পানির লাইন — সবাই share করে।
- **Namespace** = প্রতিটি অ্যাপার্টমেন্টের দেয়াল ও জানালা: ভেতর থেকে নিজের ঘর দেখা যায়, অন্যদের নয়; নিজস্ব দরজার নম্বর (PID 1), নিজস্ব ডাকবাক্স (network)।
- **cgroup** = প্রতিটি অ্যাপার্টমেন্টের নিজস্ব বিদ্যুৎ মিটার ও breaker: সীমা ছাড়ালে শুধু সেই ফ্ল্যাটের breaker পড়ে, পুরো ভবন অন্ধকার হয় না।
- **Capability** = ভাড়াটের চাবির গোছা: হয়তো ছাদের চাবি আছে (port ৮০), কিন্তু বিদ্যুৎ ঘরের (kernel module) নেই — যদিও তিনি নিজের ফ্ল্যাটে "মালিক" (container-এর root)।

### Analogy কোথায় মেলে না

- অ্যাপার্টমেন্টের দেয়াল ইট-পাথরের। Namespace-এর দেয়াল **একই kernel-এর ভেতরে software নিয়ম** — kernel-এ একটি bug থাকলে দেয়াল ভেদ করা সম্ভব (container escape)। তাই container VM-এর মতো শক্তিশালী isolation নয়; untrusted workload-এ অতিরিক্ত স্তর (seccomp, AppArmor/SELinux, user namespace, বা gVisor/Kata-র মতো sandbox) লাগে।
- ভবনের একটি "মালিকের চাবি" সব দরজা খোলে। `CAP_SYS_ADMIN` এমন একটি চাবি — এত বেশি কাজ এর আওতায় যে একে প্রায় পূর্ণ root ধরা হয়। "Privileged container" মানে সব চাবি দিয়ে দেওয়া।
- ফ্ল্যাটের দেয়াল সবদিকে একসাথে ওঠে। Namespace **আলাদা আলাদা** — একটি process network-এ আলাদা কিন্তু PID-এ host-এর সাথে share করতে পারে (Kubernetes Pod-এ container-গুলো network namespace share করে, Module 14)।

## 5. Real-world engineering scenario — "Privileged container দিলেই কাজ হয়ে যায়"

**পরিস্থিতি:** একটি monitoring agent container-এ চলে, host-এর network interface-এর তথ্য দরকার। কাজ না হওয়ায় একজন engineer `docker run --privileged` দিলেন — কাজ হলো, সবাই খুশি।

**ঝুঁকি (এই lesson-এর নমুনায় আসলে দেখা):**

```text
# সাধারণ container (Docker default) — CapEff 00000000a80425fb
14 capability, কোনো RISK নেই

# privileged — CapEff 000001ffffffffff
RISK CAP_SYS_ADMIN, CAP_SYS_MODULE, CAP_SYS_PTRACE, CAP_SYS_RAWIO,
     CAP_DAC_READ_SEARCH, CAP_NET_ADMIN, CAP_BPF ...
```

Privileged container-এ: সব capability, seccomp বন্ধ, host-এর সব device দৃশ্যমান। Agent-এ একটি vulnerability = **host-এর পূর্ণ নিয়ন্ত্রণ** (kernel module load, host disk mount)।

**সঠিক সমাধান (least privilege):** শুধু যা দরকার:

- Host network দেখতে: host-এর **network namespace** share (`--network host`) — অথবা শুধু `/proc/net` read-only mount।
- বিশেষ কাজ লাগলে নির্দিষ্ট capability (`--cap-add NET_ADMIN`) — সব নয়।

**Diagnosis পদ্ধতি:** container-এর process-এর `/proc/<PID>/status`-এর `CapEff` decode করুন (এই lesson-এর tool) এবং `ls -l /proc/<PID>/ns` host-এর সাথে তুলনা করুন — কোন দেয়াল আছে, কোন চাবি দেওয়া হয়েছে, এক নজরে।

## 6. Diagram — একটি container আসলে কী

```text
 host kernel (একটিই)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  process: python3 (host PID 5530, container-এ PID 1)                       │
 │    namespaces : pid ✓ net ✓ mnt ✓ uts ✓ ipc ✓ cgroup ✓  user ✗ (host-এর)   │  ← কী দেখে
 │    cgroup     : /system.slice/docker-3f9c...scope                          │  ← কতটা পায়
 │                 memory.max=256M  cpu.max="50000 100000" pids.max=200       │
 │    caps       : CapEff a80425fb (Docker-এর ১৪টি)                           │  ← কী করতে পারে
 │    seccomp    : filter (≈৪০+ বিপজ্জনক system call বন্ধ)                     │  ← কোন syscall
 │    LSM        : AppArmor profile "docker-default" (Fedora-তে SELinux label) │  ← কোন file/অধিকার
 │    rootfs     : overlayfs (image layer + লেখার layer, Module 09)            │  ← নিজস্ব filesystem
 └──────────────────────────────────────────────────────────────────────────┘
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Namespace | Process-এর জন্য একটি global resource-এর আলাদা দৃশ্য |
| `unshare` | নতুন namespace-এ একটি command চালানো |
| `nsenter` | বিদ্যমান process-এর namespace-এ প্রবেশ |
| cgroup v2 | Unified hierarchy (`/sys/fs/cgroup`), Ubuntu 22.04+ ও Fedora-তে default |
| Controller | cgroup-এর resource ধরন: `cpu`, `memory`, `io`, `pids` |
| `memory.max`, `cpu.max`, `pids.max` | cgroup-এর সীমা file |
| Capability | Root-এর ক্ষমতার আলাদা অংশ (`CAP_*`) |
| Effective / Permitted / Bounding / Ambient | Capability set: এখন সক্রিয় / পেতে পারে / সর্বোচ্চ সীমা / non-root program-এ উত্তরাধিকার |
| File capability | Binary-তে বসানো capability (`setcap`) |
| seccomp | Process কোন system call করতে পারবে তার filter |
| Privileged container | সব capability, seccomp বন্ধ, device access — প্রায় host root |
| Container escape | Container থেকে host-এর নিয়ন্ত্রণ পাওয়া |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Namespace-এর system call

- `clone(CLONE_NEWPID | CLONE_NEWNET | ...)` — নতুন process নতুন namespace-এ জন্মায়।
- `unshare(...)` — বর্তমান process নিজেকে নতুন namespace-এ সরায়।
- `setns(fd)` — `/proc/PID/ns/net`-এর মত file খুলে সেই namespace-এ যোগ দেওয়া (`nsenter`)।

প্রতিটি namespace-এর একটি **inode নম্বর** আছে (`net:[4026531840]`) — দুটি process-এর নম্বর একই হলে তারা একই namespace share করে। এই lesson-এর `ns` command ঠিক এই তুলনা করে।

### 8.2 cgroup v2

```text
/sys/fs/cgroup/
├── system.slice/
│   ├── ssh.service/
│   └── taskflow-demo.service/      ← L01-10-এর service
│       ├── cgroup.procs            ← কোন PID-গুলো এখানে
│       ├── memory.max              ← MemoryMax=128M → 134217728
│       ├── memory.current          ← এখন কত ব্যবহার
│       ├── cpu.max                 ← CPUQuota=50% → "50000 100000"
│       └── pids.max
└── user.slice/
```

systemd প্রতিটি service-এর জন্য cgroup তৈরি করে (L01-10); `MemoryMax=`, `CPUQuota=` আসলে এই file-গুলোতে লেখে। Docker/Kubernetes-এর `--memory`, resource limit একই mechanism।

`cpu.max = "50000 100000"` মানে প্রতি ১০০ ms-এ ৫০ ms CPU সময় — অর্থাৎ একটি core-এর ৫০%। সীমায় পৌঁছালে process **throttle** হয় (অপেক্ষা করে) — মরে না; memory সীমায় পৌঁছালে OOM-এ **মরে** (L01-09)। এই পার্থক্য production-এ গুরুত্বপূর্ণ।

### 8.3 Capability-র hex bitmask

`/proc/PID/status`-এ `CapEff: 00000000a80425fb` — প্রতিটি bit একটি capability (bit ০ = `CHOWN`, bit ১০ = `NET_BIND_SERVICE`, bit ২১ = `SYS_ADMIN` ...)। Hex থেকে bit বের করা:

`0x400` = ১০২৪ = ২¹⁰ → শুধু bit ১০ → `CAP_NET_BIND_SERVICE` (এই lesson-এর tool-এ আসলে যাচাই করা)।

### 8.4 Service-কে root ছাড়া বিশেষ অধিকার

L01-10-এর service port ৮০-এ শুনতে চাইলে root নয়:

```ini
[Service]
User=taskflow
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
```

`AmbientCapabilities=` non-root process-কে একটি capability দেয়; `CapabilityBoundingSet=` সর্বোচ্চ সীমা — অন্য কিছু কখনো পাবে না। `setcap` দিয়ে binary-তে capability বসানোর চেয়ে নিরাপদ (Python interpreter-এ setcap দিলে **সব** Python script সেই অধিকার পায়!)।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 Namespace — নিজে একটি "mini container"

```bash
sudo unshare --pid --fork --mount-proc --uts --net bash
# এখন নতুন namespace-এ:
ps aux                  # শুধু bash ও ps — PID 1 = bash
hostname lab-box; hostname
ip link                 # শুধু lo (DOWN) — কোনো network নেই
exit
hostname                # host-এর hostname অপরিবর্তিত
```

| Option | অর্থ |
|---|---|
| `--pid --fork` | নতুন PID namespace; `--fork` দরকার যাতে child PID 1 হয় |
| `--mount-proc` | নতুন `/proc` mount — না হলে `ps` host-এর process দেখাত |
| `--uts` | আলাদা hostname |
| `--net` | আলাদা network (শুধু loopback) — L02-13-এ veth দিয়ে সংযোগ করবেন |

**Namespace তুলনা:**

```bash
sudo unshare --net --uts sleep 300 &
PID=$!
ls -l /proc/1/ns > /tmp/host-ns.txt
sudo ls -l /proc/$PID/ns > /tmp/other-ns.txt
python3 ~/devops-ai-engineering/01-linux-systems/code/L01-16/caps_ns.py ns /tmp/host-ns.txt /tmp/other-ns.txt
sudo nsenter --target $PID --net ip link      # সেই process-এর network namespace-এ command
sudo kill $PID
```

> Ubuntu 23.10+ AppArmor দিয়ে **unprivileged** user namespace সীমিত করে (`kernel.apparmor_restrict_unprivileged_userns`) — sudo ছাড়া `unshare --user` কিছু কাজে "Operation not permitted" দিতে পারে। এই lesson-এর experiment sudo দিয়ে। (Fedora-তে এই সীমা default নয়।)

**নমুনা data দিয়ে আসল output** ([host](code/L01-16/sample-ns-host.txt) বনাম [container](code/L01-16/sample-ns-container.txt)):

```text
  cgroup             ISOLATED
  ipc                ISOLATED
  mnt                ISOLATED
  net                ISOLATED
  pid                ISOLATED
  time               shared
  user               shared
  uts                ISOLATED
```

`user` shared — container-এর root আসলে **host-এর root** (UID 0)! Rootless বা user-namespace-সক্রিয় container (Podman rootless, L10-07) এই ঝুঁকি কমায়।

### 9.2 cgroup দেখা

```bash
systemd-cgls --no-pager | head -30            # cgroup tree
systemd-cgtop -n 1                            # কোন cgroup কত resource
cat /proc/self/cgroup                         # এই shell কোন cgroup-এ
python3 ~/devops-ai-engineering/01-linux-systems/code/L01-16/caps_ns.py cgroup /proc/self/cgroup
```

L01-10-এর `taskflow-demo` চালু থাকলে:

```bash
CG=/sys/fs/cgroup/system.slice/taskflow-demo.service
cat $CG/memory.max $CG/memory.current $CG/cpu.max $CG/cgroup.procs
```

প্রত্যাশিত (উদাহরণ): `134217728` (১২৮ MiB), বর্তমান ব্যবহার, `50000 100000`, PID।

**CPU throttling নিজে দেখুন:**

```bash
sudo systemd-run --scope -p CPUQuota=20% timeout 20 sh -c 'while :; do :; done' &
sleep 5; top -b -n 1 | grep ' sh$'            # %CPU প্রায় ২০-এ আটকে
wait
```

### 9.3 Capability

```bash
grep Cap /proc/self/status                    # সাধারণ user: CapEff 0
sudo grep Cap /proc/1/status                  # systemd: প্রায় সব
capsh --decode=00000000a80425fb               # native decode
python3 ~/devops-ai-engineering/01-linux-systems/code/L01-16/caps_ns.py caps 00000000a80425fb
getcap /usr/bin/ping 2>/dev/null; ls -l /usr/bin/ping   # ping setuid নয়, file capability বা অন্য পদ্ধতি
```

**আসল output (repository-তে চালানো):**

```text
14 capability(ies): CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_FOWNER, CAP_FSETID, CAP_KILL, CAP_SETGID, CAP_SETUID, CAP_SETPCAP, CAP_NET_BIND_SERVICE, CAP_NET_RAW, CAP_SYS_CHROOT, CAP_MKNOD, CAP_AUDIT_WRITE, CAP_SETFCAP
```

এই ১৪টি হুবহু Docker-এর documented default capability তালিকা — tool-এর সঠিকতার একটি স্বাধীন প্রমাণ। `capsh --decode`-এর ফলের সাথে মিলিয়ে দেখুন।

**Process-এর ঝুঁকি audit:**

```bash
python3 caps_ns.py status sample-status-container.txt     # exit 0 — ঝুঁকিপূর্ণ capability নেই
python3 caps_ns.py status sample-status-privileged.txt    # exit 1 — RISK তালিকা (Section 5)
sudo cat /proc/$(pgrep -o sshd)/status > /tmp/st.txt && python3 caps_ns.py status /tmp/st.txt
```

> **Fedora-তে:** একই command; `capsh` package `libcap`। Container-এ AppArmor-এর জায়গায় SELinux label (`container_t`) কাজ করে (L01-17)।

### 9.4 Test

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-16
python3 -m unittest -v
```

[`test_caps_ns.py`](code/L01-16/test_caps_ns.py)-এর ৬টি test: Docker default mask = documented ১৪টি, একক bit (NET_BIND_SERVICE, SYS_ADMIN), পূর্ণ ৪১টি ও অজানা bit, container বনাম privileged status-এর exit code, namespace তুলনা (time ও user shared), cgroup v2 path ও v1 প্রত্যাখ্যান।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `CAPS` তালিকা, index = bit | kernel header-এর ক্রম | Bitmask decode-এর ভিত্তি |
| `mask >> bit & 1` | প্রতিটি bit পরীক্ষা | Bitwise |
| `unknown = mask >> len(CAPS)` | নতুন kernel-এর নতুন capability | নীরবে বাদ না দিয়ে report |
| `NS_RE` | `net -> 'net:[4026531840]'` | `ls -l`-এর quote থাকা বা না থাকা দুটোই |
| `parse_cgroup`: `0::` | cgroup v2-এর একমাত্র লাইন | v1 system-এ স্পষ্ট error |
| `DANGEROUS` dict | ব্যাখ্যাসহ ঝুঁকি | শুধু নাম নয়, কেন ঝুঁকিপূর্ণ |

### Python কেন এখানে, আর কোথায় নয়

Namespace তৈরি বা cgroup সীমা বসানো হয় native tool (`unshare`, systemd, Docker) দিয়ে — Python এখানে **পর্যবেক্ষণ ও audit**-এর কাজ করে: hex মান, inode নম্বর ও path-কে মানুষের পাঠযোগ্য সিদ্ধান্তে রূপান্তর।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `unshare --pid --fork --mount-proc bash`-এ `ps` | PID 1 = bash |
| `unshare --net`-এ `ip link` | শুধু `lo` |
| CPUQuota=20%-এ `top` | ~২০% |
| `caps a80425fb` | ১৪টি, Docker default-এর সাথে মেলে |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `unshare: unshare failed: Operation not permitted` | Unprivileged user namespace সীমা (Ubuntu) | `sysctl kernel.apparmor_restrict_unprivileged_userns` | Lab-এ sudo; production-এ নীতি বুঝে |
| নতুন PID namespace-এ `ps` host দেখায় | `--mount-proc` নেই | — | `--mount-proc` |
| Container-এ "Operation not permitted" | Capability বা seccomp | `CapEff` decode; audit log | নির্দিষ্ট `--cap-add`, privileged নয় |
| App ধীর, CPU কম ব্যবহার | cgroup CPU throttling | `cat cpu.stat` (`nr_throttled`) | সীমা বাড়ানো বা কাজ কমানো |
| `/sys/fs/cgroup/memory/` নেই | cgroup v2 (unified) | `stat -fc %T /sys/fs/cgroup` = `cgroup2fs` | v2 path ব্যবহার করুন |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Container = একই kernel → kernel patch জরুরি (L01-18)। `--privileged` ও `CAP_SYS_ADMIN` এড়িয়ে চলুন; capability drop করুন (`--cap-drop ALL` তারপর দরকারিগুলো যোগ — Module 09 template-এ আছে)। User namespace/rootless container (container-এর root ≠ host-এর root)। seccomp ও AppArmor/SELinux চালু রাখুন।
- **Performance:** Namespace-এর overhead প্রায় নেই; cgroup CPU সীমা throttling-এ latency বাড়াতে পারে (p99, L00-06) — Kubernetes-এ CPU limit নিয়ে বিতর্কের কারণ (Module 14)।
- **Cost:** cgroup সীমা দিয়ে একই host-এ বেশি workload নিরাপদে — কম server (bin packing)।

## 14. Hands-on exercise

1. `unshare` দিয়ে PID, UTS, NET, MNT namespace-এ bash খুলে প্রতিটির প্রভাব যাচাই করুন। ভেতরে `mount -t tmpfs none /mnt` করলে host-এ কি দেখা যায়?
2. দুটি `unshare --net` process তৈরি করে `caps_ns.py ns` দিয়ে দেখান তারা পরস্পর থেকেও আলাদা।
3. L01-10-এর service-এ `AmbientCapabilities=CAP_NET_BIND_SERVICE` দিয়ে port ৮০-এ চালান (non-root)। `/proc/<PID>/status` decode করে যাচাই করুন শুধু সেটিই আছে।
4. `caps_ns.py`-তে `diff MASK_A MASK_B` command যোগ করুন — কোন capability যোগ/বাদ। Test লিখুন।
5. Docker installed থাকলে (Module 09-এর আগে ঐচ্ছিক): `docker run --rm alpine grep Cap /proc/1/status` ও `--privileged` দিয়ে তুলনা করুন।

## 15. Mini-project — "container from scratch" নোট

শুধু `unshare`, একটি ছোট root filesystem (যেমন Alpine minirootfs tarball `/tmp/rootfs`-এ extract) ও `chroot` দিয়ে একটি অতি সরল "container" চালান: আলাদা PID/UTS/NET/MNT namespace, `systemd-run --scope -p MemoryMax=50M`, এবং ভেতরে `ps`, `hostname`, `ip link` দেখান। Notebook-এ লিখুন Docker এর তুলনায় কী নেই (image layer, network সংযোগ, capability drop, seccomp, logging) — Module 09-এ প্রতিটি দেখবেন। ⚠️ শুধু VM-এ।

## 16. Interview প্রশ্ন

1. Container ও VM-এর মূল পার্থক্য কী? Container-এর isolation কোন kernel feature দিয়ে?
2. Namespace ও cgroup-এর পার্থক্য কী?
3. Linux capability কী? `CAP_SYS_ADMIN` কেন বিপজ্জনক?
4. Privileged container কী এবং কেন এড়ানো উচিত?
5. Container-এর root কি host-এর root? কীভাবে আলাদা করা যায়?
6. CPU limit ও memory limit ছাড়ালে কী আলাদা ঘটে?
7. Non-root service-কে port ৮০ খুলতে দিতে কী করবেন?

## 17. Self-assessment প্রশ্ন

1. অ্যাপার্টমেন্ট analogy কোথায় মেলে না?
2. Section 5-এর সঠিক least-privilege সমাধান কী?
3. `0x400` কেন `CAP_NET_BIND_SERVICE`? হাতে হিসাব দেখান।
4. নমুনা namespace তুলনায় `user` shared — এর নিরাপত্তা অর্থ কী?
5. `cpu.max = "50000 100000"`-এর অর্থ।
6. Python interpreter-এ `setcap` দেওয়া কেন খারাপ ধারণা?

## 18. সংক্ষিপ্ত সারাংশ

- Container = **namespace** (কী দেখে) + **cgroup** (কতটা পায়) + **capability** (কী পারে) + seccomp + LSM + overlay filesystem — একই kernel।
- Namespace-এর inode নম্বর দিয়ে share/আলাদা বোঝা যায়; `unshare`, `nsenter`।
- cgroup v2 `/sys/fs/cgroup`: CPU সীমায় throttle, memory সীমায় OOM।
- Capability: root-এর ক্ষমতা ভাঙা; `CapEff` hex decode; `AmbientCapabilities=` দিয়ে non-root-কে নির্দিষ্ট অধিকার; privileged/`SYS_ADMIN` এড়ান।

## 19. Completion checklist

- [ ] `unshare` দিয়ে PID/UTS/NET namespace-এর প্রভাব দেখেছি
- [ ] `nsenter` ও namespace তুলনা করেছি
- [ ] `systemd-cgls`, cgroup file, CPU throttling দেখেছি
- [ ] `capsh --decode` ও Python decode মিলিয়েছি
- [ ] Non-root service-কে `AmbientCapabilities` দিয়ে port ৮০ দিয়েছি (Exercise ৩)
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `namespaces(7)`: https://man7.org/linux/man-pages/man7/namespaces.7.html
- `cgroups(7)`: https://man7.org/linux/man-pages/man7/cgroups.7.html
- Kernel docs — cgroup v2: https://docs.kernel.org/admin-guide/cgroup-v2.html
- `capabilities(7)`: https://man7.org/linux/man-pages/man7/capabilities.7.html
- `unshare(1)`: https://man7.org/linux/man-pages/man1/unshare.1.html
- `nsenter(1)`: https://man7.org/linux/man-pages/man1/nsenter.1.html
- `systemd.exec(5)` — `AmbientCapabilities=`, `CapabilityBoundingSet=`: https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- Docker — runtime privilege and Linux capabilities: https://docs.docker.com/engine/containers/run/

---

**পরের lesson:** L01-17 — Mandatory access control: AppArmor (Ubuntu) ও SELinux (Fedora)
