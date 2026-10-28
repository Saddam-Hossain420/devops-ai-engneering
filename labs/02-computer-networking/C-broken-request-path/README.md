# Lab 02-C — Broken request path: diagnose layer by layer

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট (লক্ষ্য: diagnosis + fix ২০ মিনিট) |
| **Environment** | Ubuntu VM (systemd, nftables), **snapshot বাধ্যতামূলক** |
| **Label** | ⚠️ `/etc/hosts`-এ একটি লাইন, nftables table `inet lab02c`, unit `lab02c-app.service`, `/etc/lab02c`, `/srv/lab02c` তৈরি করে — `reset.sh` সব মোছে |

## Objective

`curl http://shop.lab:8080/health`-এর পথে **তিনটি ভিন্ন স্তরে** লুকানো তিনটি সমস্যা — একটি ঠিক করলে পরেরটি দেখা দেয়, এবং দুটির symptom হুবহু একই — শুধু প্রমাণ দিয়ে (L02-16-এর স্তরভিত্তিক পদ্ধতি) খুঁজে বের করে ঠিক করা। Firewall বন্ধ করা, nftables ruleset flush করা বা app-কে `0.0.0.0`-এ খুলে দেওয়া **নিষেধ** — শুধু ভুলটি ঠিক করুন।

## Prerequisites

- Lesson: [L02-05](../../../02-computer-networking/L02-05-tcp-udp-sockets.md), [L02-06](../../../02-computer-networking/L02-06-dns.md), [L02-10](../../../02-computer-networking/L02-10-firewalls.md), [L02-15](../../../02-computer-networking/L02-15-packet-capture.md), [L02-16](../../../02-computer-networking/L02-16-troubleshooting-toolkit.md)
- [Troubleshooting methodology](../../../troubleshooting/methodology.md)
- `curl`, `dnsutils`, `tcpdump`, `nftables` installed

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/02-computer-networking/C-broken-request-path
sudo bash break-it.sh --yes-i-am-in-a-vm
```

Files: [`break-it.sh`](break-it.sh), [`app.py`](app.py), [`check.sh`](check.sh), [`reset.sh`](reset.sh)। **Script না পড়ে diagnose করুন** — বাস্তবে কেউ বলে দেয় না কী ভাঙা।

## Steps

1. Timer চালু করুন।
2. **Symptom:** `curl -sv --max-time 5 http://shop.lab:8080/health` — কী error, কত সময় পরে? Refused নাকি timeout?
3. **L02-16-এর সিদ্ধান্ত-বৃক্ষ** অনুসরণ করুন; প্রতিটি স্তরে একটি read-only প্রমাণ:
   - নাম: `getent hosts shop.lab` বনাম `dig +short shop.lab` — দুটো ভিন্ন কেন?
   - Socket: `ss -ltnp | grep 8080`
   - Route/packet: `sudo tcpdump -ni any 'tcp port 8080'` (অন্য terminal-এ, curl চলার সময়) — SYN যাচ্ছে? SYN-ACK আসছে? RST?
   - Firewall: `sudo nft list ruleset` — শুধু ufw-এর chain নয়, **সব table** দেখুন।
   - Service: `systemctl status lab02c-app`, `journalctl -u lab02c-app -n 20`
4. প্রতিটি ঠিক করার পরে আবার Step 2 — symptom কীভাবে বদলাল notebook-এ লিখুন।
5. সব ঠিক হলে:

   ```bash
   sudo bash check.sh
   ```

6. Timer থামান; notebook-এ incident report ([template](../../../templates/incident-report-template.md))।

## Expected behavior

- শুরুতে `curl` timeout। প্রথম fix-এর পরেও **timeout** (কিন্তু ভিন্ন কারণে!)। দ্বিতীয় fix-এর পরে **connection refused**। তৃতীয়টির পরে `{"status": "ok"}`।
- `check.sh`: পাঁচটি PASS ও `ALL CHECKS PASSED`, exit 0।

## Verification

```bash
sudo bash check.sh; echo "exit=$?"                                   # 0
curl -s -w ' %{http_code} %{time_total}s\n' http://shop.lab:8080/health
ss -ltn 'sport = :8080'                                              # 127.0.0.1:8080, 0.0.0.0 নয়
```

## Troubleshooting (সূত্র — আটকে গেলে একটি একটি করে খুলুন)

<details><summary>সূত্র ১</summary>

`curl -v`-এর প্রথম লাইন: `Trying X.X.X.X:8080...` — এই IP কি আপনার machine? `getent hosts` application যা দেখে (L02-06); `dig` `/etc/hosts` দেখে না। `192.0.2.0/24` কোন ধরনের address (L02-03)?
</details>

<details><summary>সূত্র ২</summary>

নাম ঠিক করার পরেও timeout, অথচ সব local। `tcpdump -ni lo port 8080`-এ SYN বারবার (retransmit), কোনো উত্তর নেই → কেউ নিঃশব্দে **drop** করছে (L02-10: drop বনাম reject)। ufw-এর বাইরেও nftables table থাকতে পারে: `sudo nft list tables`।
</details>

<details><summary>সূত্র ৩</summary>

এবার সাথে সাথে `Connection refused` — packet পৌঁছেছে, কিন্তু ঐ address:port-এ কেউ শুনছে না। `ss -ltnp`-এ app **কোন address-এ** শুনছে? `127.0.0.1` ও `127.0.0.2` কি একই socket? App-এর configuration কোথা থেকে আসে: `systemctl cat lab02c-app`। পরিবর্তনের পরে `sudo systemctl restart lab02c-app`।
</details>

## Cleanup / reset

```bash
sudo bash reset.sh --yes-i-am-in-a-vm
grep shop.lab /etc/hosts; sudo nft list tables; systemctl status lab02c-app 2>&1 | head -1   # কিছুই থাকা উচিত নয়
```

> **Fedora-তে:** একই script চলে (nftables, systemd); firewalld চালু থাকলে তার নিজের table-ও `nft list ruleset`-এ দেখবেন — lab-এর table আলাদা (`inet lab02c`)। `dig` আসে `bind-utils`-এ।

> Cloud VM-এ `cloud-init` reboot-এর সময় `/etc/hosts` নতুন করে লিখতে পারে — lab একটি session-এর মধ্যে শেষ করুন।

## Assessment

1. প্রতিটি সমস্যার জন্য: symptom (আসল output), প্রমাণ (কোন command), স্তর, কারণ, fix।
2. প্রথম ও দ্বিতীয় সমস্যার symptom একই (timeout) — কোন প্রমাণ দুটিকে আলাদা করল?
3. `dig` কেন প্রথম সমস্যায় বিভ্রান্তিকর হতে পারত?
4. তৃতীয় সমস্যায় `LAB_BIND=0.0.0.0` কেন "কাজ করে কিন্তু ভুল" সমাধান? (`check.sh` কী বলে?)
5. কোন সমস্যা কোন monitoring/check আগে থেকে ধরতে পারত (যেমন `netcheck.py --json` timer-এ)?
6. মোট সময়; লক্ষ্য পূরণ না হলে কোন ধাপে সময় গেল?
