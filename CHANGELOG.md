# CHANGELOG

এই repository-র গুরুত্বপূর্ণ পরিবর্তন এখানে লেখা হয়। নতুন entry উপরে যোগ হয়।

Format: `YYYY-MM-DD — পরিবর্তনের ধরন — বিবরণ`

ধরন: `Added` (নতুন), `Changed` (পরিবর্তন), `Fixed` (ভুল সংশোধন), `Removed` (মুছে ফেলা)।

---

## 2026-10-28

### Added

- **Module 08 labs** — `labs/08-aws-core-services/` A (S3 bucket ও IAM policy; `check_a.py`), B (TaskFlow: VPC + EC2 + ALB; `check_b.py` চারটি module tool দিয়ে ২৪টি check), C (`Target.Timeout` incident, সম্পূর্ণ offline; `check_c.py` ন্যূনতম fix ও diagnosis যাচাই)। Checker reference solution ও ইচ্ছাকৃত ভুল input দিয়ে যাচাই; A/B আসল AWS-এ চালানো হয়নি।
- **Module 08 quiz** — `assessments/08-aws-core-services/quiz.md` (৩৫ প্রশ্ন, answer key; Part B tool দিয়ে যাচাই)।
- **Lesson L08-01 – L08-12** — AWS account safety, CLI/STS/boto3, IAM role ও trust, VPC, SG/NACL, EC2 (TaskFlow user data), EBS/EFS, S3 (SigV4 presign), ALB, Route 53, CloudWatch, tagging/Cost Explorer/cleanup; মোট ২২টি tool ও ৭২টি test। সব input হাতে তৈরি describe-output; কোনো AWS call নেই।
- **GLOSSARY** — Module 08-এর AWS term।

- **Module 07 labs** — `labs/07-cloud-fundamentals/` A (local VM; `check_a.py` — host/guest `virt_probe.py`, overcommit, steal, snapshot), B (on-prem বনাম cloud; `check_b.py` availability ও খরচ নিজে আবার হিসাব করে মেলায়), C (CI deploy role-এর ভুল IAM policy; `check_c.py` — ৬টি required ও ১৩টি dangerous request, lint)। Checker reference solution দিয়ে যাচাই (solution repo-তে নেই); Lab A-র guest দিক simulate, আসল VM-এ চালানো হয়নি।
- **Module 07 quiz** — `assessments/07-cloud-fundamentals/quiz.md` (৩৫ প্রশ্ন, answer key; Part B tool দিয়ে যাচাই)।
- **Lesson L07-06** — cost model, budget, tagging, cleanup; `cost_estimate.py` (`example-prices.json` — **বানানো দাম**, প্রতিটি output-এ সতর্কতা), `tag_audit.py` (read-only), ৬টি test।
- **Lesson L07-05** — IAM ও least privilege; `policy_eval.py` (সরল evaluation logic), `policy_lint.py`, নমুনা policy ও request, ৮টি test।
- **Lesson L07-04** — public বনাম private networking; `subnet_plan.py`, তিনটি নমুনা VPC, ৪টি test।
- **Lesson L07-03** — region, AZ, fault domain; `availability.py` (analytic, Monte Carlo, naive তুলনা, SPOF), তিনটি নমুনা, ৬টি test।
- **Lesson L07-02** — IaaS/PaaS/FaaS/SaaS ও shared responsibility; `responsibility.py`, `sample-incidents.json`, ৫টি test।
- **Lesson L07-01** — virtualization ও hypervisor; `virt_probe.py` (Linux/Windows, overcommit, steal), ৭টি test।
- **GLOSSARY** — Module 07-এর cloud term।

### Fixed

