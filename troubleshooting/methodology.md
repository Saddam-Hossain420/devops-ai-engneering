# Troubleshooting methodology — অনুমান নয়, প্রমাণ

## মূল নীতি

1. **প্রথমে প্রভাব কমান, পরে কারণ খুঁজুন।** Production-এ user কষ্ট পাচ্ছে — rollback বা traffic সরানো প্রায়ই প্রথম কাজ।
2. **পরিবর্তন খুঁজুন।** বেশিরভাগ incident-এর কারণ সাম্প্রতিক কোনো পরিবর্তন: deploy, config, certificate মেয়াদ, traffic pattern, dependency।
3. **একবারে একটি পরিবর্তন।** একসাথে পাঁচটা জিনিস বদলালে কোনটি কাজ করল জানবেন না।
4. **যা দেখছেন তা লিখুন।** সময়, command, output। পরে postmortem-এ লাগবে।
5. **Read-only command আগে।** `systemctl status`, `journalctl`, `ss`, `df` — কিছু বদলায় না।

## ধাপগুলো

```text
1. Symptom স্পষ্ট করুন      — "site down" নয়; "https://x.com থেকে 502, ১০:০৫ থেকে, সব user"
2. Scope নির্ধারণ           — সব user নাকি কিছু? সব endpoint নাকি একটি? সব region?
3. Timeline                 — কখন শুরু? তখন কী পরিবর্তন হয়েছিল?
4. Layer ধরে এগোন           — DNS → network → TLS → proxy → app → dependency (DB/cache)
5. Hypothesis               — "upstream app crash করছে"
6. Test (read-only)         — journalctl -u app; curl localhost:8000/health
7. Confirm বা reject        — প্রমাণ না মিললে পরের hypothesis
8. Fix (সবচেয়ে কম ঝুঁকির)   — reversible আগে
9. Verify                   — symptom সত্যিই গেছে? metric স্বাভাবিক?
10. Document                — incident report, runbook আপডেট
```

## Layer-ভিত্তিক দ্রুত প্রশ্ন

| Layer | প্রশ্ন | Command (Ubuntu) |
|---|---|---|
| DNS | নাম কি সঠিক IP-তে resolve হয়? | `dig +short example.com`, `resolvectl query example.com` |
| Network | IP/port-এ পৌঁছানো যায়? | `ping`, `mtr`, `nc -vz host 443` |
| Firewall | কিছু block করছে? | `sudo ufw status`, `sudo nft list ruleset` |
| TLS | Certificate বৈধ? | `openssl s_client -connect host:443 -servername host` |
| Proxy | Nginx কী বলছে? | `sudo nginx -t`, `/var/log/nginx/error.log` |
| Process | App চলছে, port শুনছে? | `systemctl status app`, `ss -tlnp` |
| Resource | CPU/memory/disk শেষ? | `top`, `free -h`, `df -h`, `df -i` |
| Dependency | DB/cache reachable? | app log, `pg_isready` |

> **Fedora-তে:** firewall যাচাই `sudo firewall-cmd --list-all`; SELinux block সন্দেহ হলে `sudo ausearch -m avc -ts recent`।
