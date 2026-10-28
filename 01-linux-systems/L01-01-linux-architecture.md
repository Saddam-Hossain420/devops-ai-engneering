# L01-01 — Linux architecture: kernel space, user space ও system call

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L00-07 — Lab environment setup](../00-orientation/L00-07-lab-environment-setup.md) (Ubuntu VM প্রস্তুত) |
| **Label** | — (সব command read-only বা temporary file-এ) |
| **Tested** | Python: ৫টি unit test পাস (Python 3.14, Windows)। `syscall_demo.py` Windows-এ চালানো হয়েছে; `strace`, `uname`, `/proc` command **Ubuntu-তে চালানো হয়নি** — Linux output-গুলো উদাহরণ হিসেবে চিহ্নিত। `sample-trace.txt` হাতে তৈরি করা উদাহরণ data (একটি সাধারণ `cat` trace-এর গঠন অনুসরণ করে), আসল capture নয়। |

---

## 1. এই lesson-এ যা শিখবেন

- Operating system-এর কাজ কী, এবং **kernel** কেন আলাদা।
- **Kernel space** ও **user space** — CPU-র privilege level দিয়ে কীভাবে আলাদা রাখা হয়।
- **System call** — user program কীভাবে kernel-এর কাছে কাজ চায়।
- **libc** ও Python-এর ভূমিকা: `print()` থেকে hardware পর্যন্ত পথ।
- **Linux distribution** কী: kernel + GNU tool + package manager + configuration।
- `uname`, `/proc`, `strace` দিয়ে নিজে kernel ও system call পর্যবেক্ষণ।
- Python দিয়ে system call ঘটানো এবং strace output-এর সারাংশ তৈরি।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি computer-এ একসাথে শত শত program চলে: browser, editor, web server, database। সবাই একই CPU, memory, disk, network card ব্যবহার করে। যদি প্রতিটি program সরাসরি hardware-এ হাত দিতে পারত:

- একটি buggy program অন্য program-এর memory-তে লিখে সেটিকে crash করাতে পারত।
- দুটি program একসাথে disk-এর একই জায়গায় লিখে data নষ্ট করত।
- যেকোনো program অন্য user-এর file পড়তে পারত — কোনো নিরাপত্তা থাকত না।
- প্রতিটি program-কে প্রতিটি hardware-এর driver নিজেই লিখতে হতো।

**Kernel** এই সমস্যার সমাধান: hardware-এর একমাত্র "দারোয়ান"। Program-গুলো সরাসরি hardware ছোঁয় না; তারা **system call** দিয়ে kernel-কে অনুরোধ করে, kernel permission যাচাই করে কাজটি করে দেয়।

DevOps-এ এটি জানা জরুরি কারণ: container (Module 09) আসলে kernel-এর feature; "Permission denied", "Too many open files", "No such file or directory" — এসব error সরাসরি system call-এর ব্যর্থতা থেকে আসে; আর `strace` দিয়ে একটি অস্বচ্ছ program আসলে কী করছে দেখা যায় — production debugging-এর শক্তিশালী হাতিয়ার।

## 3. সহজ ভাষায় পরিচয়

**Kernel কী?** Operating system-এর কেন্দ্রীয় program, যা computer চালু হওয়ার পর থেকে বন্ধ হওয়া পর্যন্ত memory-তে থাকে এবং hardware, memory, process, file, network নিয়ন্ত্রণ করে।

**User space কী?** Kernel-এর বাইরের সব program — shell, Python, Nginx, আপনার script। এরা সীমিত অধিকারে চলে।

**System call কী?** User space program-এর kernel-এর কাছে কাজ চাওয়ার নির্দিষ্ট, নিয়ন্ত্রিত দরজা। যেমন `openat` (file খোলো), `read`, `write`, `clone` (নতুন process/thread), `socket` (network connection)। Linux-এ কয়েকশো system call আছে (architecture অনুযায়ী সংখ্যা আলাদা)।

**Linux আসলে কী?** কঠোর অর্থে "Linux" শুধু kernel। Ubuntu বা Fedora হলো **distribution**: Linux kernel + GNU core utility (`ls`, `cp`, Bash) + system library (glibc) + init system (systemd) + package manager (`apt`/`dnf`) + default configuration।

