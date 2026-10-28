# GLOSSARY — গুরুত্বপূর্ণ technical term

Term-গুলো English-এ রাখা হয়েছে (কারণ documentation, error message ও interview-এ এগুলোই ব্যবহার হয়), পাশে সহজ বাংলা ব্যাখ্যা। নতুন lesson-এ নতুন term এলে এখানে যোগ করা হবে। প্রথম module নম্বর বন্ধনীতে।

## A

- **AppArmor** profile ও **complain mode** — Ubuntu-তে program-ভিত্তিক path নিয়ম; complain = শুধু log, আটকায় না। (01)
- **ADR (Architecture Decision Record)** — একটি architecture সিদ্ধান্তের প্রেক্ষাপট, বিকল্প, সিদ্ধান্ত ও ফলাফলের ছোট লিখিত রেকর্ড; বদলালে নতুন ADR দিয়ে supersede। (00)
- **ACL (Access Control List)** — file বা network resource-এ কোন user/address কী করতে পারবে তার বিস্তারিত তালিকা। সাধারণ owner/group/other permission-এর চেয়ে সূক্ষ্ম। (01, 02)
- **Agent (AI)** — LLM-ভিত্তিক program যা লক্ষ্য পূরণে নিজে tool বেছে নিয়ে ধাপে ধাপে কাজ করে। (27)
- **Alert fatigue** — এত বেশি অপ্রয়োজনীয় alert যে engineer আসল alert উপেক্ষা করতে শুরু করে। (17)
- **API (Application Programming Interface)** — এক program অন্য program-এর সাথে কথা বলার নির্ধারিত নিয়ম। (05)
- **AppArmor** — Ubuntu-র default mandatory access control system; program-ভিত্তিক profile দিয়ে কোন file/capability ব্যবহার করা যাবে তা সীমিত করে। Fedora-তে এর জায়গায় SELinux। (01)
- **Artifact** — build-এর ফলাফল যা deploy করা হয়: container image, package, binary, model file। (11)
- **Availability Zone (AZ)** — একটি cloud region-এর ভেতরে আলাদা power ও network সহ এক বা একাধিক data center। (07)
- **ARP (Address Resolution Protocol)** — একই LAN-এ IP থেকে MAC address বের করা; IPv6-এ এর জায়গায় Neighbor Discovery। (02)
- **Authoritative DNS server** — একটি zone-এর আসল উত্তরদাতা (উত্তরে AA flag); recursive resolver এর কাছ থেকে জেনে cache করে। (02)
- **Annotated tag** — নিজস্ব object-যুক্ত tag (tagger, তারিখ, message, signature); release-এর জন্য। Lightweight tag শুধু একটি ref। (03)
- **Atomic rename** — একই filesystem-এ `mv`: পাঠক হয় পুরোনো, নয় সম্পূর্ণ নতুন file দেখে — আধা-লেখা কখনো নয়। (04)
- **ACME / HTTP-01 / DNS-01** — certificate স্বয়ংক্রিয়ভাবে নেওয়ার protocol (Let's Encrypt); domain-এর মালিকানা প্রমাণ web path বা TXT record দিয়ে। (06)
- **Apex (zone root)** — `example.com` নিজে (`@`); এখানে CNAME রাখা যায় না — A/AAAA বা provider-এর ALIAS। (06)

## B

- **Boot process** — UEFI → GRUB → kernel + initramfs → systemd → target। (01)
- **Blast radius** — একটি ভুল বা আক্রমণে ক্ষতি কতদূর ছড়াতে পারে; least privilege এটি ছোট রাখে। (01)
- **Build once, deploy many** — একবার build করা একই immutable artifact সব environment-এ promote করা; শুধু configuration আলাদা। (00)
- **Blue-green deployment** — দুটি পূর্ণ environment; নতুন version (green) তৈরি করে traffic একবারে সেখানে সরানো, সমস্যা হলে পুরোনো (blue)-তে ফেরা। (11)
- **Blameless postmortem** — incident-এর পরে ব্যক্তিকে দোষ না দিয়ে system ও process-এর দুর্বলতা খোঁজার লিখিত বিশ্লেষণ। (18)

- **Batch size** — একবারে কতগুলো পরিবর্তন একসাথে release হয়। ছোট batch = কম ঝুঁকি, সহজ debugging। (00)
- **Bastion / jump host** — private network-এ প্রবেশের একমাত্র নিয়ন্ত্রিত দরজা; `ssh -J`। (02)
- **Bridge (Linux)** — kernel-এর virtual L2 switch; Docker-এর `docker0`। (02)
- **BPF capture filter** — tcpdump-এ capture-এর সময় packet বাছাইয়ের syntax (`tcp port 443`); Wireshark display filter থেকে আলাদা। (02)
- **Bisect** — binary search দিয়ে কোন commit regression এনেছে তা খোঁজা; `git bisect run` স্বয়ংক্রিয়; test deterministic হতে হবে। (03)
- **Blob / tree (Git)** — file-এর content / directory-র তালিকা (নাম → mode + hash); দুটোই content-addressable object। (03)
- **bats-core** — Bash-এ লেখা test framework: `@test`, `run`, `$status`, `$output`। (04)

## C

- **cgroup** — process-গোষ্ঠীর CPU/memory/IO/pids সীমা ও হিসাব; CPU সীমায় throttle, memory সীমায় OOM। (01, 09)
- **cron** — পাঁচ field-এর সময়সূচিতে command চালানোর পুরোনো Unix scheduler; dom/dow দুটো দিলে OR নিয়ম। (01)
- **Configuration drift** — একই রকম হওয়ার কথা এমন server-গুলো সময়ের সাথে হাতে-করা পরিবর্তনে আলাদা হয়ে যাওয়া। (01, 12, 13)
- **C4 model** — Context, Container, Component, Code — চার স্তরের architecture diagram পদ্ধতি; C4 "container" মানে চলমান অংশ, Docker container নয়। (00)
- **Cycle time** — একটি কাজ শুরু (In progress) থেকে শেষ (Done) হতে কত সময় লাগে। (00)
- **CALMS** — DevOps-এর পাঁচ স্তম্ভ: Culture, Automation, Lean, Measurement, Sharing। (00)
- **Canary deployment** — নতুন version প্রথমে অল্প কিছু user/traffic-এ দেওয়া, metric ভালো থাকলে ধীরে বাড়ানো। (11)
- **Capability (Linux)** — root-এর বিশাল ক্ষমতাকে ছোট ছোট অংশে ভাগ করা (যেমন `CAP_NET_BIND_SERVICE` = 1024-এর নিচের port খোলা)। (01)
- **cgroup (control group)** — Linux kernel feature যা process-এর CPU, memory, I/O ব্যবহার সীমিত ও মাপে। Container-এর resource limit এর উপর দাঁড়িয়ে। (01)
- **CI (Continuous Integration)** — প্রতিটি code পরিবর্তন স্বয়ংক্রিয়ভাবে build ও test করা। (11)
- **CD (Continuous Delivery / Deployment)** — Delivery: যেকোনো সময় release-যোগ্য artifact তৈরি থাকে, deploy-এ মানুষের অনুমোদন লাগে। Deployment: test পাস করলে স্বয়ংক্রিয়ভাবে production-এ। (11)
- **CIDR** — IP address range লেখার পদ্ধতি, যেমন `10.0.0.0/24` = 256টি address। (02)
- **Container** — namespace ও cgroup দিয়ে আলাদা করা একটি process (বা process group), নিজের filesystem view সহ। Virtual machine নয়, host kernel share করে। (09)
- **Control loop / Reconciliation** — desired state ও actual state বারবার তুলনা করে পার্থক্য দূর করার প্রক্রিয়া। Kubernetes ও GitOps-এর মূল নীতি। (14, 16)
- **Certificate chain / chain of trust** — leaf → intermediate → trusted root CA; server-কে leaf ও intermediate পাঠাতে হয়। (02)
- **Chunked transfer encoding** — HTTP/1.1-এ আকার আগে না জেনে body টুকরো টুকরো পাঠানো (streaming)। (02)
- **Conntrack** — Linux kernel-এর connection tracking; stateful firewall-এর ভিত্তি (`ct state established`)। (02)
- **Connect timeout বনাম read timeout** — connection স্থাপনের সীমা বনাম উত্তরের অপেক্ষার সীমা; আলাদা না রাখলে 502/504 ভুল আসে। (02)
- **Consistent hashing** — hash ring + virtual node; node যোগ/বাদে শুধু ~১/N key সরে (modulo-তে প্রায় সব)। (02)
- **CODEOWNERS** — কোন path-এর জন্য কার review বাধ্যতামূলক; gitignore-ধাঁচের pattern, শেষ match জেতে। (03)
- **Commit (Git)** — root tree + parent(s) + author/committer + message-এর object; hash শৃঙ্খল history-কে tamper-evident করে। (03)
- **Conventional Commits** — `feat:`, `fix:`, `feat!:`/`BREAKING CHANGE:` message রীতি; স্বয়ংক্রিয় SemVer-এর ভিত্তি। (03)
- **Cardinality** — একটি field-এর ভিন্ন মানের সংখ্যা (path, user id); বেশি হলে log/metrics-এর memory ও খরচ বিস্ফোরিত হয় — `/tasks/{id}`-এর মতো normalize করুন। (05)
- **Circuit breaker** — পরপর ব্যর্থতার পরে কিছুক্ষণ কোনো request না পাঠানো, তারপর একটি পরীক্ষামূলক চেষ্টা; ব্যর্থ dependency-কে সেরে ওঠার সময় দেয়। (05, 18)
- **Command injection** — বাইরের মান shell string-এ বসে নতুন command হিসেবে চলা; প্রতিরোধ: list argument, shell নয় (`subprocess`), `--`। (05)
- **contextvars** — Python-এ thread/async-নিরাপদ "বর্তমান context"-এর মান (যেমন request id); নতুন thread খালি context পায় — `copy_context().run()` লাগে। (05)
- **Correlation / request id** — একটি কাজের সব log লাইন ও service জুড়ে একই ID; `X-Request-ID` header-এ client-কেও ফেরত দেওয়া হয়। (05, 17)
- **CAA record** — কোন CA এই domain-এর certificate দিতে পারবে (RFC 8659)। (06)
- **Catch-all default_server** — কোনো server_name না মিললে যে server; নিরাপদ রূপ `return 444`। (06)

## D

- **DAC বনাম MAC** — মালিক-নির্ধারিত permission বনাম কেন্দ্রীয় policy (AppArmor/SELinux), যার অধীন root-ও। (01)
- **Default ACL** — directory-তে রাখা ACL যা ভেতরের নতুন file উত্তরাধিকার পায়। (01)
- **Docs-as-code** — documentation Markdown-এ Git-এ রেখে PR review ও CI যাচাই দিয়ে পরিচালনা। (00)
- **DaemonSet** — Kubernetes object যা প্রতিটি (বা নির্বাচিত) node-এ একটি করে Pod চালায়। (14)
- **Data drift** — production-এ আসা data-র বৈশিষ্ট্য training data থেকে বদলে যাওয়া, ফলে model-এর মান কমে। (24)
- **DNS (Domain Name System)** — domain name-কে IP address-এ resolve করার distributed ব্যবস্থা। (02)
- **DORA metrics** — software delivery performance মাপার metric: deployment frequency, lead time for changes, change failure rate, failed deployment recovery time। (00)
- **Drift** — বাস্তব infrastructure-এর অবস্থা code/config-এ লেখা desired state থেকে সরে যাওয়া। (12)
- **DHCP** — স্বয়ংক্রিয়ভাবে IP, gateway, DNS দেওয়া; DORA (Discover-Offer-Request-Ack), lease, T1/T2। (02)
- **Default deny** — যা স্পষ্টভাবে অনুমোদিত নয় তা নিষিদ্ধ — firewall-এর নিরাপদ default policy। (02)
- **Dry-run** — কিছু না বদলে ঠিক কী করত তা দেখানো; আসল run-এর একই সিদ্ধান্তের পথ দিয়ে যেতে হবে। (04)
- **Daemon thread** — Python-এ যে thread-এর জন্য program শেষে অপেক্ষা করা হয় না; deadline-যুক্ত health check-এ লাগে (`ThreadPoolExecutor`-এর worker daemon নয়)। (05)
- **dataclass** — Python-এ field ঘোষণা থেকে `__init__`/`__repr__`/`__eq__` স্বয়ংক্রিয়; `frozen=True` = অপরিবর্তনীয় ও hashable। (05)

## E

- **Exit code** — program শেষে ফেরত দেওয়া ০–২৫৫ সংখ্যা; ০ = সফল, ১২৬/১২৭ = চালানো/খোঁজা যায়নি, ১২৮+N = signal N (১৩৭ = SIGKILL, ১৪৩ = SIGTERM)। (01)
- **errno** — system call ব্যর্থ হলে কারণ জানানো সংখ্যা (ENOENT = নেই, EACCES = অনুমতি নেই)। (01)
- **Environment parity** — dev/staging/prod-এর মধ্যে মিল: artifact, runtime version ও architecture একই রাখা। (00)
- **Environment variable** — process চালুর সময় OS থেকে পাওয়া key=value সেটিং; child process copy পায়। (00, 01)
- **Embedding** — text বা অন্য data-কে সংখ্যার vector-এ রূপান্তর, যাতে অর্থগত মিল দূরত্ব দিয়ে মাপা যায়। (25)
- **Error budget** — SLO অনুযায়ী অনুমোদিত ব্যর্থতার পরিমাণ (যেমন 99.9% SLO = 0.1% budget)। (18)
- **etcd** — Kubernetes cluster-এর সব state রাখা distributed key-value store। (14)
- **Ephemeral port** — client-এর অস্থায়ী source port (Linux-এ ৩২৭৬৮–৬০৯৯৯); stateless NACL-এ উত্তরের জন্য rule লাগে। (02)
- **Exponential backoff** — প্রতিটি ব্যর্থ চেষ্টার পরে অপেক্ষা দ্বিগুণ; সীমা ও jitter সহ retry। (04)
- **EX_TEMPFAIL (৭৫)** — `sysexits.h`-এর "সাময়িক ব্যর্থতা, পরে আবার চেষ্টা করুন" — যেমন অন্য run lock ধরে আছে। (04)
- **Event loop (nginx worker)** — একটি thread epoll দিয়ে হাজার non-blocking connection সামলায়; blocking কাজ পুরো worker থামায়। (06)

## F

- **File descriptor (fd)** — খোলা file/socket/pipe-এর জন্য kernel-এর দেওয়া ছোট সংখ্যা; 0 stdin, 1 stdout, 2 stderr। (01)
- **FHS (Filesystem Hierarchy Standard)** — Linux-এ কোন file কোন directory-তে থাকবে তার standard। (01)
- **Feedback loop** — কাজের ফলাফল থেকে তথ্য ফিরে এসে পরের কাজকে প্রভাবিত করার চক্র। যত ছোট ও দ্রুত, তত সস্তায় ভুল ঠিক হয়। (00)
- **Fast-forward** — target branch-এর নাম শুধু সামনে সরানো, merge commit ছাড়া; target যখন source-এর পূর্বপুরুষ। (03)
- **Force push / `--force-with-lease`** — remote-এর history overwrite / শুধু remote আপনার শেষ দেখা অবস্থায় থাকলে overwrite। (03)
- **flock** — file descriptor-এর উপর kernel advisory lock; process মারা গেলে নিজে মুক্ত হয়। (04)
- **Fail fast** — ভুল config বা input-এ শুরুতেই স্পষ্ট error দিয়ে থামা, ভুল অবস্থায় চলতে থাকা নয়। (05)
- **False positive / false negative** — ভুল সতর্কতা / ছুটে যাওয়া আসল সমস্যা; scanner ও alert-এ একটি কমালে অন্যটি বাড়ার ঝুঁকি। (05, 17, 19)
- **Fixture (pytest)** — test-এর জন্য প্রস্তুত করা অবস্থা বা object (`tmp_path`, নিজের fixture); `conftest.py`-তে shared। (05)
- **Flaky test** — একই code-এ কখনো পাস, কখনো ব্যর্থ; সাধারণ কারণ সময়, ক্রম, network, shared state। (05, 11)
- **fsync** — OS-এর buffer থেকে data disk-এ পাঠানো নিশ্চিত করা; atomic write-এ rename-এর আগে লাগে। (05)
- **FastCGI** — web server ও দীর্ঘজীবী application process-এর binary protocol; nginx `fastcgi_pass` → PHP-FPM। `SCRIPT_FILENAME` অপরিহার্য। (06)
- **Fullchain** — leaf + intermediate certificate (leaf আগে); nginx-এর `ssl_certificate`-এ এটাই। (06)

## G

- **Graceful shutdown** — SIGTERM পেয়ে চলমান কাজ শেষ করে পরিষ্কারভাবে বন্ধ হওয়া। (01, 09, 14)
- **Glob** — `*`, `?`, `[...]` দিয়ে shell-এর file নাম মেলানো। (01)
- **Goodhart's law** — কোনো মাপ লক্ষ্য হয়ে গেলে সেটি আর ভালো মাপ থাকে না; মানুষ metric "game" করতে শুরু করে। (00)
- **GitOps** — Git-এ রাখা desired state থেকে একটি agent স্বয়ংক্রিয়ভাবে cluster-কে মিলিয়ে রাখে। (16)
- **Golden path** — platform team-এর সুপারিশকৃত, পরীক্ষিত পথ যা developer-রা সহজে অনুসরণ করতে পারে। (16)
- **GITHUB_TOKEN** — প্রতি workflow run-এর স্বল্পমেয়াদি token; `permissions:` দিয়ে ন্যূনতম রাখুন। (03)
- **GitHub Actions** — GitHub-এর CI/CD: workflow (trigger) → job (runner) → step (`run`/`uses`)। (03)
- **getopts** — Bash/POSIX builtin: short option parsing (`-vn`, `-o FILE`); long option ও ক্রম বদল পারে না। (04)

## H

- **Hypothesis (engineering)** — ভুল প্রমাণযোগ্য, যাচাইযোগ্য অনুমান; experiment দিয়ে পরীক্ষা করা হয়। (00)
- **HTTP/2 ও HTTP/3** — HTTP/2: binary frame, একটি TCP connection-এ multiplexing; HTTP/3: UDP-ভিত্তিক QUIC-এর উপর, stream-স্তরের loss recovery। (02)
- **Health check (active/passive)** — LB নিজে নিয়মিত পরীক্ষা / আসল traffic-এর error দেখে backend সাময়িক বাদ। (02)
- **HEAD** — বর্তমান branch-এর symbolic ref (বা detached অবস্থায় সরাসরি commit)। (03)
- **HSTS** — `Strict-Transport-Security` header: browser নির্দিষ্ট সময় শুধু HTTPS ব্যবহার করে; nginx-এ `always` সহ। (06)

## I

- **initramfs** — boot-এর প্রথম অস্থায়ী root filesystem; আসল root (LVM, encryption) mount করার driver রাখে। (01)
- **Immutable infrastructure** — চলমান server বদলানোর বদলে নতুন image থেকে নতুন server। (01, 12)
- **Internal Developer Platform (IDP)** — developer-দের জন্য self-service tool, template ও workflow-এর সমষ্টি, যা platform team একটি product হিসেবে তৈরি করে। (00, 16)
- **Inference** — train করা model দিয়ে নতুন input-এ উত্তর বা prediction তৈরি করা। (00, 23)
- **IaC (Infrastructure as Code)** — infrastructure হাতে তৈরি না করে code দিয়ে বর্ণনা ও তৈরি করা। (12)
- **IAM (Identity and Access Management)** — কে (identity) কোন resource-এ কী করতে পারবে (permission) তার ব্যবস্থাপনা। (07)
- **Idempotency** — একই operation একাধিকবার চালালেও ফলাফল একবার চালানোর মতোই থাকে। (04, 13)
- **Immutable artifact** — একবার তৈরি হলে আর পরিবর্তন হয় না; নতুন পরিবর্তন মানে নতুন version। (11)
- **Inode** — Linux filesystem-এ file-এর metadata (permission, owner, size, data block-এর অবস্থান) রাখা structure; file name এতে থাকে না। (01)
- **ICMP** — network-এর error ও diagnostic বার্তা (echo, unreachable, time exceeded, fragmentation needed); সব block করলে PMTUD ভাঙে। (02)
- **Internet gateway / NAT gateway** — public IP-সহ instance-এর দুই দিকের Internet পথ / private instance-এর শুধু বাইরের দিকের পথ। (02)
- **IFS** — word splitting-এর বিভাজক; `"$*"` এর প্রথম অক্ষর দিয়ে জোড়া হয়। (04)
- **Idempotency key** — client-এর দেওয়া অনন্য ID; server একই key-র request আবার এলে কাজ না করে আগের ফল ফেরত দেয় — POST retry নিরাপদ করে। (05)

## J

- **journald / journalctl** — systemd-এর structured log service ও তা পড়ার command। (01, 17)
- **Jitter** — retry-র অপেক্ষায় এলোমেলোতা (full jitter: `random(0, min(cap, base·2ⁿ))`), যাতে সব client একসাথে না ফেরে। (05)

## K

- **Kanban** — WIP limit ও flow metric-ভিত্তিক ধারাবাহিক কাজের পদ্ধতি; operations ও platform team-এ প্রচলিত। (00)
- **Kernel** — OS-এর কেন্দ্রীয় অংশ যা hardware, memory, process ও device নিয়ন্ত্রণ করে। (01)
- **KV cache** — LLM inference-এ আগের token-এর attention হিসাব জমা রাখা memory; context বড় হলে VRAM ব্যবহার বাড়ে। (25)
- **Keep-alive (HTTP)** — একটি TCP connection-এ একাধিক request; proxy-র চেয়ে backend-এর idle timeout বেশি রাখতে হয়। (02)

## L

- **LVM (PV/VG/LV)** — disk-কে pool-এ জুড়ে নমনীয় volume; online বড় করা যায়, কিন্তু redundancy নয়। (01)
- **Load average** — ১/৫/১৫ মিনিটে গড়ে কতগুলো task CPU চাইছিল (R) বা I/O-তে আটকে ছিল (D); CPU% নয়। (01)
- **Log level** — log-এর গুরুত্বের মাত্রা: DEBUG, INFO, WARN, ERROR। (00, 17)
- **Little's Law** — গড় WIP = throughput × গড় cycle time; কাজের board ও server দুই জায়গাতেই খাটে। (00, 18)
- **Latency** — একটি request সম্পূর্ণ হতে কত সময় লাগে। Percentile (p50, p95, p99) দিয়ে মাপা উচিত, শুধু average নয়। (17)
- **Lead time for changes** — code commit থেকে production-এ চলা পর্যন্ত সময়। (00)
- **Least privilege** — কাজ করতে যতটুকু permission দরকার, ঠিক ততটুকুই দেওয়া। (07)
- **Load balancer** — আসা traffic একাধিক server/backend-এর মধ্যে ভাগ করে দেয়। (02)
- **Longest prefix match** — routing table-এ সবচেয়ে নির্দিষ্ট (বড় prefix) route জেতে। (02)
- **Liveness / readiness check** — liveness: process জীবিত (ব্যর্থ হলে restart); readiness: traffic নিতে প্রস্তুত, dependency সহ (ব্যর্থ হলে traffic সরানো)। (05, 14)
- **Lock file (dependency)** — সব dependency-র (transitive সহ) নির্দিষ্ট version, প্রায়ই hash-সহ; `pip install --require-hashes`। (05)

## M

- **MemAvailable** — swap ছাড়া নতুন কাজের জন্য আনুমানিক কত RAM পাওয়া যাবে; MemFree-এর চেয়ে অর্থবহ। (01)
- **Mask (ACL)** — named user ও সব group ACL entry-র সর্বোচ্চ সীমা; effective = entry AND mask। (01)
- **Mount** — একটি filesystem-কে একক directory tree-এর কোনো directory-তে যুক্ত করা। (01)
- **MCP (Model Context Protocol)** — AI application-কে বাইরের tool ও data source-এর সাথে নির্দিষ্ট নিয়মে যুক্ত করার open protocol। (27)
- **Model registry** — যাচাইকৃত ML model-এর version, metadata ও stage (staging/production) সংরক্ষণের catalog। (24)
- **MTU (Maximum Transmission Unit)** — একটি network link-এ একবারে পাঠানো যায় এমন সর্বোচ্চ packet size। (02)
- **MSS (Maximum Segment Size)** — TCP segment-এ সর্বোচ্চ data = MTU − IP ও TCP header (১৫০০ → ১৪৬০)। (02)
- **mTLS** — দুই পক্ষই certificate দেখিয়ে পরিচয় প্রমাণ করে; service mesh ও zero-trust-এ ব্যবহৃত। (02)
- **Merge base** — দুই branch-এর সর্বশেষ সাধারণ পূর্বপুরুষ; three-way merge-এর ভিত্তি। (03)
- **mktemp** — অনুমান-অযোগ্য নামে, শুধু owner-এর অধিকারে temp file/directory (symlink attack প্রতিরোধ)। (04)

## N

- **Noise (measurement)** — মাপের এলোমেলো ওঠানামা যা আসল পরিবর্তনের সাথে সম্পর্কিত নয়; একাধিকবার মেপে আলাদা করতে হয়। (00)
- **Namespace (Linux)** — process-কে আলাদা view দেয় (নিজস্ব PID, network, mount, hostname ইত্যাদি)। Container isolation-এর ভিত্তি। প্রকার: pid, net, mnt, uts, ipc, user, cgroup, time — inode নম্বর মিললে shared। (01)
- **Namespace (Kubernetes)** — একটি cluster-এর ভেতরে resource ভাগ করার logical সীমা। Linux namespace থেকে আলাদা ধারণা। (14)
- **NAT (Network Address Translation)** — packet-এর source/destination IP পরিবর্তন করা, যেমন private network থেকে internet-এ যাওয়ার সময়। (02)
- **NACL (Network ACL)** — cloud subnet-স্তরের stateless firewall; numbered rule, allow ও deny দুটোই। (02)
- **Negative caching (DNS)** — NXDOMAIN উত্তরও cache হয়, SOA-র শেষ field পর্যন্ত (RFC 2308)। (06)

## O

- **Observability** — বাইরের output (metric, log, trace) দেখে system-এর ভেতরের অবস্থা বোঝার সক্ষমতা। (17)
- **OCI (Open Container Initiative)** — container image ও runtime-এর open standard। (09)
- **OIDC (OpenID Connect)** — identity যাচাইয়ের standard; CI/CD-তে long-lived key ছাড়াই cloud-এ temporary credential পেতে ব্যবহার হয়। (11)
- **OOM (Out Of Memory) killer** — memory শেষ হলে Linux kernel যে mechanism দিয়ে কোনো process মেরে ফেলে। (01)
- **On-call** — নির্দিষ্ট সময়ে production সমস্যায় সাড়া দেওয়ার দায়িত্ব, রাতেও হতে পারে। (00, 18)
- **OSI / TCP-IP model** — network communication-কে স্তরে ভাগ করার model; প্রতিটি স্তর নিচের স্তরের header-এ মোড়ানো (encapsulation)। (02)
- **Orphan process** — parent মারা যাওয়ার পরেও চলতে থাকা child (PPID ১); cleanup-এ child বন্ধ করতে হয়। (04)

## P

- **Profiler** — code-এর কোথায় কত সময় যায় মাপার tool (deterministic: cProfile; sampling: perf, py-spy)। (01)
- **ProxyJump** — মধ্যবর্তী host দিয়ে end-to-end SSH; agent forwarding-এর নিরাপদ বিকল্প। (01)
- **Page cache** — disk file-এর RAM-এ রাখা copy; দরকার হলে kernel মুক্ত করে। (01)
- **Pipe** — একটি process-এর stdout পরেরটির stdin-এ জোড়ার kernel buffer। (01)
- **PSI (Pressure Stall Information)** — CPU/memory/IO-র অভাবে task কত শতাংশ সময় আটকে ছিল। (01)
- **Package manager** — software install/update/remove ও dependency সামলানোর tool (apt/dpkg, dnf/rpm)। (01)
- **PEP 668** — system Python-কে "externally managed" চিহ্নিত করার standard; Ubuntu 23.04+ এ venv-এর বাইরে `pip install` প্রত্যাখ্যান করে। (00, 05)
- **Platform as a product** — internal platform-কে একটি product হিসেবে দেখা, যার customer হলো developer-রা। (00, 16)
- **Pod** — Kubernetes-এর সবচেয়ে ছোট deploy unit; এক বা একাধিক container যারা network ও storage share করে। (14)
- **Process** — চলমান program; নিজের memory space, PID ও resource সহ। (01)
- **Prompt injection** — untrusted input-এ লুকানো নির্দেশ দিয়ে LLM-কে তার আসল নির্দেশ থেকে সরিয়ে দেওয়ার আক্রমণ। (25, 27)
- **PMTUD (Path MTU Discovery)** — DF bit ও ICMP "fragmentation needed" দিয়ে পথের সর্বনিম্ন MTU খোঁজা; ICMP block হলে black hole। (02)
- **pcap** — packet capture file format (tcpdump/Wireshark); আসল capture-এ secret থাকতে পারে — Git-এ নয়। (02)
- **Port forwarding (SSH tunnel)** — `ssh -L/-R/-D`: একটি port-এর traffic encrypted SSH channel দিয়ে অন্যত্র পাঠানো। (02)
- **Protected branch / ruleset** — branch-এ PR, approval, status check বাধ্যতামূলক ও force push নিষেধের নিয়ম। (03)
- **Pull request (PR)** — একটি branch-এর পরিবর্তন অন্যটিতে আনার অনুরোধ: review + CI gate + audit trail। (03)
- **Parameter expansion** — `${var##*/}`, `${var%.*}`, `${var:-d}`, `${var//a/b}`: external process ছাড়া string রূপান্তর। (04)
- **pipefail** — pipeline-এর যেকোনো অংশ ব্যর্থ হলে পুরো pipeline ব্যর্থ; না থাকলে শুধু শেষ command-এর status। (04)
- **Parameterized query** — SQL-এ মান `?` দিয়ে আলাদা পাঠানো; SQL injection ঠেকায়। (05, 20)
- **Parametrize (pytest)** — একটি test-কে অনেক input দিয়ে চালানো, প্রতিটি আলাদা test হিসেবে। (05)
- **Path traversal** — `../` বা absolute path দিয়ে নির্ধারিত directory-র বাইরে পড়া/লেখা; archive extract-এ `tarfile`-এর `filter="data"`। (05, 19)
- **Percentile (nearest-rank)** — pN = মানগুলোর N% যার সমান বা কম; nearest-rank সবসময় একটি আসল পরিমাপ দেয়। (05, 17)
- **Provenance (config)** — একটি config মান কোন উৎস (default/file/env/CLI) থেকে এসেছে। (05)
- **PHP-FPM / pm.max_children** — PHP-র FastCGI process manager; একসাথে সর্বোচ্চ worker memory থেকে হিসাব করতে হয়। (06)
- **proxy_pass URI rule** — proxy_pass-এ URI অংশ থাকলে location-এর মেলা prefix বদলে যায়; slash অমিলে `//tasks`, `/v1tasks`। (06)

## Q

- **Quantization** — model weight কম bit-এ (যেমন 16-bit থেকে 4-bit) রাখা; memory কমে, কিছু মান হারাতে পারে। (25)

## R

- **rescue.target / emergency.target** — মেরামতের জন্য ন্যূনতম systemd অবস্থা। (01)
- **RSS (Resident Set Size)** — process-এর এখন RAM-এ থাকা memory; VSZ = reserve করা মোট। (01)
- **RAG (Retrieval-Augmented Generation)** — প্রশ্নের সাথে সম্পর্কিত document খুঁজে LLM-কে context হিসেবে দিয়ে উত্তর তৈরি করা। (25)
- **RBAC (Role-Based Access Control)** — role-ভিত্তিক permission; user বা service-কে role দেওয়া হয়, role-এ permission থাকে। (14)
- **Reverse proxy** — client-এর request গ্রহণ করে backend server-এ পাঠায় (যেমন Nginx)। (06)
- **Rollback** — সমস্যাযুক্ত release-এর আগের ভালো version-এ ফিরে যাওয়া। (11)
- **RPO (Recovery Point Objective)** — সর্বোচ্চ কতটুকু সময়ের data হারানো গ্রহণযোগ্য। (30)
- **RTO (Recovery Time Objective)** — ব্যর্থতার পরে সর্বোচ্চ কত সময়ের মধ্যে service ফেরত আসতে হবে। (30)
- **Runbook** — নির্দিষ্ট operational কাজ বা incident সামলানোর ধাপে ধাপে লিখিত নির্দেশিকা। (18)
- **Recursive resolver** — client-এর পক্ষে root → TLD → authoritative পর্যন্ত খুঁজে উত্তর বের করে ও TTL অনুযায়ী cache করে। (02)
- **Request ID / correlation ID** — edge-এ একবার তৈরি হয়ে সব hop-এর log-এ যায়; distributed tracing-এর ভিত্তি। (02)
- **Rebase** — commit-গুলো নতুন base-এর উপর নতুন commit হিসেবে প্রয়োগ; hash বদলায় — shared branch-এ নয়। (03)
- **Reflog** — local ref-গুলো কোথায় কোথায় ছিল তার ডায়েরি; "হারানো" commit উদ্ধারের প্রথম জায়গা (মেয়াদসহ)। (03)
- **Remote-tracking branch** — `origin/main`: remote-এর শেষ fetch-এর সময়কার ছবি। (03)
- **Reset বনাম revert** — branch সরানো (history পুনর্লিখন) বনাম উল্টো পরিবর্তনের নতুন commit (shared branch-এ নিরাপদ)। (03)
- **Regression test** — একবার পাওয়া bug আবার না ফেরার জন্য লেখা test; আগে ব্যর্থ, fix-এর পরে পাস। (05)
- **Retry-After** — HTTP header (429/503-এ) — কত সেকেন্ড বা কোন সময় পরে আবার চেষ্টা; client-এর নিজের backoff-এর চেয়ে অগ্রাধিকার। (05)
- **Rotation (secret)** — secret বদলানো, নিয়মিত বা ফাঁসের পরে; ফাঁস হলে প্রথম কাজ। (05, 19)

## S

- **SELinux context/label** — `user:role:type:level`; type enforcement; `restorecon`, boolean, port label। (01)
- **SSH key pair** — private (গোপন, 600) ও public (`authorized_keys`-এ); নতুন key ed25519। (01)
- **setuid / setgid / sticky** — বিশেষ permission bit: owner-এর অধিকারে চালানো / group উত্তরাধিকার / শুধু owner মুছতে পারে। (01)
- **strace** — একটি program-এর system call ধরে দেখানোর tool। (01)
- **sudo** — নির্দিষ্ট command অন্য user (সাধারণত root) হিসেবে, নিজের password দিয়ে ও log সহ চালানো। (01)
- **System call (syscall)** — user program থেকে kernel-এর কাছে নিয়ন্ত্রিত অনুরোধ। (01)
- **Snapshot (VM)** — VM-এর নির্দিষ্ট মুহূর্তের অবস্থা যেখানে ফিরে যাওয়া যায়; backup নয়। (00, 07)
- **Structured log** — নির্দিষ্ট key=value বা JSON format-এর log, যা program সহজে parse ও filter করতে পারে। (00, 17)
- **Scrum** — নির্দিষ্ট দৈর্ঘ্যের sprint, role (Product Owner, Scrum Master, Developers) ও event-ভিত্তিক Agile framework। (00)
- **SemVer (Semantic Versioning)** — `MAJOR.MINOR.PATCH`: breaking change, নতুন feature, bug fix। (00, 03)
- **SBOM (Software Bill of Materials)** — একটি software-এ কোন কোন dependency ও version আছে তার তালিকা। (11, 19)
- **SELinux** — Fedora/RHEL-এর default mandatory access control system; label-ভিত্তিক policy দিয়ে process-এর access সীমিত করে। Ubuntu-তে এর জায়গায় AppArmor। (01)
- **Signal** — process-কে পাঠানো ছোট notification (যেমন `SIGTERM` = বন্ধ হও, `SIGKILL` = জোর করে বন্ধ)। (01)
- **SLI / SLO / SLA** — SLI: যা মাপা হয় (যেমন সফল request-এর অনুপাত)। SLO: সেই মাপের লক্ষ্য (99.9%)। SLA: customer-এর সাথে চুক্তি, ভঙ্গ হলে জরিমানা। (18)
- **Socket** — network communication-এর endpoint: IP + port + protocol। (02)
- **State (Terraform)** — Terraform কোন real resource তৈরি করেছে তার রেকর্ড; plan তৈরির জন্য অপরিহার্য। (12)
- **systemd** — আধুনিক Linux-এর init system ও service manager (PID 1)। (01)
- **Shift left** — security বা testing-কে delivery-র শেষ থেকে শুরুর দিকে সরানো, যাতে সমস্যা আগে ও সস্তায় ধরা পড়ে। (00, 19)
- **SAN (Subject Alternative Name)** — certificate কোন hostname/IP-র জন্য বৈধ; hostname যাচাই এর উপর হয়। (02)
- **Security group** — cloud-এ instance/interface-স্তরের stateful firewall; শুধু allow rule, ক্রম অর্থহীন। (02)
- **SNI (Server Name Indication)** — TLS ClientHello-তে কাঙ্ক্ষিত hostname, যেন একই IP-তে বহু site সঠিক certificate দিতে পারে। (02)
- **Stateful বনাম stateless firewall** — stateful connection মনে রাখে ও উত্তর স্বয়ংক্রিয়ভাবে অনুমোদন করে; stateless প্রতিটি packet আলাদা বিচার করে। (02)
- **Script injection (CI)** — untrusted text (PR title, branch name) `${{ }}` দিয়ে `run:`-এ বসে shell code হয়ে যাওয়া; প্রতিরোধ: `env:`। (03)
- **SHA pinning** — dependency/action-কে অপরিবর্তনীয় commit SHA-তে বাঁধা; tag সরানো যায়। (03)
- **Staging area / index** — পরের commit-এর প্রস্তুত অবস্থা (`git add`)। (03)
- **ShellCheck** — shell script-এর parser-ভিত্তিক static analyzer; SCxxxx code (যেমন SC2086, SC2155)। (04)
- **Strict mode (Bash)** — `set -Eeuo pipefail` (+ `inherit_errexit`); অনেক জায়গায় ইচ্ছাকৃতভাবে নীরব (if, &&, ||, `local x=$(...)`)। (04)
- **Secret scanning** — code/history-তে secret-এর নিদর্শন খোঁজা (pre-commit, CI); allowlist fingerprint দিয়ে, কারণসহ। (05, 19)
- **SecretStr** — যে মান print/log/repr-এ `***` দেখায়, আসল মান শুধু `.reveal()`-এ। (05)
- **SIGPIPE / EPIPE** — পাঠক চলে যাওয়ার পরে pipe-এ লেখা (`… | head`); Python-এ `BrokenPipeError`, Windows-এ `OSError` EINVAL; shell-এর রীতিতে exit ১৪১। (05)
- **server_name precedence** — exact → দীর্ঘতম `*.x` → দীর্ঘতম `x.*` → প্রথম regex → default_server। (06)
- **Socket activation (systemd)** — systemd socket ধরে রাখে ও service-কে fd ৩ হিসেবে দেয় (`LISTEN_FDS`); restart-এ connection refused নয়। (06)

## T

- **systemd timer** — `.timer` unit যা নির্দিষ্ট সময়ে `.service` চালায়; `Persistent=`, `RandomizedDelaySec=`। (01)
- **Tail latency** — p99-এর মত উপরের দিকের latency; অনেক call একসাথে হলে অধিকাংশ user-কে প্রভাবিত করে। (00, 17)
- **Trust boundary** — যে সীমা পেরোলে বিশ্বাসের মাত্রা বদলায় (যেমন internet → private network); diagram ও threat model-এর ভিত্তি। (00, 19)
- **T-shaped engineer** — অনেক বিষয়ে মৌলিক জ্ঞান + এক-দুটি বিষয়ে গভীর দক্ষতা। (00)
- **TLS (Transport Layer Security)** — network-এ data encrypt ও server-এর পরিচয় যাচাই করার protocol (HTTPS-এর "S")। (02)
- **Throughput** — নির্দিষ্ট সময়ে কতগুলো কাজ/request সম্পন্ন হয়। (17)
- **Toil** — হাতে করা, পুনরাবৃত্তিমূলক, automate-যোগ্য operational কাজ যা স্থায়ী মূল্য তৈরি করে না। (18)
- **TTFT (Time To First Token)** — LLM request পাঠানো থেকে প্রথম token ফেরত আসা পর্যন্ত সময়। (25)
- **TIME-WAIT / CLOSE-WAIT** — TCP state: TIME-WAIT = যে আগে বন্ধ করেছে সে কিছুক্ষণ অপেক্ষা করে (স্বাভাবিক); অনেক CLOSE-WAIT = application socket বন্ধ করছে না (bug)। (02)
- **TTL** — DNS-এ: record কতক্ষণ cache করা যাবে; IP-তে: packet কত hop যেতে পারবে। (02)
- **traceroute / mtr** — TTL বাড়িয়ে প্রতিটি hop খোঁজা; শুধু শেষ hop পর্যন্ত টিকে থাকা latency/loss আসল। (02)
- **Transit gateway** — বহু VPC/VPN-এর কেন্দ্রীয় router (hub-and-spoke); peering-এর non-transitive সীমা দূর করে। (02)
- **Trunk-based development** — ছোট, স্বল্পস্থায়ী branch ও ঘন ঘন main-এ merge; feature flag সহ। (03)
- **trap** — EXIT/ERR/INT/TERM-এ command চালানো; cleanup, ত্রুটির লাইন ও graceful shutdown। (04)
- **Test pyramid** — অনেক দ্রুত unit test, কিছু integration, অল্প end-to-end। (05, 11)
- **Thundering herd / retry storm** — বহু client একসাথে retry করে সবে সেরে ওঠা service-কে আবার ফেলে দেওয়া। (05)
- **Type hint** — Python-এ parameter/return-এর প্রত্যাশিত type-এর ঘোষণা; runtime-এ যাচাই হয় না — mypy বা নিজের validation। (05)

## U

- **USE method** — প্রতিটি resource-এর Utilization, Saturation, Errors পরীক্ষা। (01, 18)
- **Unit (systemd)** — systemd-পরিচালিত বস্তু: service, socket, timer, target, mount। (01)
- **UID / GID** — user ও group-এর সংখ্যাগত পরিচয়; kernel নাম নয়, সংখ্যা দেখে। (01)
- **umask** — নতুন file/directory তৈরির সময় কোন permission bit বাদ যাবে। (01)
- **User space** — kernel-এর বাইরে সীমিত অধিকারে program চলার পরিবেশ। (01)
- **Upstream keepalive** — nginx ও app-এর connection reuse; লাগে `keepalive N` + `proxy_http_version 1.1` + `Connection ""`। (06)

## V

- **venv** — project-ভিত্তিক আলাদা Python package environment; activate মানে `PATH`-এর শুরুতে `.venv/bin` যোগ। (00, 05)
- **Vector database** — embedding vector সংরক্ষণ ও similarity দিয়ে দ্রুত খোঁজার database। (25)
- **VPC (Virtual Private Cloud)** — cloud-এর ভেতরে আপনার নিজস্ব isolated virtual network। (07, 08)
- **VRAM** — GPU-র নিজস্ব memory; model weight ও KV cache এখানে থাকে। (26)
- **VLAN (802.1Q)** — একটি physical switch-কে ৪-byte tag দিয়ে একাধিক আলাদা L2 network-এ ভাগ করা। (02)
- **veth pair** — দুই মাথার virtual cable: এক প্রান্ত container namespace-এ (`eth0`), অপর প্রান্ত host-এ bridge-এ। (02)
- **VPC peering** — দুই VPC-র সরাসরি সংযোগ; CIDR overlap চলবে না, transitive নয়, দুই দিকে route লাগে। (02)
- **VPN / WireGuard** — encrypted virtual network link; WireGuard: key pair, AllowedIPs (route + ACL), UDP ৫১৮২০, MTU ১৪২০। (02)
- **Virtual environment (venv)** — project-এর নিজস্ব `site-packages`; `sys.prefix` ≠ `sys.base_prefix`; base interpreter বদলালে আবার তৈরি। (05)

## W

- **Word splitting** — unquoted expansion-এর ফলকে shell space/tab/newline দিয়ে ভাগ করে আলাদা argument বানায়। (01)
- **WSL2** — Windows Subsystem for Linux 2: Windows-এর ভেতরে হালকা VM-এ আসল Linux kernel। (00)
- **WIP (Work In Progress)** — শুরু হয়েছে কিন্তু শেষ হয়নি এমন কাজ; WIP limit একসাথে চলমান কাজের সর্বোচ্চ সংখ্যা। (00)
- **WAL (Write-Ahead Logging)** — SQLite/PostgreSQL-এ পরিবর্তন আগে log-এ লেখা; SQLite-এ পাঠক ও লেখক একে অপরকে কম আটকায়। (05, 20)

## X

- **X-Forwarded-For** — proxy যোগ করে আসল client IP; শুধু বিশ্বস্ত proxy-র অংশ বিশ্বাসযোগ্য। (02)

## Z

- **Zombie process** — শেষ হয়েছে কিন্তু parent এখনো `wait` করে exit status নেয়নি; শুধু PID ও process table entry রাখে। (01)
- **Zero trust** — network location নয়, identity + device + প্রতিটি request-এ policy + audit দিয়ে access। (02)
