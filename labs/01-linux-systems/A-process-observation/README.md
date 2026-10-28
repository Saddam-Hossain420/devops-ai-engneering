# Lab 01-A — Process observation

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৬০ মিনিট |
| **Environment** | Ubuntu VM, Python 3.10+ |
| **Label** | — (নিজের process; কোনো system পরিবর্তন নয়) |

## Objective

একটি চলমান process-কে তার জীবনচক্র জুড়ে পর্যবেক্ষণ করা: জন্ম, `/proc`-এ পরিচয়, খোলা file, memory, capability, signal-এ প্রতিক্রিয়া ও exit code — প্রতিটি পর্যবেক্ষণ একটি command ও একটি Python tool দিয়ে মিলিয়ে।

## Prerequisites

- Lesson: [L01-01](../../../01-linux-systems/L01-01-linux-architecture.md), [L01-06](../../../01-linux-systems/L01-06-shell-fundamentals.md), [L01-08](../../../01-linux-systems/L01-08-processes-signals.md), [L01-09](../../../01-linux-systems/L01-09-cpu-memory-oom.md), [L01-16](../../../01-linux-systems/L01-16-namespaces-cgroups-capabilities.md)
- `strace`, `lsof` installed

## Environment setup

```bash
cd ~/devops-ai-engineering/01-linux-systems/code
mkdir -p ~/devops-notebook/labs/01-A
```

## Steps

1. **জন্ম ও পরিচয়:**

   ```bash
   python3 L01-08/graceful_worker.py --job-seconds 3 &
   PID=$!
   ps -o pid,ppid,stat,user,comm -p $PID
   cat /proc/$PID/status | grep -E 'Name|State|PPid|Threads|VmRSS'
   ```

2. **খোলা file:** `ls -l /proc/$PID/fd` ও `lsof -p $PID | head` — fd 0, 1, 2 কোথায় যুক্ত?
3. **Capability:** `grep CapEff /proc/$PID/status` → `python3 L01-16/caps_ns.py caps <মান>` — কেন শূন্য?
4. **Tree:** `ps -eo pid,ppid,stat,user,comm --no-headers > /tmp/ps.txt` → `python3 L01-08/ps_tree.py /tmp/ps.txt --root $(ps -o ppid= -p $PID | tr -d ' ')` — আপনার shell-এর নিচে worker।
5. **Signal:** `kill -HUP $PID` (reload — চলতে থাকে), তারপর `kill -TERM $PID; wait $PID; echo "exit=$?"`।
6. **SIGKILL তুলনা:** নতুন worker চালু করে `kill -KILL`, `wait`, exit code — `python3 L01-06/exit_code.py <code>`।
7. **System call:** `strace -f -e trace=openat,write -o /tmp/t.txt python3 L01-01/syscall_demo.py` → `python3 L01-01/strace_summary.py /tmp/t.txt`।
8. **Memory:** `python3 L01-09/mem_report.py meminfo` ও `free -h` মিলিয়ে দেখুন।

## Expected behavior

- SIGHUP-এর পরে worker চলতে থাকে, log-এ "reloading config"।
- SIGTERM → "clean shutdown", exit 0; SIGKILL → exit 137, shutdown বার্তা নেই।
- সাধারণ user-এর process-এর `CapEff` = `0000000000000000`।

## Verification

```bash
grep -c "clean shutdown" ~/devops-notebook/labs/01-A/worker.log   # যদি output redirect করে থাকেন: ≥1
python3 L01-06/exit_code.py 143 137
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `wait: pid ... is not a child of this shell` | অন্য terminal-এ চালানো | একই shell-এ চালান |
| `strace: command not found` | install নেই | `sudo apt install strace` |
| `lsof` অন্য user-এর process দেখায় না | permission | নিজের process বা `sudo` |

## Cleanup / reset

```bash
kill %1 %2 2>/dev/null; rm -f /tmp/ps.txt /tmp/t.txt
```

## Assessment

1. fd 0/1/2 কোথায় যুক্ত ছিল এবং output redirect করলে কী বদলায়?
2. SIGTERM ও SIGKILL-এ আচরণ ও exit code-এর পার্থক্য প্রমাণ সহ লিখুন।
3. সাধারণ process-এর CapEff শূন্য কেন, আর sshd-এর (`/proc/<sshd PID>/status`) কেন নয়?
4. strace summary-তে কোন file খোলা ব্যর্থ হয়েছে এবং সেটি কি সমস্যা?