**কেন এভাবে তৈরি?** নিরাপত্তা (একটি program অন্যটিকে বা kernel-কে নষ্ট করতে পারে না), স্থিতিশীলতা (program crash করলে শুধু সেটিই মরে), এবং সরলতা (program-গুলো একই interface দিয়ে যেকোনো hardware ব্যবহার করতে পারে)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ব্যাংকের কাউন্টার

ব্যাংকের ভল্টে (hardware) গ্রাহক (user program) নিজে ঢুকতে পারেন না। তিনি কাউন্টারে (system call) একটি নির্দিষ্ট ফর্ম জমা দেন — "১০,০০০ টাকা তুলতে চাই"। ক্যাশিয়ার (kernel) পরিচয় ও balance যাচাই করেন (permission check), ভল্ট থেকে টাকা এনে দেন, অথবা কারণসহ প্রত্যাখ্যান করেন ("অপর্যাপ্ত balance" — যেমন `EACCES` বা `ENOENT` error)।

- কাউন্টারের ফর্মের ধরন নির্দিষ্ট — যেমন system call-এর তালিকা নির্দিষ্ট।
- গ্রাহক ক্যাশিয়ারের ভেতরের কাজ দেখেন না — যেমন program জানে না disk কোন model-এর।

### Analogy কোথায় মেলে না

- ব্যাংকে কাউন্টারে লাইন দিতে কয়েক মিনিট লাগে। System call **মাইক্রোসেকেন্ড বা তার কম** সময়ে হয় — তবু function call-এর তুলনায় ব্যয়বহুল, কারণ CPU-কে mode বদলাতে হয়। তাই program-গুলো অনেক ছোট `write`-এর বদলে buffer জমিয়ে একবারে লেখে।
- ক্যাশিয়ার একজন মানুষ, একবারে একজন গ্রাহক। Kernel **একসাথে বহু CPU core-এ** বহু system call সামলায়।
- গ্রাহক কাউন্টারে গেলে অপেক্ষা করেন। Kernel কখনো program-কে "ঘুম পাড়িয়ে" (block) অন্য program চালায়, data এলে জাগায় — এটি scheduler-এর কাজ (L01-09)।

## 5. Real-world engineering scenario — "file আছে, তবু app বলছে নেই"

**পরিস্থিতি:** একটি Python service চালু হতে গিয়ে crash করছে: `FileNotFoundError: config.yaml`। Engineer নিশ্চিত — `/etc/myapp/config.yaml` আছে।

**জড়িত component:** application, filesystem, kernel-এর `openat` system call।

**ঘটনার ক্রম ও diagnosis:**

1. Log-এ শুধু "config.yaml not found" — কোন path-এ খুঁজেছে লেখা নেই।
2. Engineer service-টি `strace` দিয়ে চালালেন, শুধু file খোলার call দেখতে:

   ```bash
   strace -f -e trace=openat python3 app.py
   ```

3. Output-এ দেখা গেল (উদাহরণ):

   ```text
   openat(AT_FDCWD, "config.yaml", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
   ```

4. Path relative — `config.yaml`, `/etc/myapp/config.yaml` নয়। Program খুঁজছে **current working directory**-তে। Terminal থেকে চালালে কাজ করত (engineer `/etc/myapp`-এ ছিলেন), কিন্তু systemd service-এর working directory আলাদা (`/`)।
5. সমাধান: code-এ absolute path বা configurable path; systemd unit-এ `WorkingDirectory=` (L01-10)।

**শিক্ষা:** Application-এর error message অসম্পূর্ণ হতে পারে, কিন্তু **system call মিথ্যা বলে না**। `strace` দেখায় program আসলে kernel-কে কী জিজ্ঞেস করেছে এবং kernel কী উত্তর দিয়েছে।

## 6. Diagram

### Linux-এর স্তর