- **L08 (লেখার সময় test-এ ধরা):** `cleanup_plan.py`-এ security group-এর পারস্পরিক reference revoke-এর ক্রম ও আগেই-মুছে-যাওয়া root volume-এ `set -e`-এর কারণে অর্ধেক cleanup; `r53_plan.py`-এর একমুখী CNAME-conflict check ও DELETE-ক্রম; `alarm_sim.py`-এ প্রমাণ ছাড়া state বদল; L08-05-এর test-এ Python 3.13-only `copy.replace`; L08-04-এ py3.11-এ অচল nested f-string।
- **L05-13 `taskflow_api.py`:** 413-এর পরে body না পড়ে connection বন্ধ করায় kernel RST পাঠাত, client মাঝে মাঝে উত্তরটাই হারাত (Windows-এ ৩০ বারে ~৮)। এখন সীমিত lingering drain (`MAX_DRAIN` ১ MiB, ১ s); ৩০-বারের regression test (fix ছাড়া FAIL যাচাই করা); lesson হালনাগাদ। Module 07-এর পূর্ণ validation-এ flaky test থেকে ধরা পড়েছে।
- **L07-05 `policy_lint.py`:** `Allow` + `NotAction` on `*` শুধু WARN পাচ্ছিল, অথচ iam/sts/kms/organizations বাদ না দিলে সেটা কার্যত admin — এখন CRITICAL, regression test সহ।

---

## 2026-10-27

### Added

- **Fixed — L05-12 `verify_backup.py`:** gzip-এর CRC আসলে যাচাই হচ্ছিল না (`tarfile` end-of-archive-এ থামে, trailer পড়ে না) — data-র মাঝের bit flip নীরবে চলে যেত। এখন compressed stream শেষ পর্যন্ত পড়া হয় (`BadGzipFile: CRC check failed`); নির্ধারিত regression test (stored gzip block) যোগ; lesson-এর ভুল দাবি সংশোধিত। Module 06-এর পূর্ণ validation-এ সময়-নির্ভর test ব্যর্থ হয়ে ধরা পড়েছে।
- **Module 06 labs** — `labs/06-web-server-and-reverse-proxy/` A (static site ও server block; `check_a.py` offline + `--live`), B (TaskFlow: nginx → unix socket → HTTPS; `check_b.py`), C (মেয়াদোত্তীর্ণ cert, ভুল socket, socket permission; VM-only guard-যুক্ত `break-it.sh`/`check.sh`/`reset.sh`)। Offline checker Windows-এ যাচাই; VM অংশ চালানো হয়নি।
- **Module 06 quiz** — `assessments/06-web-server-and-reverse-proxy/quiz.md` (৩৫ প্রশ্ন, answer key)।
- **Lesson L06-09** — PHP-FPM ও WordPress; `fcgi_client.py` (FastCGI client), `php_fastcgi_demo.py` (আসল php-cgi), `fpm_pool_calc.py`, `wp_nginx_lint.py`, নমুনা config, ৭টি test।
- **Lesson L06-08** — Linux server hardening; `harden_audit.py` (read-only), `sample-root/`, ৬টি test।
- **Lesson L06-07** — nginx TLS; `pki_lab.py` (lab PKI, পাঁচ deployment ভুল), `cert_expiry.py`, `tls_conf_lint.py`, নমুনা config, ৭টি test।
- **Lesson L06-06** — Caching ও compression; `cache_sim.py`, `gzip_bench.py`, ৮টি test।
- **Lesson L06-05** — Process, port, unix socket, systemd; `taskflow_serve.py`, `socket_check.py`, `bind_probe.py`, `taskflow.socket`/`.service`, ১০টি test (২টি POSIX skip)।
- **Lesson L06-04** — Reverse proxy ও upstream; `proxy_uri.py`, `proxy_lint.py`, `error_explainer.py`, `keepalive_bench.py`, নমুনা config ও error log, ৯টি test।
- **Lesson L06-03** — Server block; `server_select.py` (server_name ও location নির্বাচন), `sites.conf`, ৮টি test।
- **Lesson L06-02** — nginx architecture; `nginx_conf.py` (parser + capacity), `event_loop_demo.py`, নমুনা config, ৮টি test।
- **Lesson L06-01** — DNS record; `zone_lint.py` (lint + TTL migration plan), নমুনা zone, ৮টি test।
- **GLOSSARY** — 14টি web server/TLS/DNS term।

