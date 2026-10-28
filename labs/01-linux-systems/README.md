# Module 01 Labs — Linux and Operating Systems

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — Process observation](A-process-observation/README.md) | A — Fundamentals | Process, signal, `/proc`, memory ও capability পর্যবেক্ষণ | ৬০ মিনিট | L01-01, L01-06, L01-08, L01-09, L01-16 |
| [B — Service and timer](B-service-and-timer/README.md) | B — Integrated | Python tool-কে hardened systemd service + timer হিসেবে, log ও audit সহ | ৯০ মিনিট | L01-04, L01-10, L01-11, L01-14 |
| [C — Broken service](C-broken-service/README.md) | C — Failure and Recovery | তিনটি স্তরে ভাঙা service diagnose ও ঠিক করা | ৬০–৯০ মিনিট | L01-03, L01-04, L01-10, L01-12, L01-14 |

**Environment:** Ubuntu VM (systemd PID 1), **snapshot নিয়ে শুরু করুন**। Lab C ⚠️ system user, unit ও একটি ছোট tmpfs তৈরি করে — শুধু VM-এ, script `--yes-i-am-in-a-vm` flag ছাড়া চলে না, এবং `reset.sh` সব পরিষ্কার করে।

**Milestone 1-এর acceptance test** ([ROADMAP](../../ROADMAP.md)): Lab C ১৫ মিনিটের মধ্যে, `journalctl`, `systemctl`, `ls -l`, `df` দিয়ে, `chmod 777` ছাড়া।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [01-linux-systems/PROGRESS.md](../../01-linux-systems/PROGRESS.md)-এর Module assessment table আপডেট করুন।