```text
 ┌──────────────────────────── USER SPACE (ring 3, সীমিত অধিকার) ───────────────────────────┐
 │                                                                                             │
 │   bash      python3 app.py      nginx       systemd (PID 1)      sshd                       │
 │     │            │                 │              │                │                        │
 │     └────────────┴──── glibc (C library: open(), printf(), malloc()) ────────────────┘      │
 │                                    │                                                        │
 ├──────────────────── system call interface (syscall instruction) ────────────────────────────┤
 │                                    ▼                                                        │
 │ ┌──────────────────────── KERNEL SPACE (ring 0, পূর্ণ অধিকার) ───────────────────────────┐ │
 │ │  Process scheduler │ Memory manager │ VFS + filesystems │ Network stack │ Security (LSM) │ │
 │ │                          Device drivers (disk, NIC, GPU ...)                            │ │
 │ └──────────────────────────────────────────────────────────────────────────────────────────┘ │
 └───────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                             ▼
                          HARDWARE: CPU · RAM · Disk · Network card
```

### `print("hello")` থেকে screen পর্যন্ত

```text
Python: print("hello")
   └─► sys.stdout.write("hello\n")            (Python-এর buffer)
         └─► os.write(1, b"hello\n")          (flush হলে)
               └─► glibc write(1, ...)
                     └─► syscall instruction ── CPU user mode → kernel mode
                           └─► kernel: fd 1 কোথায় যুক্ত? (terminal / file / pipe)
                                 └─► terminal driver ─► screen-এ লেখা
                     ◄── return 6 (লেখা byte সংখ্যা) ── kernel mode → user mode
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Kernel | OS-এর কেন্দ্র; hardware ও resource নিয়ন্ত্রণ করে |
| Kernel space | Kernel যে memory ও privilege level-এ চলে |
| User space | সাধারণ program-এর সীমিত পরিবেশ |
| Privilege level / ring | CPU-র অধিকারের স্তর; x86-এ ring 0 = kernel, ring 3 = user |
| System call (syscall) | User program থেকে kernel-এর কাছে নির্দিষ্ট অনুরোধ |
| glibc | GNU C Library — বেশিরভাগ program system call এর মাধ্যমে করে |
| File descriptor (fd) | একটি খোলা file/socket/pipe-এর জন্য kernel-এর দেওয়া ছোট সংখ্যা; 0 = stdin, 1 = stdout, 2 = stderr |
| errno | System call ব্যর্থ হলে কারণ জানানো সংখ্যা (যেমন `ENOENT` = file নেই, `EACCES` = permission নেই) |
| Context switch / mode switch | CPU-র user mode ও kernel mode-এর মধ্যে বদল |
| `/proc` | Kernel-এর তথ্য file আকারে দেখানো virtual filesystem (disk-এ নেই) |
| Distribution | Kernel + tool + package manager + configuration-এর পূর্ণ OS |
| strace | একটি program-এর system call ধরে দেখানোর tool |
| Kernel module | চলমান kernel-এ যোগ করা যায় এমন code (যেমন driver) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Privilege separation

আধুনিক CPU-তে hardware-স্তরের নিয়ম আছে: **user mode**-এ চলা code কিছু instruction চালাতে পারে না (যেমন hardware সরাসরি নিয়ন্ত্রণ, page table বদলানো) এবং kernel-এর memory পড়তে পারে না। চেষ্টা করলে CPU একটি **exception** তৈরি করে, kernel সেই process-কে signal পাঠায় (সাধারণত `SIGSEGV` — "Segmentation fault")। নিরাপত্তা তাই শুধু software-এর ভরসায় নয়, hardware দিয়ে বাধ্যতামূলক।

### 8.2 System call-এর ধাপ (x86-64 Linux, সরলীকৃত)

1. Program (সাধারণত glibc-এর মাধ্যমে) system call নম্বর একটি register-এ এবং argument অন্য register-এ রাখে।
2. `syscall` instruction চালায় → CPU kernel mode-এ যায়, kernel-এর নির্দিষ্ট entry point-এ লাফ দেয়।
3. Kernel নম্বর দেখে সঠিক handler চালায়; argument ও permission যাচাই করে।
4. কাজ শেষে ফল একটি register-এ রাখে (সফল হলে ≥ 0, ব্যর্থ হলে negative error code, যা glibc `-1` ও `errno`-তে রূপান্তর করে)।
5. CPU user mode-এ ফেরে।

### 8.3 সাধারণ system call পরিবার

| পরিবার | উদাহরণ | কোথায় দেখবেন |
|---|---|---|
| File | `openat`, `read`, `write`, `close`, `newfstatat`, `unlink` | এই lesson, L01-03 |
| Process | `clone`, `execve`, `wait4`, `exit_group`, `kill` | L01-08 |
| Memory | `mmap`, `brk`, `munmap` | L01-09 |
| Network | `socket`, `connect`, `accept`, `sendto` | Module 02 |
| Namespace/cgroup | `unshare`, `setns`, `clone3` | L01-16, Module 09 |

### 8.4 `/proc` — kernel-এর জানালা

`/proc`-এর file disk-এ নেই; পড়ার মুহূর্তে kernel তৈরি করে দেয়। যেমন `/proc/version` (kernel version), `/proc/cpuinfo`, `/proc/meminfo`, `/proc/<PID>/status`। L00-07-এর `check_env.py` এগুলোই পড়ত।

### 8.5 Failure behavior ও performance

- System call ব্যর্থ হলে program-এর কাছে শুধু errno আসে; program সেটি কীভাবে দেখাবে (বা লুকাবে) তা program-এর উপর নির্ভর করে।
- প্রতিটি system call-এ mode switch-এর খরচ আছে। খুব ছোট ছোট অনেক `write` ধীর; তাই buffering। `strace -c` দিয়ে কোন call-এ সময় যাচ্ছে মাপা যায়।
- `strace` নিজে program-কে অনেক ধীর করে (প্রতিটি call-এ থামিয়ে দেখে) — production-এ সাবধানে ও অল্প সময়ের জন্য ব্যবহার করুন।

## 9. Practical demonstration (Ubuntu VM-এ)

### 9.1 Kernel ও distribution চেনা

```bash
uname -r                 # চলমান kernel-এর version
uname -a                 # সব তথ্য: kernel নাম, hostname, version, architecture
cat /etc/os-release      # distribution-এর তথ্য
cat /proc/version        # kernel build-এর তথ্য, kernel নিজে জানায়
```

সবগুলো শুধু পড়ে। উদাহরণ output (আপনার version ভিন্ন হবে):

```text
6.8.0-45-generic
Linux devlab 6.8.0-45-generic #45-Ubuntu SMP PREEMPT_DYNAMIC ... x86_64 x86_64 x86_64 GNU/Linux
```

`6.8.0` = upstream kernel version; `-45-generic` = Ubuntu-র নিজস্ব build নম্বর ও flavor। Kernel ও distribution আলাদা জিনিস — একই Ubuntu version-এ kernel update হতে পারে (HWE kernel)।

> **Fedora-তে:** একই command; kernel নামে `fc41` জাতীয় অংশ থাকে (যেমন `6.11.4-301.fc41.x86_64`)। Fedora সাধারণত upstream-এর নতুন kernel দ্রুত দেয়।

### 9.2 প্রথম strace

```bash
sudo apt install -y strace       # (একবার; system-এ package যোগ করে)
strace -c cat /etc/hostname      # -c: system call-এর সংখ্যা ও সময়ের সারাংশ
```

এরপর বিস্তারিত, file-এ:

```bash
strace -o /tmp/trace.txt cat /etc/hostname
head -20 /tmp/trace.txt
```

| Option | অর্থ |
|---|---|
| `-c` | প্রতিটি call-এর গণনা ও সময়ের table (call দেখায় না) |
| `-o FILE` | Output terminal-এর বদলে file-এ |
| `-f` | Child process ও thread-ও trace করে |
| `-e trace=openat,read` | শুধু নির্দিষ্ট call |
| `-p PID` | চলমান process-এ যুক্ত হওয়া (⚠️ অন্য user-এর process-এ `sudo` লাগে; production-এ সাবধানে) |

> **Fedora-তে:** `sudo dnf install -y strace`।

### 9.3 Python থেকে system call — নিজে দেখুন

File: [`code/L01-01/syscall_demo.py`](code/L01-01/syscall_demo.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-01
python3 syscall_demo.py
```

