# Module 01 Quiz — Linux and Operating Systems

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৬০ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part C-এর জন্য Ubuntu VM লাগবে।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. Kernel space ও user space-এর পার্থক্য এক বাক্যে।
2. `rm` কোন system call, এবং data কখন সত্যিই মুক্ত হয়?
3. Hard link ও symlink-এর একটি করে সীমাবদ্ধতা।
4. Directory-তে `x` bit-এর অর্থ।
5. `chmod 2770 dir`-এর special bit কী করে?
6. ACL-এ mask কী?
7. `sudo less /var/log/syslog` অনুমতি দেওয়া কেন ঝুঁকিপূর্ণ?
8. `"$var"` ও `$var`-এর পার্থক্য।
9. Exit code 127 ও 137-এর অর্থ।
10. `sort | uniq -c`-এ `sort` কেন আগে?
11. Zombie process কী এবং `kill -9` কেন কাজ করে না?
12. SIGTERM ও SIGKILL-এর পার্থক্য।
13. MemFree কম কিন্তু MemAvailable বেশি — সমস্যা কি?
14. Load average উঁচু কিন্তু CPU usage কম — সম্ভাব্য কারণ।
15. `systemctl start` ও `enable`-এর পার্থক্য।
16. Cron-এ `0 0 1 * 1` কখন চলে?
17. `lvextend -r`-এ `-r` কী করে?
18. sshd_config-এ একই keyword দুবার থাকলে কোনটি কার্যকর?
19. Namespace, cgroup ও capability — প্রতিটি এক শব্দে (দেখে / পায় / পারে)।
20. "Permission ঠিক, তবু denied" — Fedora-তে প্রথম কী দেখবেন?

## Part B — Calculation ও analysis (প্রতিটি ২ নম্বর)

21. umask `027`-এ নতুন file ও directory-র mode হিসাব দেখান।
22. Mode `0047`, file owner ১০০০। UID ১০০০-এর user পড়তে পারবে? কেন?
23. `CapEff: 0000000000000400` decode করুন।
24. ৪-core server-এ load `7.8 6.9 5.1` — অবস্থা কী এবং trend কী?
25. Disk ৫০ GB, ব্যবহৃত ৪১ GB, দিনে ০.৬ GB বৃদ্ধি — কবে ৯০%?
26. Kernel version `6.8.0-9` ও `6.8.0-45` — কোনটি নতুন, এবং string sort কী ভুল করে?
27. vmstat-এ `wa` ৬৪%, `r` ২, ৪ CPU, iostat-এ `%util` ১০০ — bottleneck কোথায়?
28. RSA public key-এর modulus ২৫৬ byte (শীর্ষ bit set) — কত bit?
29. `/proc/mounts`-এ `/mnt/backup\040disk` — আসল path কী?
30. Journal-এ priority ২-এর একটি entry ও priority ৩-এর ১৪টি — কোনটি আগে তদন্ত করবেন এবং কেন উভয়ই আলাদা ঘটনা হতে পারে?

## Part C — Practical (Ubuntu VM-এ)

31. (৫ নম্বর) [Lab 01-C](../../labs/01-linux-systems/C-broken-service/README.md) সম্পূর্ণ করুন; `check.sh`-এর output ও সময় লিখুন।
32. (৫ নম্বর) একটি non-root systemd service যা port ৮০-এ শোনে, `AmbientCapabilities` দিয়ে; `/proc/<PID>/status`-এর CapEff decode করে দেখান শুধু একটি capability।
33. (৫ নম্বর) `unshare --pid --fork --mount-proc --net` দিয়ে একটি shell; ভেতরে `ps` ও `ip link`-এর output এবং host-এর সাথে namespace তুলনা (`caps_ns.py ns`)।
34. (৫ নম্বর) নিজের `sshd -T` ও `authorized_keys` audit করে প্রতিটি finding-এর সিদ্ধান্ত (ঠিক করবেন / ইচ্ছাকৃত, কেন)।

---

<details>
<summary><strong>Answer key</strong></summary>

**Part A**

1. Kernel পূর্ণ অধিকারে hardware নিয়ন্ত্রণ করে; user program সীমিত অধিকারে চলে এবং system call দিয়ে kernel-এর কাছে কাজ চায়।
2. `unlink`; link count ০ **এবং** কোনো process file খোলা না রাখলে।
3. Hard link: শুধু একই filesystem, সাধারণত directory নয়। Symlink: target মুছলে dangling।
4. ভেতরে প্রবেশ/path পেরোনো।
5. setgid directory — নতুন file directory-র group পায়।
6. Named user ও সব group entry-র সর্বোচ্চ সীমা; effective = entry AND mask।
7. less-এর ভেতরে `!sh` দিয়ে root shell।
8. Quote ছাড়া word splitting ও glob হয়; quote-এ একটি argument।
9. ১২৭ command not found; ১৩৭ SIGKILL (প্রায়ই OOM)।
10. `uniq` শুধু পরপর একই লাইন গোনে।
11. শেষ হয়েছে কিন্তু parent wait করেনি; সে আগে থেকেই মৃত — parent ঠিক/restart করতে হয়।
12. SIGTERM ধরা যায়, graceful; SIGKILL ধরা যায় না।
13. সাধারণত না — page cache reclaimable।
14. I/O wait (D state গোনা হয়) বা steal।
15. start = এখন; enable = boot-এ।
16. মাসের ১ তারিখে **এবং** প্রতি সোমবার (OR)।
17. Filesystem-ও বড় করে।
18. প্রথমটি।
19. Namespace = দেখে, cgroup = পায়, capability = পারে।
20. `ausearch -m avc -ts recent` (SELinux AVC) ও `ls -Z`।

**Part B**

21. File: 666 & ~027 = **640**; directory: 777 & ~027 = **750**।
22. **না** — owner class মিলেছে, owner bit `---`; other-এর অধিকার owner পায় না।
23. Bit ১০ → `CAP_NET_BIND_SERVICE`।
24. 7.8 ÷ 4 = 1.95 per CPU → overloaded; load1 > load15 → বাড়ছে।
25. (৪৫ − ৪১) ÷ ০.৬ = **৬.৭ দিন**।
26. `-45` নতুন; string sort-এ '9' > '4' তাই `-9`-কে ভুলভাবে নতুন ধরত।
27. Disk — CPU-র "ব্যস্ততা" আসলে iowait; run queue কম।
28. ২৫৬ × ৮ = **২০৪৮ bit**।
29. `/mnt/backup disk` (`\040` = space)।
30. Priority ২ (crit, যেমন OOM kill) আগে; কিন্তু ১৪টি err (যেমন DB connection) অন্য উৎস থেকে — timeline দিয়ে আলাদা করুন।

**Part C — গ্রহণযোগ্য উত্তরের বৈশিষ্ট্য:** আসল command ও output; least-privilege fix (Lab C-তে group-ভিত্তিক read, filler সরানো বা সঠিক আকারের storage, execute bit — `777` নয়); CapEff decode-এ শুধু `CAP_NET_BIND_SERVICE`; namespace তুলনায় pid/net/mnt ISOLATED; audit finding-এর প্রতিটির সিদ্ধান্ত সহ যুক্তি।

</details>
