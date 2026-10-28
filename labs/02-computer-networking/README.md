# Module 02 Labs — Computer Networking

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — Network fact sheet](A-network-fact-sheet/README.md) | A — Fundamentals | নিজের machine-এর interface, subnet, route, DNS, socket, MTU ও HTTPS timing — command ও Python tool মিলিয়ে | ৬০–৭৫ মিনিট | L02-01 – L02-09, L02-16 |
| [B — Secure reverse proxy](B-secure-reverse-proxy/README.md) | B — Integrated | Nginx + নিজের CA-র TLS + least_conn load balancing + request ID + ufw, প্রতিটি দাবির প্রমাণ | ৯০–১২০ মিনিট | L02-05, L02-07, L02-08, L02-10, L02-12, L02-15 – L02-17 |
| [C — Broken request path](C-broken-request-path/README.md) | C — Failure and Recovery | DNS, firewall ও bind address — তিন স্তরে ভাঙা request path স্তর ধরে diagnose | ৬০–৯০ মিনিট | L02-05, L02-06, L02-10, L02-15, L02-16 |

**Environment:** Ubuntu VM, **snapshot নিয়ে শুরু করুন**। Lab A সম্পূর্ণ read-only। Lab B ও C system configuration বদলায় (Nginx, ufw, `/etc/hosts`, nftables) — Lab C-এর script `--yes-i-am-in-a-vm` flag ছাড়া চলে না এবং `reset.sh` সব পরিষ্কার করে; Lab B-র cleanup ধাপ README-তে।

**Milestone 2-এর acceptance test** ([ROADMAP](../../ROADMAP.md)) — চারটি পরিস্থিতিতে সঠিক layer চিহ্নিত করা:

| পরিস্থিতি | কোথায় অনুশীলন |
|---|---|
| DNS ভুল | Lab C (প্রথম ব্যর্থতা) |
| Firewall block | Lab C (দ্বিতীয় ব্যর্থতা) |
| Upstream down | Lab C (তৃতীয় — কেউ শুনছে না) ও Lab B Step 6 (একটি backend বন্ধ, failover) |
| TLS certificate মেয়াদোত্তীর্ণ | `netcheck.py https://expired.badssl.com/` ও `openssl s_client` দিয়ে প্রমাণ ([L02-08](../../02-computer-networking/L02-08-tls-certificates.md), [L02-16](../../02-computer-networking/L02-16-troubleshooting-toolkit.md)); নিজের lab-এ: Lab B-র certificate-এর মেয়াদ (`-days 7`) পার হওয়ার পরে আবার `netcheck` |

Lab C ২০ মিনিটের মধ্যে, firewall বন্ধ বা `0.0.0.0` bind ছাড়া; সাথে [L02-17](../../02-computer-networking/L02-17-request-journey.md)-এর mini-project (request flow walkthrough)।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [02-computer-networking/PROGRESS.md](../../02-computer-networking/PROGRESS.md)-এর Module assessment table আপডেট করুন।