- **Module 05 labs** — `labs/05-python-for-infrastructure/` A (pathlib/json/subprocess-এর ১৫টি experiment, আসল output-সহ answer key), B (TaskFlow access log report — `gen_taskflow_log.py`, grader `check_b.py`), C (ফাঁদযুক্ত API sync tool — `break_it.py`, `chaos_server.py`, `check_c.py`, marker-guarded `reset.py`)। B ও C-র grader reference solution দিয়ে Windows-এ `ALL CHECKS PASSED` যাচাই (solution repo-তে নেই)।
- **Module 05 quiz** — `assessments/05-python-for-infrastructure/quiz.md` (৩৫ প্রশ্ন, answer key)।
- **Lesson L05-13** — Continuous project TaskFlow API v0.1 (stdlib `http.server` + `sqlite3`): CRUD `/tasks`, `/health`, `/ready`, validation, request id, JSON log, graceful shutdown; `.env.example`; ১০টি integration test; baseline throughput।
- **Lesson L05-12** — Health check ও backup verification; `healthcheck.py` (daemon thread-এ সত্যিকারের deadline), `verify_backup.py` (checksum, archive, safe restore, SQLite integrity), `make_demo_backups.py`, ৮টি test।
- **Lesson L05-11** — Log analysis; `logscan.py` (streaming, gzip, percentile, spike), `gen_access_log.py`, ৮টি test।
- **Lesson L05-10** — Secret; `secrets_loader.py` (`SecretStr`, `NAME_FILE`), `scan_secrets.py` ও `repo-allowlist.txt` (এই repository scan — ০ finding), ১৩টি test।
- **Lesson L05-09** — pytest; `retention.py` (GFS), `tests/` (fixture, parametrize, marker), unittest wrapper, ২২টি pytest test।
- **Lesson L05-08** — argparse CLI; `opsctl.py` (subcommand, monitoring exit code, broken pipe), ১০টি test।
- **Lesson L05-07** — Structured logging; `logsetup.py` (JSON, request id, redaction), `demo_job.py`, ১০টি test।
- **Lesson L05-06** — HTTP client; `http_client.py` (timeout, retry, full jitter, Retry-After, Idempotency-Key), `flaky_server.py`, ১১টি test।
- **Lesson L05-05** — Config; `config_loader.py` (layered, provenance, schema, duplicate key), নমুনা config, ১২টি test (PyYAML-এর ১টি skip)।
- **Lesson L05-04** — subprocess; `run_cmd.py` (process tree kill), `injection_demo.py`, ৮টি test।
- **Lesson L05-03** — pathlib; `fs_tools.py` (largest, older-than dry-run, du, atomic write), ১০টি test (২টি POSIX skip)।
- **Lesson L05-02** — Python fundamentals ও type hint; `inventory.py`, `hosts.csv`, ৮টি test।
- **Lesson L05-01** — Python environment; `envcheck.py`, `pin_check.py`, নমুনা requirements/pyproject, ৭টি test (আসল venv সহ)।
- **Module 04 labs** — `labs/04-bash-and-shell-automation/` A (quoting ও expansion), B (backup with locking), C (broken script — `break-it.sh`, `check.sh`, `reset.sh`; Windows/Git Bash-এ `ALL CHECKS PASSED` যাচাই)।
- **Module 04 quiz** — `assessments/04-bash-and-shell-automation/quiz.md` (৩৪ প্রশ্ন)।
- **Lesson L04-08** — Bash বনাম Python; `gen_log.py`, `top_errors.sh`, `top_errors.py`, ৪টি test; ২ লাখ লাইনে আসল সময় মাপা।
- **GLOSSARY** — 32টি Python/infrastructure term।
- **Lesson L04-07** — ShellCheck ও bats; `code/L04-07/shlint_mini.py` (ShellCheck-এর ৬টি নিয়মের শেখার-সংস্করণ), `run_checks.sh` (স্পষ্ট SKIP, `--strict`), `shellcheckrc`, bats test file, ১০টি test (৩টি opt-in)। ShellCheck ও bats এখানে চালানো হয়নি।
- **Lesson L04-06** — Safe ও idempotent script; `code/L04-06/backup_safe.sh` (flock/mkdir lock, atomic publish, fingerprint, rotation), ৬টি test।
- **Lesson L04-05** — Argument parsing ও logging; `code/L04-05/getopts_demo.sh`, `backup.sh`, ৯টি test।
- **Lesson L04-04** — Error handling ও trap; `code/L04-04/trap_demo.sh`, `safe_job.sh`, ৬টি test।
- **Lesson L04-03** — Function ও reusable script; `code/L04-03/lib/common.sh`, `disk_check.sh`, নমুনা `df`, ৯টি test।
- **Lesson L04-02** — Variable, array ও parameter expansion; `code/L04-02/expansion_lab.sh`, `rename_ext.sh`, ৭টি test।
- **Lesson L04-01** — Script-এর গঠন ও strict mode; `code/L04-01/strict_mode_demo.sh`, `script_template.sh`, ৮টি test।
- **GLOSSARY** — ১৫টি Bash term।

