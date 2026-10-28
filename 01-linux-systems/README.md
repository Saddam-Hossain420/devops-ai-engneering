# Module 01 — Linux and Operating Systems

**Stage:** 1 · **Lesson:** 18 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Linux kernel ও user space, package management, filesystem, user ও permission, process, memory, systemd, storage, SSH, log, performance, namespace/cgroup এবং AppArmor/SELinux — server চালানো ও troubleshoot করার জন্য যা যা দরকার। প্রতিটি ধারণার underlying mechanism ব্যাখ্যা ও নিরাপদ command সহ।

## পূর্বশর্ত (Prerequisites)

[00-orientation](../00-orientation/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Kernel/user space boundary ও system call ব্যাখ্যা করা
- Permission, ownership, ACL, sudo নিরাপদভাবে ব্যবহার করা
- Process, signal, memory ও OOM সমস্যা diagnose করা
- systemd service ও timer লেখা এবং journald দিয়ে debug করা
- Disk, performance ও security সমস্যা খুঁজে বের করা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L01-01 | [Linux architecture: kernel space, user space ও system call](L01-01-linux-architecture.md) | Beginner |  | COMPLETED |
| L01-02 | [Package management: apt, dpkg, repository (Fedora-তে dnf, rpm)](L01-02-package-management.md) | Beginner | 🎩 | COMPLETED |
| L01-03 | [Filesystem hierarchy, mount point, inode ও link](L01-03-filesystem-hierarchy.md) | Beginner |  | COMPLETED |
| L01-04 | [Users, groups, ownership ও permission](L01-04-users-permissions.md) | Beginner |  | COMPLETED |
| L01-05 | [ACL, sudo ও least privilege](L01-05-acl-sudo.md) | Beginner |  | COMPLETED |
| L01-06 | [Shell fundamentals: quoting, expansion, environment variable, exit code](L01-06-shell-fundamentals.md) | Beginner |  | COMPLETED |
| L01-07 | [Pipe, redirection, grep, sed, awk, find, xargs, jq](L01-07-pipes-text-tools.md) | Beginner |  | COMPLETED |
| L01-08 | [Process, thread, process state ও signal](L01-08-processes-signals.md) | Intermediate |  | COMPLETED |
| L01-09 | [CPU scheduling, virtual memory, swap ও OOM](L01-09-cpu-memory-oom.md) | Intermediate |  | COMPLETED |
| L01-10 | [systemd: unit, service, target ও journald](L01-10-systemd-services.md) | Intermediate |  | COMPLETED |
| L01-11 | [cron বনাম systemd timer](L01-11-scheduling-jobs.md) | Beginner |  | COMPLETED |
| L01-12 | [Storage: partition, filesystem, LVM, disk usage](L01-12-storage-lvm.md) | Intermediate | 🖥️ ⚠️ | COMPLETED |
| L01-13 | [SSH, SSH key, agent forwarding ও নিরাপদ remote access](L01-13-ssh-remote-access.md) | Intermediate |  | COMPLETED |
| L01-14 | [Log, debugging ও resource inspection (journalctl, strace, lsof)](L01-14-logs-and-debugging.md) | Intermediate |  | COMPLETED |
| L01-15 | [Performance profiling: top, vmstat, iostat, pidstat, perf](L01-15-performance-profiling.md) | Intermediate |  | COMPLETED |
| L01-16 | [Namespace, cgroup ও Linux capability](L01-16-namespaces-cgroups-capabilities.md) | Advanced |  | COMPLETED |
| L01-17 | [Mandatory access control: AppArmor (Ubuntu) ও SELinux (Fedora)](L01-17-apparmor-selinux.md) | Advanced | 🖥️ 🎩 | COMPLETED |
| L01-18 | [Software update, boot process ও system recovery](L01-18-updates-and-recovery.md) | Intermediate | 🖥️ | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `01-linux-systems/LNN-MM-slug.md`

## Labs

Lab folder: [labs/01-linux-systems/](../labs/01-linux-systems/README.md) · Module quiz: [assessments/01-linux-systems/quiz.md](../assessments/01-linux-systems/quiz.md)

- Level A — process, signal ও /proc পর্যবেক্ষণ
- Level B — Python script-কে systemd service + timer হিসেবে চালানো
- Level C — ভুল permission, পূর্ণ disk ও crash হওয়া service খুঁজে ঠিক করা

## সংশ্লিষ্ট project

[P01-linux-ops-toolkit](../projects/P01-linux-ops-toolkit/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] একটি ভাঙা systemd service ১৫ মিনিটে ঠিক করা (Level C lab)
- [ ] Project 1-এর প্রথম version (health check script)

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
