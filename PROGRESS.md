# PROGRESS — অগ্রগতি ও পরের lesson

> নতুন Claude session শুরু হলে প্রথমে এই file পড়ুন, তারপর কাজ করুন।

## এখনকার অবস্থা

| বিষয় | মান |
|---|---|
| Repository foundation (root file, module folder, index) | COMPLETED |
| সম্পন্ন lesson (content তৈরি ও যাচাই) | 96 / 356 |
| সর্বশেষ সম্পন্ন | [L08-12 — Tagging, Cost Explorer ও resource cleanup automation](08-aws-core-services/L08-12-tagging-cost-explorer-cleanup.md) — Module 08 সম্পূর্ণ (lab ও quiz সহ); **Stage 4 সম্পূর্ণ** |
| **পরের lesson** | **L09-01 — Container বনাম virtual machine** (Module 09 — Docker and Containers) |
| পরের lesson-এর file | `09-docker-and-containers/L09-01-*.md` |
| Ubuntu-তে যাচাই বাকি | Windows-এ skip হওয়া test: L01-04 `audit`, L01-08 signal (২টি); সব Linux command-এর আসল output (systemctl, journalctl, OOM experiment, Module 02-এর `ip`/`ss`/`dig`/`ufw`/`nft`/`tcpdump`/WireGuard/Nginx, `netns_lab.sh` ও Lab 02-B/C); **Module 04-এর ShellCheck ও bats** (এই machine-এ নেই — `sudo apt install shellcheck bats`, তারপর `RUN_SHELLCHECK=1 RUN_BATS=1`) ও `flock` পথ; **Module 05-এর POSIX-only test** (L05-03 symlink ও permission, L05-10 file permission, L05-13 SIGTERM graceful shutdown), `os.killpg` path (L05-04), Linux-এর `BrokenPipeError`/connection-refused আচরণ (L05-06, L05-08), PEP 668 ও `python3-venv` (L05-01), TaskFlow-এর systemd unit (L05-13); PyYAML-এর Norway test (L05-05 — venv-এ `pip install pyyaml`); **Module 06-এর সব nginx-নির্ভর অংশ** (এই machine-এ nginx নেই — config tool শুধু nginx-এর নিয়মের অনুকরণ; `nginx -t`/`curl` দিয়ে মেলানো বাকি), L06-05-এর unix socket ও socket activation test (২টি POSIX skip), L06-09-এর PHP-FPM `security.limit_extensions`, Lab 06-A/B-এর `--live` ও Lab 06-C-এর break→fix→check; **Module 07:** L07-01-এর Linux পথ (`systemd-detect-virt`, DMI, `steal`) আসল VM-এ ও Lab 07-A (guest দিক simulate করা); L07-05-এর evaluator AWS IAM policy simulator-এ মেলানো; **Module 08: কোনো AWS command আসল account-এ চালানো হয়নি** (AWS CLI ও boto3 এই machine-এ নেই) — সব tool হাতে তৈরি describe-output-এ, `inventory.py` নকল boto3 session-এ; user data-র systemd/cloud-init অংশ, fstab/reboot, আসল ALB/Route 53/CloudWatch, Lab 08-A/B আসল account-এ বাকি |
| Primary OS | Ubuntu LTS (Fedora পার্থক্য inline note-এ) |

## দুই ধরনের status

### ১. Content status (lesson তৈরি হয়েছে কিনা — Claude update করবে)

| State | অর্থ |
|---|---|
| `NOT_STARTED` | lesson এখনো লেখা হয়নি |
| `IN_PROGRESS` | আংশিক লেখা, কী বাকি তা "Validation" কলামে |
| `COMPLETED` | Documentation, code, exercise তৈরি এবং যাচাই করা হয়েছে |
| `NEEDS_REVISION` | ভুল বা অসম্পূর্ণতা পাওয়া গেছে |