- **Module 03 labs** — `labs/03-git-and-collaboration/` A (inside `.git`), B (PR থেকে release), C (Git disaster recovery; `break-it.sh`, `check.sh`, `reset.sh` — নিজের directory-তে, marker-guarded reset)।
- **Module 03 quiz** — `assessments/03-git-and-collaboration/quiz.md` (answer key; Part B module-এর tool দিয়ে যাচাই)।
- **Lesson L03-06** — GitHub Actions fundamentals; `code/L03-06/workflow_lint.py`, খারাপ/ভালো নমুনা workflow, ৭টি test (repository workflow-এর regression guard সহ)।
- **Lesson L03-05** — Git recovery; `code/L03-05/lost_commits.py`, `recovery_demo.sh`, `bisect_demo.sh`, ৭টি test।
- **Lesson L03-04** — PR, code review, protected branch, CODEOWNERS; `code/L03-04/codeowners.py`, `protection_check.py`, নমুনা CODEOWNERS/protection JSON/PR template, ৯টি test।
- **Lesson L03-03** — Remote, tag ও SemVer; `code/L03-03/semver.py`, `remote_demo.sh`, ৮টি test।
- **Lesson L03-02** — Branch, merge ও rebase; `code/L03-02/graph.py`, `conflict_markers.py`, `merge_vs_rebase.sh`, ৭টি test।
- **Lesson L03-01** — Git internals; `code/L03-01/git_objects.py`, `make_demo_repo.sh`, ৮টি test।
- **GLOSSARY** — ২২টি Git ও CI term।