Script একটি temporary directory-তে file খোলে, লেখে, `fsync`, বন্ধ, `stat`, একটি নেই এমন file খোলার চেষ্টা, তারপর মুছে ফেলে। কিছু রেখে যায় না।

**এই repository-তে (Windows-এ) চালিয়ে পাওয়া আসল output** (PID আপনার ভিন্ন হবে):

```text
getpid -> 27724
open -> file descriptor 3
write -> 13 bytes
fsync -> data flushed to storage
close -> fd released
stat -> size 13
open missing -> errno 2 (No such file or directory)
unlink -> file removed
```

লক্ষ্য করুন: নতুন খোলা file পেল **fd 3** — কারণ 0, 1, 2 আগে থেকেই stdin, stdout, stderr। আর missing file-এ **errno 2 = ENOENT**।

এখন strace দিয়ে একই script (Ubuntu-তে):

```bash
strace -f -e trace=openat,write,fsync,close,unlink python3 syscall_demo.py 2>&1 | grep -E 'demo\.txt|missing|hello'
```

`2>&1` = strace-এর output (stderr) ও program-এর output একসাথে; `grep` শুধু প্রাসঙ্গিক লাইন রাখে। প্রত্যাশিত গঠন (উদাহরণ, path ভিন্ন হবে):