File থাকলেই lesson `COMPLETED` নয়। যাচাই (link, code run, syntax check) হলে তবেই।

### ২. Learner status (আপনি নিজে update করবেন)

| State | অর্থ |
|---|---|
| Not started | শুরু হয়নি |
| In progress | পড়ছেন / practice করছেন |
| Practiced | Practical ও exercise শেষ |
| Assessment passed | Quiz/assessment-এ ≥ 70% |
| Project completed | সংশ্লিষ্ট project শেষ |
| Needs revision | আবার দেখা দরকার |

## Stage summary

| Stage | Module | Lesson | Content সম্পন্ন | Stage progress file |
|---|---|---|---|---|
| 0 | 00 | 7 | 7 ✔ | [00-orientation/PROGRESS.md](00-orientation/PROGRESS.md) |
| 1 | 01 | 18 | 18 ✔ | [01-linux-systems/PROGRESS.md](01-linux-systems/PROGRESS.md) |
| 2 | 02 | 17 | 17 ✔ | [02-computer-networking/PROGRESS.md](02-computer-networking/PROGRESS.md) |
| 3 | 03, 04, 05 | 27 | 27 ✔ (Module 03 ✔, 04 ✔, 05 ✔) | প্রতিটি module folder-এর `PROGRESS.md` |
| 4 | 06, 07, 08 | 27 | 27 ✔ (Module 06 ✔, 07 ✔, 08 ✔) | 〃 |
| 5 | 09, 10 | 21 | 0 | 〃 |
| 6 | 11 | 14 | 0 | 〃 |
| 7 | 12, 13 | 21 | 0 | 〃 |
| 8 | 14, 15 | 29 | 0 | 〃 |
| 9 | 16 | 10 | 0 | 〃 |
| 10 | 17, 18 | 21 | 0 | 〃 |
| 11 | 19 | 16 | 0 | 〃 |
| 12 | 20, 21, 22 | 24 | 0 | 〃 |
| 13 | 23 | 9 | 0 | 〃 |
| 14 | 24 | 15 | 0 | 〃 |
| 15 | 25, 26 | 26 | 0 | 〃 |
| 16 | 27 | 13 | 0 | 〃 |
| 17 | 28 | 10 | 0 | 〃 |
| 18 | 29, 30 | 16 | 0 | 〃 |
| — | 31, 32 | 15 | 0 | 〃 |

প্রতিটি module folder-এ একটি `PROGRESS.md` আছে, যেখানে প্রতিটি lesson-এর ID, title, content status, learner status, required file, validation status, পূর্বশর্ত ও পরের lesson লেখা থাকে।

## Milestone

| Milestone | অবস্থা |
|---|---|
| 1 — Linux server operate ও troubleshoot | Content ready (Module 00–01 + Lab 01-C) — learner-এর acceptance test বাকি |
| 2 — Network ও HTTP request flow | Content ready (Module 02 + Lab 02-C; Nginx অংশ Module 06 + Lab 06-B/C) — learner-এর acceptance test বাকি |
| 3 — Containerized application | Continuous project TaskFlow v0.1 প্রস্তুত (L05-13) — container অংশ Module 09–10-এ |
| 4 — Secure CI/CD | Not started |
| 5 — Terraform + Ansible | Not started — AWS-এর ভিত্তি (Module 08: VPC, EC2, ALB, IAM, cleanup) প্রস্তুত |
| 6 — Kubernetes | Not started |
| 7 — Monitoring, SLO, runbook | Not started |
| 8 — Secure delivery | Not started |
| 9 — MLOps pipeline | Not started |
| 10 — AI inference service | Not started |
| 11 — Safe AI ops workflow | Not started |
| 12 — Final production architecture | Not started |

## Session log (handover)