- **Module 02 labs** — `labs/02-computer-networking/` A (network fact sheet), B (Nginx + নিজের CA-র TLS + load balancing + ufw), C (DNS/firewall/bind — তিন স্তরে ভাঙা request path; `break-it.sh`, `check.sh`, `reset.sh`, `app.py` — VM-only guard সহ)।
- **Module 02 quiz** — `assessments/02-computer-networking/quiz.md` (answer key; Part B-এর হিসাব module-এর tool দিয়ে যাচাই)।
- **Lesson L02-17** — Browser থেকে database: request-এর পূর্ণ যাত্রা; `code/L02-17/request_journey.py` (proxy → app → SQLite, request ID, fault injection), ৬টি test।
- **Lesson L02-16** — Troubleshooting toolkit; `code/L02-16/netcheck.py` (DNS → TCP → TLS → HTTP, পরের command সুপারিশ, JSON), ৭টি test।
- **Lesson L02-15** — tcpdump ও Wireshark; `code/L02-15/make_pcap.py`, `pcap_summary.py`, synthetic `sample.pcap`, ৭টি test।
- **Lesson L02-14** — Cloud networking (VPC, subnet, routing, peering); `code/L02-14/vpc_sim.py` (trace ও design lint), নমুনা `sample-vpcs.json`, ১০টি test।
- **Lesson L02-13** — Network namespace, veth ও bridge; `code/L02-13/netns_lab.sh` (VM-only), `netns_inspect.py`, নমুনা `sample-links.json`, ৭টি test।
- **Lesson L02-12** — Load balancing ও reverse proxy; `code/L02-12/lb_algorithms.py`, `mini_proxy.py`, ৮টি test।
- **Lesson L02-11** — SSH tunnel, VPN, WireGuard ও zero trust; `code/L02-11/port_forward.py`, `wg_lint.py`, synthetic `sample-wg0.conf`, ৭টি test।
- **GLOSSARY** — ১৭টি নতুন term (bastion, consistent hashing, veth, VPC peering, zero trust ইত্যাদি)।

### Changed

- `.github/workflows/validate.yml` ও `templates/github-actions-ci.yml` — action commit SHA দিয়ে pin (`git ls-remote` দিয়ে যাচাই), `validate.yml`-এ `concurrency` (L03-06-এর linter-এর finding)।
- `03-git-and-collaboration/README.md` — Labs section আসল lab-এর সাথে মেলানো, quiz link।
- `.gitignore` — `*.pcap`, `*.pcapng` (শুধু synthetic `L02-15/sample.pcap` ব্যতিক্রম)।
- `02-computer-networking/README.md` — Labs section আসল lab-এর সাথে মেলানো, quiz link।

### Fixed

- GLOSSARY-তে "Namespace (Linux)"-এর duplicate entry একত্র।

## 2026-10-26

### Added