```text
openat(AT_FDCWD, "/tmp/syscall-demo-xxxx/demo.txt", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0600) = 3
write(3, "hello kernel\n", 13)          = 13
openat(AT_FDCWD, "/tmp/syscall-demo-xxxx/missing.txt", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
unlink("/tmp/syscall-demo-xxxx/demo.txt") = 0
```

প্রতিটি Python লাইন (`os.open`, `os.write`, `os.unlink`) সরাসরি একটি system call হয়ে দেখা দিচ্ছে। Python startup নিজেও শত শত call করে (module load) — তাই `grep` দিয়ে ছাঁকা।

**একটি platform শিক্ষা (এই repository লেখার সময় পাওয়া):** প্রথম version-এ Windows-এ `stat` দেখিয়েছিল ১৪ byte, যদিও ১৩ byte লেখা হয়েছিল — কারণ Windows-এ `os.open` default-ভাবে **text mode**-এ `\n`-কে `\r\n` করে দেয়। Linux kernel file-কে শুধু byte-এর ধারা হিসেবে দেখে, text/binary পার্থক্য নেই। Code-এ `O_BINARY` (শুধু Windows-এ আছে) যোগ করে ঠিক করা হয়েছে।

### 9.4 strace output-এর সারাংশ

File: [`code/L01-01/strace_summary.py`](code/L01-01/strace_summary.py) · উদাহরণ data: [`sample-trace.txt`](code/L01-01/sample-trace.txt) (হাতে তৈরি, `cat /etc/hostname`-এর trace-এর গঠনে)

```bash
python3 strace_summary.py sample-trace.txt
```

**আসল output (sample data দিয়ে):**

```text
total system calls: 24   distinct: 10

most frequent:
      5  close
      4  openat
      4  newfstatat
      3  mmap
      3  read
      ...

failed calls (name, errno):
      1  access ENOENT
      1  openat ENOENT

files opened successfully:
  fd=  3  /etc/ld.so.cache
  fd=  3  /lib/x86_64-linux-gnu/libc.so.6
  fd=  3  /etc/hostname
```

**ব্যাখ্যা:** `cat`-এর মতো ছোট program-ও আসল কাজের (hostname পড়া ও লেখা) আগে dynamic linker দিয়ে `libc.so.6` load করে। আর সব "ব্যর্থ" call সমস্যা নয় — `/etc/ld.so.preload` না থাকা স্বাভাবিক। **ENOENT দেখলেই আতঙ্কিত হবেন না; প্রাসঙ্গিক path-টি খুঁজুন।**

নিজের আসল trace দিয়ে চালান:

```bash
strace -f -o /tmp/trace.txt python3 syscall_demo.py
python3 strace_summary.py /tmp/trace.txt
rm /tmp/trace.txt
```

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l01_01.py`](code/L01-01/test_l01_01.py)-এর ৫টি test: demo-র ধাপ ও cleanup, সফল/ব্যর্থ strace লাইন parse, PID prefix ও noise লাইন, sample trace-এর গণনা, ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `os.open(path, flags, 0o600)` | `openat` system call; mode 0600 = শুধু মালিক পড়া-লেখা | High-level `open()`-এর চেয়ে system call-এর কাছাকাছি; permission L01-04-এ |
| `os.O_WRONLY \| os.O_CREAT \| os.O_TRUNC` | Flag bit OR করে মেলানো | Kernel-এর flag argument ঠিক এভাবেই কাজ করে |
| `os.fsync(fd)` | Kernel-এর buffer থেকে disk-এ লেখা নিশ্চিত | `write` সফল মানেই disk-এ পৌঁছানো নয় — database ও backup-এ গুরুত্বপূর্ণ |
| `FileNotFoundError.errno` | Kernel-এর ENOENT Python exception-এ | Python exception-এর পেছনে system call-এর errno থাকে |
| `tempfile.TemporaryDirectory()` | শেষে স্বয়ংক্রিয়ভাবে মোছে | Demo কোনো আবর্জনা রেখে যায় না |
| `LINE_RE` | `name(args) = ret ERRNO` ধরে | strace-এর মূল format; `+++`/`---` লাইন বাদ |
| `errors="replace"` | অবৈধ byte-এ crash নয় | strace output-এ binary data থাকে |

### Python কেন এখানে, আর কোথায় নয়

System call-এর **ধারণা** দেখাতে Python সুবিধাজনক (`os` module প্রায় সরাসরি syscall)। কিন্তু **observation**-এর জন্য native tool `strace`-ই সঠিক — Python তা প্রতিস্থাপন করে না। Python এখানে strace-এর output বিশ্লেষণে সাহায্য করে।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `uname -r` | Kernel version |
| `strace -c true` | `exit_group`, `execve` সহ table (true প্রায় কিছুই করে না) |
| `python3 syscall_demo.py` | ৮টি ধাপ, `stat -> size 13`, `errno 2` |
| `python3 -m unittest -v` | `Ran 5 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `strace: command not found` | install নেই | `which strace` | `sudo apt install strace` |
| `strace: attach: ptrace(PTRACE_SEIZE, ...): Operation not permitted` | অন্য user-এর process, বা Ubuntu-র ptrace সীমা | `cat /proc/sys/kernel/yama/ptrace_scope` | নিজের চালু করা program trace করুন; অথবা প্রয়োজনে `sudo` (নিজের lab-এ) |
| Container-এ strace কাজ করে না | Container-এ ptrace সীমিত | — | Module 09-এ capability শিখবেন |
| trace output বিশাল | Python/Java-র startup | `wc -l` | `-e trace=...` ও `grep` দিয়ে ছাঁকুন |
| `Segmentation fault` | Program নিষিদ্ধ memory-তে হাত দিয়েছে (kernel থামিয়েছে) | `dmesg` বা `journalctl -k` | Bug — L01-14-এ debug |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Kernel-এ bug মানে পুরো system ঝুঁকিতে — তাই kernel security update জরুরি (L01-18)। Container সব একই kernel share করে, তাই container isolation VM-এর চেয়ে দুর্বল (Module 09)। `strace`-এ argument দেখা যায় — password থাকলে সেটিও দেখা যাবে; trace file শেয়ার করার আগে দেখে নিন।
- **Performance:** System call-এর খরচ; buffering; `strace` নিজে ধীর করে।
- **Cost:** নেই।

## 14. Hands-on exercise

1. `strace -c ls /etc` ও `strace -c ls -l /etc` তুলনা করুন। কোন call বেড়েছে? কেন (সংকেত: `-l` প্রতিটি file-এর metadata চায়)?
2. `strace -e trace=openat curl -s https://example.com -o /dev/null` চালিয়ে দেখুন DNS ও TLS-এর জন্য কোন config file খোলা হয় (`/etc/resolv.conf`, `/etc/ssl/...`)।
3. `syscall_demo.py`-তে একটি ধাপ যোগ করুন: `os.rename` দিয়ে file নাম বদলানো। strace-এ কোন system call দেখা যায়?
4. `strace_summary.py`-তে `--failed-only` option যোগ করুন এবং test লিখুন।
5. `/proc/self/status` পড়ে নিজের process-এর `Pid`, `PPid`, `Threads` দেখান (`cat /proc/self/status | head`)। `self` কোন process-কে বোঝায়?