| তারিখ | কী হয়েছে | পরের কাজ |
|---|---|---|
| 2026-10-26 | Foundation সম্পন্ন: plan.txt-এর পুরো structure, ১২টি root file, ৩৩ module-এর README ও PROGRESS, ১৩টি project spec, templates (doc + code), assessments, reference, docs, scripts (progress, link check, test), `.github` workflow। L00-01 সম্পন্ন (lesson + Python code + ৭টি test)। যাচাই: `progress.py validate` 0 error, `check_links.py` 0 broken, script test ও L00-01 test পাস — Windows/Python 3.14-এ; Ubuntu-তে এখনো চালানো হয়নি। | `next` → L00-02 |
| 2026-10-26 | `next`: L00-02 সম্পন্ন — engineering roles lesson, `role_fit.py` (role fit ও skill gap), `roles.json`, ৯টি test পাস; validate ও link check পাস (Windows/Python 3.14)। | `next` → L00-03 |
| 2026-10-26 | `next 2`: L00-03 (SDLC/Agile/Scrum/Kanban/release; `flow_metrics.py` — cycle time, throughput, WIP, Little's Law; ৭ test) ও L00-04 (environments; `envconfig.py` — layered config, prod validation, diff, secret masking; ১১ test) সম্পন্ন। validate ও link check পাস (Windows/Python 3.14)। | `next` → L00-05 |
| 2026-10-26 | `next`: L00-05 সম্পন্ন — C4 model, Mermaid container diagram (trust boundary সহ), ADR, docs-as-code; `adr.py` (new/list/supersede/lint) ও ৯টি test; repo-র `architecture/adr` lint পাস। | `next` → L00-06 |
| 2026-10-26 | `next`: L00-06 সম্পন্ন — বৈজ্ঞানিক পদ্ধতি, measurement, structured log, incident timeline, engineering notebook; `latency_experiment.py` (local server, p50/p95/p99, ৩বার পুনরাবৃত্তি), `incident_timeline.py`, ৭টি test। Windows timer resolution hypothesis Ubuntu-তে যাচাই বাকি (lesson-এর Exercise ১)। Module 00-এর Level A/B/C lab ও module quiz L00-07-এর সাথে তৈরি হবে। | `next` → L00-07 |
| 2026-10-26 | `next`: L00-07 সম্পন্ন — Ubuntu VM/WSL2/native, snapshot, venv ও PEP 668, `check_env.py` (read-only), `init-notebook.sh` (idempotent, dry-run), ৯টি test। Module 00 lab A/B/C (`labs/00-orientation/`, Lab C-এর `incident.log` সহ) ও module quiz তৈরি; Lab C-এর gate injection চালিয়ে যাচাই। **Module 00 সম্পূর্ণ।** | `next` → L01-01 |
| 2026-10-26 | `next 5`: L01-01 (kernel/user space, system call; `syscall_demo.py`, `strace_summary.py`), L01-02 (apt/dpkg, dnf/rpm; `pkg_inventory.py` drift), L01-03 (FHS, mount, inode, link; `fs_explorer.py`), L01-04 (users, permission, umask, special bits; `perm_tool.py`), L01-05 (ACL, sudo; `acl_check.py`, `sudoers_audit.py`) সম্পন্ন। মোট ৩২টি test পাস + ১টি skip (POSIX audit)। Test চালাতে গিয়ে ৩টি আসল bug ধরা ও ঠিক: Windows text-mode `\n`→`\r\n`, sudoers continuation-এর লাইন নম্বর (test-এর ভুল), duplicate finding। সব Linux command Ubuntu-তে চালানো বাকি। Module 01-এর lab ও quiz L01-18-এর সাথে। | `next` → L01-06 |
| 2026-10-26 | `next 5`: L01-06 (shell quoting/expansion/exit code; `argv_show.py`, `exit_code.py` — Bash test আসল GNU Bash-এ), L01-07 (pipe/grep/sed/awk/find/xargs/jq; `access_report.py` — shell ও Python-এর ফল হুবহু মিলেছে), L01-08 (process/signal; `ps_tree.py`, `graceful_worker.py`), L01-09 (CPU/memory/swap/OOM/PSI; `mem_report.py`), L01-10 (systemd/journald; `hello_service.py`, hardened `taskflow-demo.service`, `unit_lint.py`) সম্পন্ন। ২৯টি test পাস + ২টি skip (L01-08 signal, Windows)। ধরা ও ঠিক: Windows-এ `subprocess(["bash"])` WSL bash চালায় (পূর্ণ path), unit continuation-এ double space। jq installed ছিল না। | `next` → L01-11 |
| 2026-10-26 | `next 7`: L01-11 (cron/timer; `cron_explain.py`, ops-memcheck timer), L01-12 (storage/LVM; `storage_report.py`), L01-13 (SSH; `ssh_audit.py`, synthetic key), L01-14 (log/debugging; `journal_summary.py`, logrotate conf), L01-15 (performance/USE; `use_check.py`, `slow_app.py` cProfile আসলে মাপা), L01-16 (namespace/cgroup/capability; `caps_ns.py` — Docker default mask স্বাধীনভাবে মিলেছে), L01-17 (AppArmor/SELinux; `mac_denials.py`) সম্পন্ন। ৪৩টি test পাস। ধরা ও ঠিক: test-এর ৩টি ভুল প্রত্যাশিত মান (৪৬.৭%, ৮২%), lsblk tree alignment, SELinux bind-port `src=`; ছোট workload-এ profiling বিভ্রান্তি নথিভুক্ত। | `next` → L01-18 |
| 2026-10-26 | `next`: L01-18 (update, boot, recovery; `boot_report.py`, ৭টি test) সম্পন্ন। Module 01 lab A/B/C ও quiz তৈরি — Lab C-তে VM-only guard-যুক্ত `break-it.sh`/`check.sh`/`reset.sh` (bash -n ও guard যাচাই; Ubuntu-তে চালানো বাকি)। **Module 01 সম্পূর্ণ।** Milestone 1-এর acceptance test = Lab C। | `next` → L02-01 |
| 2026-10-26 | `next 10`: L02-01 (OSI/TCP-IP; `packet_layers.py`, RFC 1071 checksum), L02-02 (Ethernet/ARP/VLAN; `l2_tool.py`), L02-03 (CIDR; `subnet_calc.py`), L02-04 (routing/NAT; `route_nat.py`), L02-05 (TCP/UDP/socket; `sock_demo.py`, `ss_summary.py`), L02-06 (DNS; `dns_wire.py` — ১.১.১.১-এ আসল query), L02-07 (HTTP; `http_raw.py` — keep-alive, chunked, example.com), L02-08 (TLS; `tls_inspect.py` — temp CA lab, badssl), L02-09 (DHCP/ICMP/MTU; `mtu_calc.py` — আসল path MTU ১৪৮০ মাপা), L02-10 (firewall; `fw_sim.py`, audit) সম্পন্ন। মোট ৭২টি test পাস (Windows/Python 3.14)। GLOSSARY-তে ২৫টি networking term। `ip`/`ss`/`dig`/`ufw`/`nft` ইত্যাদি Ubuntu-তে চালানো বাকি। | `next` → L02-11 |
| 2026-10-27 | `next 7`: L02-11 (SSH tunnel/VPN/WireGuard/zero trust; `port_forward.py`, `wg_lint.py`), L02-12 (load balancing; `lb_algorithms.py`, `mini_proxy.py`), L02-13 (netns/veth/bridge; `netns_lab.sh`, `netns_inspect.py`), L02-14 (VPC; `vpc_sim.py`), L02-15 (packet capture; `make_pcap.py`, `pcap_summary.py`, synthetic `sample.pcap`), L02-16 (troubleshooting; `netcheck.py`, আসল tracert), L02-17 (request journey; `request_journey.py`) সম্পন্ন। Module 02 lab A/B/C (`labs/02-computer-networking/`, Lab C-এর VM-only guard-যুক্ত break-it/check/reset.sh) ও quiz তৈরি। ৫২টি নতুন test পাস। Test-এ ধরা ও ঠিক: proxy round-robin-এর ২টি bug, VPC lint-এর design ভুল, SQLite connection leak, connect/read timeout মিশে 502-এর বদলে 504, keep-alive-এ aborted connection। `.gitignore`-এ `*.pcap`। **Module 02 সম্পূর্ণ।** | `next` → L03-01 |
| 2026-10-27 | `next 6`: L03-01 (Git internals; `git_objects.py`, deterministic demo), L03-02 (merge/rebase; `graph.py` criss-cross সহ git-এর সাথে মেলানো, `conflict_markers.py`), L03-03 (remote/tag/SemVer; `semver.py`, local bare remote demo), L03-04 (PR/CODEOWNERS/protection; `codeowners.py` GitHub doc উদাহরণে, `protection_check.py`), L03-05 (recovery; `lost_commits.py`, bisect demo), L03-06 (GitHub Actions; `workflow_lint.py`) সম্পন্ন। Module 03 lab A/B/C ও quiz — Lab C break→সমাধান→`ALL CHECKS PASSED` Windows-এ আসলে চালানো। ৪৬টি নতুন test। আসল আবিষ্কার: bisect-এ stale `.pyc`, force push-এর পরে `pull --rebase`-এর fork-point commit ফেলে দেয়, `pipefail` + `grep -q`-এর SIGPIPE, `actions/checkout@v4` ≠ `v4.2.2`। এই repository-র `validate.yml` ও CI template action SHA-pinned ও concurrency যোগ। **Module 03 সম্পূর্ণ।** | `next` → L04-01 |
| 2026-10-27 | `next 7`: L04-01 (strict mode; ১৮টি case-এর আসল ফল, template), L04-02 (expansion ও array; নিরাপদ rename — নামে newline সহ), L04-03 (function ও library; `lib/common.sh`, `disk_check.sh`), L04-04 (trap; `safe_job.sh` — SIGTERM-এ cleanup), L04-05 (argument parsing ও logging; `backup.sh`), L04-06 (locking, atomic, idempotency; `backup_safe.sh`), L04-07 (`shlint_mini.py`, `run_checks.sh`, bats file) সম্পন্ন। ৫৫টি নতুন test (৩টি opt-in skip)। প্রতিটি lesson-এ নিজের code-এর আসল bug ধরা ও ঠিক: IFS-এর `"$*"` join, `[@]`/`[*]`, আসল `df`-এ space-যুক্ত source, associative array-এর খালি key, অনাথ child process, `-q`-এ log file খালি, path normalization ছাড়া dest-inside-source, `tar`-এর `host:path`, dry-run rotation অমিল, template-এর SC2155। **ShellCheck ও bats install-এর অনুমতি মেলেনি — চালানো হয়নি; test opt-in।** | `next` → L04-08 |
| 2026-10-27 | `next 14`: L04-08 (Bash বনাম Python; একই report দুই ভাষায়, ২ লাখ লাইনে আসল সময়) ও Module 04 lab A/B/C ও quiz — **Module 04 সম্পূর্ণ।** তারপর পুরো Module 05: L05-01 (venv/pip/pyproject; `envcheck.py`, `pin_check.py` — আসল venv-এ test), L05-02 (dataclass/StrEnum; `inventory.py`), L05-03 (pathlib, atomic write; `fs_tools.py`), L05-04 (`run_cmd.py` — timeout-এ process tree kill: সাধারণ `run` ৬.০৬ s বনাম ১.১৮ s), L05-05 (layered config + provenance; `config_loader.py`), L05-06 (retry/backoff/jitter/Idempotency-Key; local flaky server), L05-07 (JSON log, request id, redaction), L05-08 (`opsctl.py`), L05-09 (pytest; `retention.py` GFS), L05-10 (`secrets_loader.py`, `scan_secrets.py` — পুরো repo scan, ০ finding + ৫ fingerprint allowlist), L05-11 (`logscan.py` — ২ লাখ লাইন, ৭.৩ MiB), L05-12 (`healthcheck.py`, `verify_backup.py` — ৭টি demo backup), L05-13 (**TaskFlow API v0.1** — stdlib, ১০টি integration test, baseline throughput)। Module 05 lab A/B/C (B-তে grader, C-তে break/check/reset — দুটোই reference solution দিয়ে Windows-এ `ALL CHECKS PASSED`) ও quiz। নিজের code-এ ধরা আসল bug: `splitlines()`-এ newline হারানো, subparser default ফাঁদ, monitoring severity ক্রম, Windows broken pipe = EINVAL, HTTPError connection leak, thread-এ contextvar হারানো, scanner-এর `` false negative ও `(?i)` পরিধির bug (সব test পাস করছিল), ThreadPoolExecutor-এর deadline (report ৪ s, process ২০ s), কাটা archive-এ বিভ্রান্তিকর PASS, ruff `S`-এর assert ও dynamic SQL। **PyYAML, mypy, pytest-cov নেই — install করা হয়নি; সংশ্লিষ্ট test skip বা অংশ চালানো হয়নি।** | `next` → L06-01 |
| 2026-10-27 | `next 9`: পুরো Module 06 — L06-01 (DNS; `zone_lint.py`, TTL migration plan), L06-02 (nginx architecture; `nginx_conf.py` parser ও capacity, `event_loop_demo.py` — ২০ ধীর client-এ event loop ১.২ ms বনাম thread pool ২.৭ s, ৫০০-তে ৩০ s-এও উত্তর নেই), L06-03 (`server_select.py` — nginx doc-এর উদাহরণে), L06-04 (`proxy_uri.py`, `proxy_lint.py`, `error_explainer.py`; keepalive ~১৩ গুণ মাপা), L06-05 (`taskflow_serve.py` — unix socket ও socket activation, `socket_check.py`, `bind_probe.py`; .socket/.service unit), L06-06 (`cache_sim.py`, `gzip_bench.py`), L06-07 (`pki_lab.py` — OpenSSL ৩.৫-এ আসল মেয়াদোত্তীর্ণ cert, পাঁচ deployment ভুল; `cert_expiry.py`, `tls_conf_lint.py`), L06-08 (`harden_audit.py`, read-only; sshd first-value-wins), L06-09 (নিজের FastCGI client দিয়ে আসল php-cgi-তে upload-execution পুনরুৎপাদন; `fpm_pool_calc.py`, `wp_nginx_lint.py`)। Module 06 lab A/B/C (offline checker Windows-এ যাচাই; Lab C VM-only guard) ও quiz। ধরা bug: `ipaddress.is_private` documentation range-কে private বলে, PCRE named group, Host normalization-এর ক্রম, ভুল test প্রত্যাশা, unclosed socket, Windows bind আচরণ (0.0.0.0 ও 127.0.0.1 একসাথে), benchmark-এর অস্থিরতা, PKI dict-এ stem সংঘাত, lint-এর false positive/vacuous pass, Lab A-এর 'refused = 444' false PASS। পূর্ণ validation-এ **L05-12-এর একটি পুরোনো গুরুতর bug** ধরা পড়ল ও ঠিক হলো: `verify_backup.py` gzip CRC যাচাই করছিল না (সময়-নির্ভর test কাকতালীয়ভাবে পাস করছিল); regression test ও lesson সংশোধন। **nginx এই machine-এ নেই ও install করা হয়নি — সব nginx অংশ Ubuntu-তে যাচাই বাকি।** | `next` → L07-01 |
| 2026-10-28 | `next 6`: পুরো Module 07 — L07-01 (virtualization; `virt_probe.py` — এই laptop-এ আসল: physical, Hyper-V root partition; overcommit, steal), L07-02 (service model; `responsibility.py` matrix + ১১টি incident, `resilience` layer), L07-03 (region/AZ; `availability.py` — analytic + Monte Carlo; same-AZ জোড়ায় সঠিক ৯.০ h/year বনাম naive ১৯ min), L07-04 (networking; `subnet_plan.py` — best-fit, overlap ও RFC 1918), L07-05 (IAM; `policy_eval.py`, `policy_lint.py`), L07-06 (cost; `cost_estimate.py` — **উদাহরণ-দাম**, `tag_audit.py` read-only)। ৩৬টি নতুন test পাস। ধরা ও ঠিক: matrix-এ provider outage-এর দায় (resilience layer), naive formula-র দিক নিয়ে নিজের ভুল ধারণা, subnet allocation-এর অগোছালো loop, Allow+NotAction-কে শুধু WARN দেওয়া। Lab A/B/C (`labs/07-cloud-fundamentals/` — checker reference solution দিয়ে যাচাই; Lab A-র guest দিক simulate) ও quiz (Part B-এর ১০টি উত্তর tool চালিয়ে মেলানো)। কোনো cloud resource বা API call নেই। পূর্ণ validation-এ flaky test থেকে L05-13-এর আসল bug ধরা ও ঠিক: 413-এর পরে body না পড়ে বন্ধ → RST → client উত্তর হারাত (lingering drain + regression test)। **Module 07 সম্পূর্ণ।** | `next` → L08-01 (আসল AWS — খরচ ও MFA আগে) |
| 2026-10-28 | `next 12`: পুরো Module 08 — L08-01 (account safety; `account_baseline.py`, `make_budget.py`), L08-02 (CLI/profile/STS/boto3; `aws_config_audit.py`, `inventory.py`), L08-03 (role/trust/instance profile; `trust_policy_lint.py` — GitHub OIDC-এর `sub`), L08-04 (VPC; `vpc_audit.py`, `vpc_commands.py`), L08-05 (SG/NACL; `sg_reach.py` — stateless ফেরত পথ), L08-06 (EC2; `make_user_data.py` — TaskFlow embed, NAT ছাড়া; `userdata_lint.py`, `ec2_audit.py`), L08-07 (EBS/EFS; `ebs_audit.py`, `fstab_lint.py`), L08-08 (S3; `presign.py` — **AWS documentation-এর SigV4 উদাহরণের signature হুবহু**; `s3_audit.py`), L08-09 (ALB; `tg_health.py`, `hc_sim.py` — দুটি আসল TaskFlow process-এ detection মাপা), L08-10 (Route 53; `r53_plan.py`), L08-11 (CloudWatch; `alarm_sim.py` সরল মডেল, `alarm_defs.py`), L08-12 (`cleanup_plan.py` — তৈরি script নকল `aws` দিয়ে Git Bash-এ আসলে চালানো; `ce_report.py`)। ৭২টি নতুন test পাস। Lab A/B/C (`labs/08-aws-core-services/`; C সম্পূর্ণ offline, স্তরে স্তরে দুটি কারণ) ও quiz (Part B tool দিয়ে মেলানো)। ধরা ও ঠিক: cleanup-এ SG revoke-এর ক্রম ও মুছে-যাওয়া volume-এ `set -e` abort, Route 53-এর একমুখী CNAME check ও DELETE-ক্রম, alarm-এর বিভ্রান্তিকর missing-mode, Python 3.13-only `copy.replace`, py3.11-এ অচল f-string, region-inheritance ও `_netdev`/Target.Timeout নিয়ে নিজের ভুল দাবি। **কোনো AWS resource তৈরি বা API call হয়নি; কোনো দাম বানানো হয়নি।** **Module 08 ও Stage 4 সম্পূর্ণ।** | `next` → L09-01 |