- **Lesson L02-10** — Firewall: nftables, ufw (Fedora: firewalld), security group ও NACL; `code/L02-10/fw_sim.py` (first-match, conntrack, NACL ephemeral ফাঁদ, audit), `sample-rules.txt`, ৯টি test।
- **Lesson L02-09** — DHCP, ICMP, MTU ও PMTUD; `code/L02-09/mtu_calc.py` (MSS, tunnel overhead, fragmentation, PMTUD search, lease timer), ৭টি test; আসল path MTU পরিমাপ নথিভুক্ত।
- **Lesson L02-08** — TLS, certificate ও HTTPS; `code/L02-08/tls_inspect.py` (verify, SAN, expiry, temp-CA lab), ৮টি test।
- **Lesson L02-07** — HTTP/1.1, HTTP/2 ও HTTP/3; `code/L02-07/http_raw.py` (raw request, keep-alive, chunked decode, local server), ৭টি test।
- **Lesson L02-06** — DNS; `code/L02-06/dns_wire.py` (RFC 1035 wire format, compression pointer, আসল query), ৭টি test।
- **Lesson L02-05** — TCP, UDP, port, socket ও connection state; `code/L02-05/sock_demo.py`, `ss_summary.py`, নমুনা `ss` output, ৭টি test।
- **Lesson L02-04** — Routing table, gateway ও NAT; `code/L02-04/route_nat.py` (longest prefix match, NAT port exhaustion), নমুনা route/flow, ৭টি test।
- **Lesson L02-03** — IP addressing ও CIDR; `code/L02-03/subnet_calc.py` (info/split/overlap/plan, cloud-reserved address), ৮টি test।
- **Lesson L02-02** — Ethernet, MAC, ARP ও VLAN; `code/L02-02/l2_tool.py`, নমুনা `ip neigh`, ৬টি test।
- **Lesson L02-01** — OSI ও TCP/IP model; `code/L02-01/packet_layers.py` (encapsulation, RFC 1071 checksum, hexdump), ৬টি test।
- **GLOSSARY** — Module 02-এর ২৫টি networking term।
- **Lesson L01-18** — Software update, boot process ও system recovery; `code/L01-18/boot_report.py` (boot timing, reboot-needed, সংখ্যাভিত্তিক kernel version), ৭টি test।
- **Module 01 labs** — `labs/01-linux-systems/` A (process observation), B (hardened service + timer), C (তিন স্তরে ভাঙা service; `break-it.sh`, `check.sh`, `reset.sh`, `app.py` — VM-only guard সহ)।
- **Module 01 quiz** — `assessments/01-linux-systems/quiz.md` (answer key সহ)।
- **Lesson L01-17** — AppArmor (Ubuntu) ও SELinux (Fedora); `code/L01-17/mac_denials.py`, নমুনা audit log, ৫টি test।
- **Lesson L01-16** — Namespace, cgroup ও capability; `code/L01-16/caps_ns.py` (capability decode, namespace তুলনা, cgroup path), ৬টি test।
- **Lesson L01-15** — Performance profiling ও USE method; `code/L01-15/use_check.py`, `slow_app.py` (cProfile), ৫টি test।
- **Lesson L01-14** — Log, debugging ও resource inspection; `code/L01-14/journal_summary.py`, `taskflow-logrotate.conf`, ৪টি test।
- **Lesson L01-13** — SSH ও নিরাপদ remote access; `code/L01-13/ssh_audit.py` (sshd ও authorized_keys, RSA bit), synthetic নমুনা key, ৯টি test।
- **Lesson L01-12** — Storage, partition, LVM; `code/L01-12/storage_report.py` (lsblk, LVM, disk-full forecast), ৬টি test।
- **Lesson L01-11** — cron বনাম systemd timer; `code/L01-11/cron_explain.py`, `ops-memcheck.service/.timer`, ৮টি test।
- **Lesson L01-10** — systemd: unit, service, target ও journald; `code/L01-10/hello_service.py`, hardened `taskflow-demo.service`, `unit_lint.py`, ৭টি test।
- **Lesson L01-09** — CPU scheduling, virtual memory, swap ও OOM; `code/L01-09/mem_report.py` (meminfo, load, PSI, system বনাম cgroup OOM), ৬টি test।
- **Lesson L01-08** — Process, thread, state ও signal; `code/L01-08/ps_tree.py` (tree, zombie, D-state), `graceful_worker.py`, ৬টি test (২টি POSIX-only)।
- **Lesson L01-07** — Pipe, grep, sed, awk, find, xargs, jq; `code/L01-07/access_report.py`, নমুনা `access.log`/`events.json`, ৪টি test (shell pipeline-এর সাথে তুলনা সহ)।
- **Lesson L01-06** — Shell fundamentals; `code/L01-06/argv_show.py`, `exit_code.py`, ৮টি test (৩টি আসল Bash চালিয়ে)।
- **Lesson L01-05** — ACL, sudo ও least privilege; `code/L01-05/acl_check.py` (POSIX ACL algorithm, mask), `sudoers_audit.py` (NOPASSWD ALL, shell escape, wildcard, env_keep), ১১টি test।
- **Lesson L01-04** — Users, groups, ownership ও permission; `code/L01-04/perm_tool.py` (explain, umask, access decision, users, audit), ৮টি test (১টি POSIX-only)।
- **Lesson L01-03** — Filesystem hierarchy, mount, inode ও link; `code/L01-03/fs_explorer.py` (FHS lookup, /proc/mounts, link experiment), ৪টি test।
- **Lesson L01-02** — Package management (apt/dpkg, Fedora dnf/rpm); `code/L01-02/pkg_inventory.py` (largest packages, server drift), ৫টি test।
- **Lesson L01-01** — Linux architecture ও system call; `code/L01-01/syscall_demo.py`, `strace_summary.py`, ৫টি test।
- **Lesson L00-07** — Lab environment setup; `code/L00-07/check_env.py` (read-only environment checker), `init-notebook.sh` (idempotent, dry-run), ৯টি unit test।
- **Module 00 labs** — `labs/00-orientation/` A (delivery metrics), B (TaskFlow delivery design), C (incident analysis: decoy বনাম আসল কারণ, config gate injection, `incident.log`)।
- **Module 00 quiz** — `assessments/00-orientation/quiz.md` (answer key সহ)।
- **Lesson L00-06** — Experiment, log, measurement ও incident analysis দিয়ে শেখা; `code/L00-06/latency_experiment.py` (loopback HTTP server-এ নিয়ন্ত্রিত latency/failure experiment), `incident_timeline.py` (structured log → প্রতি মিনিটের error rate ও incident window), `sample-app.log`, ৭টি unit test।
- **Lesson L00-05** — Architecture diagram ও technical documentation (C4, ADR, docs-as-code); `code/L00-05/adr.py` (ADR new/list/supersede/lint), দুটি example ADR, ৯টি unit test।
- **Lesson L00-04** — Environments: development, testing, staging, production; `code/L00-04/envconfig.py` (base → env file → env var layered config, production validation, environment diff, secret masking, file-এ secret প্রত্যাখ্যান), ১১টি unit test।
- **Lesson L00-03** — SDLC, Agile, Scrum, Kanban ও release management; `code/L00-03/flow_metrics.py` (cycle time, p50/p85, throughput, WIP, Little's Law), ৭টি unit test।
- **Lesson L00-02** — Engineering roles: DevOps, SRE, Platform, Cloud, Security, MLOps, AI Infra; `code/L00-02/role_fit.py` (weighted role fit ও skill gap → module সুপারিশ), `roles.json`, ৯টি unit test।

- plan.txt অনুযায়ী পূর্ণ top-level structure: 33টি module folder এবং `labs/`, `projects/`, `architecture/`, `scripts/`, `templates/`, `assessments/`, `troubleshooting/`, `runbooks/`, `reference/`, `docs/`, `.github/`।
- Root file: `README.md`, `START-HERE.md`, `ROADMAP.md`, `LEARNING-TRACKS.md`, `CURRICULUM-MAP.md`, `GLOSSARY.md`, `PROGRESS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `.gitignore`, `.editorconfig`।
- 356টি lesson-সহ পূর্ণ curriculum map ও module dependency graph।
- ৩৩টি module-এর `README.md` (scope, পূর্বশর্ত, outcome, lesson, lab, completion criteria) ও `PROGRESS.md`।
- `projects/`: ১৩টি project spec (architecture, acceptance criteria, resource, cleanup)।
- `templates/`: lesson, lab, project README, ADR, runbook, incident report, postmortem; CI workflow, Dockerfile, Compose, Terraform module, Ansible role, Kubernetes manifest, Helm chart, Prometheus alert, ML pipeline, model-serving API, agent tool।
- `assessments/`: scoring model, diagnostic assessment, code ও security review checklist, capstone rubric।
- `reference/`: official documentation index, Ubuntu বনাম Fedora cheat sheet।
- `docs/`: implementation plan, session protocol, hardware ও cost guide, keeping-current guide।
- `architecture/`: ADR-0001, continuous project evolution।
- `troubleshooting/methodology.md`, `runbooks/README.md`, `labs/README.md`।
- `scripts/progress.py`, `scripts/check_links.py` ও test; `.github/workflows/validate.yml`, PR ও issue template।
- **Lesson L00-01** — DevOps আসলে কী: culture, feedback loop ও DORA metrics; `code/L00-01/dora_metrics.py` ও ৭টি unit test।

### Changed

- Primary practice OS **Ubuntu LTS** নির্ধারণ। Fedora-তে আলাদা কিছু হলে inline "Fedora-তে:" note।