## 15. Mini-project — "অস্বচ্ছ program-এর রহস্য"

একটি ছোট Python script লিখুন যা একটি hard-coded relative path থেকে config পড়ার চেষ্টা করে এবং শুধু "config error" দেখিয়ে exit করে (কোনো path বলে না)। তারপর অন্য কারো মতো ভান করে — কোড না দেখে — শুধু `strace` দিয়ে খুঁজে বের করুন কোন file খুঁজছে। Notebook-এ L00-06-এর experiment format-এ লিখুন।

## 16. Interview প্রশ্ন

1. Kernel space ও user space কী? কেন আলাদা?
2. System call কী? একটি উদাহরণ দিয়ে ধাপগুলো বলুন।
3. `strace` কী এবং কখন ব্যবহার করবেন? Production-এ ঝুঁকি কী?
4. File descriptor 0, 1, 2 কী?
5. Linux kernel ও Linux distribution-এর পার্থক্য কী?
6. Container কেন VM-এর মতো সম্পূর্ণ বিচ্ছিন্ন নয়?

## 17. Self-assessment প্রশ্ন

1. ব্যাংক analogy দিয়ে system call ব্যাখ্যা করুন, এবং analogy কোথায় মেলে না বলুন।
2. `print("hello")` থেকে screen পর্যন্ত ধাপগুলো লিখুন।
3. Section 5-এর বিভ্রান্তিকর `FileNotFoundError`-এর আসল কারণ কী ছিল এবং strace কীভাবে দেখাল?
4. নতুন খোলা file সাধারণত fd 3 পায় কেন?
5. `write` সফল হলেও data disk-এ নাও থাকতে পারে কেন? কোন call নিশ্চিত করে?
6. Sample trace-এ দুটি ENOENT ছিল — কোনোটি কি সমস্যা? কীভাবে বুঝলেন?

## 18. সংক্ষিপ্ত সারাংশ

- **Kernel** hardware-এর একমাত্র নিয়ন্ত্রক; **user space** program সীমিত অধিকারে চলে — CPU-র privilege level এটি বাধ্যতামূলক করে।
- Program kernel-এর কাছে কাজ চায় **system call** দিয়ে; ব্যর্থ হলে **errno** (ENOENT, EACCES ...)।
- Python → glibc → syscall → kernel → hardware।
- **Distribution** = kernel + GNU tool + library + systemd + package manager।
- **`strace`** দেখায় program আসলে kernel-কে কী বলছে — অস্বচ্ছ error-এর শক্তিশালী diagnosis tool।

## 19. Completion checklist

- [ ] `uname -a`, `/etc/os-release`, `/proc/version` দেখে kernel ও distribution আলাদা করতে পারি
- [ ] `strace -c` ও `strace -e trace=openat` নিজে চালিয়েছি
- [ ] `syscall_demo.py`-কে strace দিয়ে চালিয়ে প্রতিটি Python লাইনের system call মিলিয়েছি
- [ ] নিজের trace `strace_summary.py` দিয়ে বিশ্লেষণ করেছি
- [ ] `python3 -m unittest -v`-এ ৫টি test পাস
- [ ] Exercise ১ ও ২ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Linux kernel documentation: https://docs.kernel.org/
- `syscalls(2)` — Linux system call তালিকা: https://man7.org/linux/man-pages/man2/syscalls.2.html
- `strace(1)`: https://man7.org/linux/man-pages/man1/strace.1.html
- `errno(3)`: https://man7.org/linux/man-pages/man3/errno.3.html
- `proc(5)`: https://man7.org/linux/man-pages/man5/proc.5.html
- Python `os` module: https://docs.python.org/3/library/os.html

---

**পরের lesson:** L01-02 — Package management: apt, dpkg, repository (Fedora-তে dnf, rpm)
