# L06-01 — DNS record ও domain configuration

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-06 — DNS](../02-computer-networking/L02-06-dns.md), [L05-13 — TaskFlow API](../05-python-for-infrastructure/L05-13-taskflow-api-v01.md) |
| **Label** | — |
| **Tested** | `zone_lint.py`: ৮টি test পাস (Python 3.14.5, Windows)। নমুনা zone-এর ৬টি ইচ্ছাকৃত error সব ধরা পড়েছে। লেখার সময় একটি আসল bug ধরা পড়েছে: Python-এর `ipaddress.is_private` documentation range-কেও "private" বলে (Section 9.3)। `getaddrinfo` দিয়ে `example.com`-এর আসল lookup চালানো হয়েছে। `dig` এই machine-এ নেই, তাই Section 9.4-এর `dig` command **চালানো হয়নি**। কোনো domain কেনা বা আসল DNS record বদলানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Domain কেনা থেকে browser-এ পৌঁছানো: registrar, registry, nameserver delegation, authoritative zone।
- Web hosting-এর জন্য দরকারি record: A, AAAA, CNAME, MX, TXT (SPF), CAA, NS, SOA, SRV।
- চারটি ক্লাসিক ভুল: **apex-এ CNAME**, CNAME-এর সাথে অন্য record, trailing dot বাদ, MX-এর লক্ষ্য CNAME।
- **TTL দিয়ে নিরাপদ migration:** কখন কমাবেন, কখন বদলাবেন, কখন পুরোনো server বন্ধ করবেন।
- Zone file পড়া ও lint করা; zone file-কে code হিসেবে রাখা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Nginx ও TLS (এই module-এর বাকি অংশ) কাজ করার আগে প্রথম প্রশ্ন: `taskflow.example.com` টাইপ করলে browser কোন IP-তে যাবে? DNS ভুল হলে বাকি সব configuration নিখুঁত হলেও site পৌঁছানো যায় না।

DNS-এর ভুলগুলো বিশেষভাবে বিপজ্জনক, কারণ:

- **Cache-এর কারণে ধীরে প্রকাশ পায়** — ভুল record আজ বসালেন, কিছু user কাল পর্যন্ত পুরোনো ঠিক উত্তর পাবেন। তারপর হঠাৎ সবার জন্য ভেঙে যায়।
- **Rollback-ও ধীর** — ঠিক করলেও ভুল উত্তর TTL পর্যন্ত cache-এ থাকে।
- Email (MX, SPF) ও certificate (CAA, ACME challenge) DNS-এর ওপর নির্ভর করে — একটি ভুল TXT record-এ পুরো company-র mail spam-এ যেতে পারে।

## 3. সহজ ভাষায় পরিচয়

| Record | কাজ | উদাহরণ |
|---|---|---|
| A / AAAA | নাম → IPv4 / IPv6 | `@ A 192.0.2.10` |
| CNAME | নাম → অন্য নাম (alias) | `www CNAME example.com.` |
| MX | Mail কোন server নেবে | `@ MX 10 mail.example.com.` |
| TXT | যাচাই, SPF, DKIM, DMARC | `@ TXT "v=spf1 … -all"` |
| CAA | কোন CA certificate দিতে পারে | `@ CAA 0 issue "letsencrypt.org"` |
| NS | Zone-এর authoritative server | `@ NS ns1.example.com.` |
| SOA | Zone-এর metadata (serial, negative TTL) | — |
| SRV | Service-এর host ও port | `_https._tcp SRV 0 5 443 web.` |

**Zone file-এর তিনটি নিয়ম:**

- `@` মানে zone নিজে (apex)।
- শেষে `.` না থাকা নাম relative — origin যোগ হয়।
- প্রথম column খালি থাকলে আগের লাইনের নাম।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ঠিকানার খাতা ও ডাকঘর

- **Registrar** = যে দোকান থেকে বাড়ির নাম রেজিস্ট্রি করালেন।
- **NS delegation** = পৌরসভার রেজিস্টারে লেখা: "এই বাড়ির ঠিকানার তথ্য ওই অফিস রাখে।"
- **A record** = আসল ঠিকানা (রাস্তা ও নম্বর)।
- **CNAME** = "আমার চিঠি আমার ভাইয়ের ঠিকানায় পাঠান" — নিজের ঠিকানা নয়, অন্যের নাম।
- **TTL** = কত দিন পর্যন্ত পিয়ন মুখস্থ রাখা ঠিকানা ব্যবহার করবেন, খাতা আবার না দেখে।

### Analogy কোথায় মেলে না

- **"এখানেও থাকি, ভাইয়ের কাছেও পাঠান" একসাথে বলা যায় না।** কোনো নামে CNAME থাকলে সেই নামে আর কোনো record (MX, TXT, A) থাকতে পারে না (RFC 1034)। Zone-এর apex-এ (`example.com`) সবসময় SOA ও NS থাকে, তাই apex-এ CNAME অসম্ভব। Provider-রা "ALIAS/ANAME/CNAME flattening" নামে নিজস্ব সমাধান দেয় — এটি DNS standard-এর অংশ নয়।
- **TTL কোনো চুক্তি নয়, অনুরোধ।** ঠিকানা বদলের নোটিশ সবার কাছে একসাথে পৌঁছায় না। কিছু resolver TTL-কে নিজের নিম্ন বা ঊর্ধ্বসীমায় বেঁধে দেয়, আর browser ও OS নিজেরাও cache রাখে। তাই "TTL ৫ মিনিট" মানে "বেশিরভাগ user ৫ মিনিটে" — সবাই নয়।
- **ভুল ঠিকানায় ডাক গেলে পিয়ন ফেরত আনেন।** "এই নামে কিছু নেই" (NXDOMAIN) উত্তরও cache হয় — SOA-র শেষ সংখ্যা পর্যন্ত (negative caching, RFC 2308)। নতুন record বানানোর আগে কেউ নামটা খুঁজে থাকলে, তিনি কিছুক্ষণ "নেই"-ই দেখবেন।

## 5. Real-world engineering scenario — "Server বদলালাম, অর্ধেক user পুরোনোতে"

**পরিস্থিতি:** TaskFlow নতুন server-এ (`198.51.100.20`) সরানো হলো। শুক্রবার সন্ধ্যায় A record বদলে, এক ঘণ্টা পরে পুরোনো server (`192.0.2.10`) বন্ধ করা হলো। TTL ছিল ৮৬,৪০০ s (১ দিন)।

শনিবার সকাল পর্যন্ত বহু user-এর resolver পুরোনো IP cache-এ রেখেছিল — তারা পেলেন connection timeout। Support বলল "আমাদের দিক থেকে সব ঠিক" (তাঁদের নিজের resolver নতুন IP পেয়েছিল)।

**সঠিক সময়রেখা** (`zone_lint.py plan` দিয়ে, আসল output):

```text
2026-11-02 01:00Z  lower TTL 86400s → 300s (at least 86400s before the change, +1h margin)
2026-11-03 02:00Z  change the record (new IP); keep the old server running
2026-11-03 02:05Z  most resolvers now see the new value (new TTL expired)
2026-11-04 02:00Z  worst case: a resolver that ignored the lowered TTL — then retire the old server
2026-11-04 03:00Z  raise TTL back (e.g. 86400s)
```

**শিক্ষা:**

- TTL কমানোর কাজটি পুরোনো TTL-এর **চেয়ে আগে** করতে হয়।
- Migration-এর সময় দুই server-ই চালু রাখুন।
- পুরোনো server-এর access log-এ traffic শূন্যে নামা দেখে তবেই বন্ধ করুন (L05-11)।

## 6. Diagram — `taskflow.example.com`-এর যাত্রা

```text
 browser ── stub resolver (OS cache) ── recursive resolver (ISP / 1.1.1.1, cache)
                                              │ cache-এ নেই
                                              ├─► root (.) ── "com.-এর NS ওরা"
                                              ├─► com. TLD ── "example.com.-এর NS: ns1.example.com." (delegation, registrar-এ সেট)
                                              └─► ns1.example.com. (authoritative, আমাদের zone file)
                                                     taskflow  300 IN A 198.51.100.20
                                              ◄── উত্তর + TTL 300 → cache 300 s
 browser ──TCP 443──► 198.51.100.20 (nginx, L06-02…)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Registrar / registry | Domain বিক্রেতা / TLD-এর মালিক (যেমন `.com`-এর Verisign) |
| Delegation | Parent zone-এ child-এর NS record |
| Authoritative server | Zone-এর আসল উত্তরদাতা |
| Recursive resolver | Client-এর হয়ে খুঁজে আনে ও cache রাখে |
| Apex / zone root | `example.com` নিজে (`@`) |
| TTL | Cache-এ কতক্ষণ রাখা যাবে |
| Negative caching | "নেই" উত্তর cache — SOA-র minimum/শেষ field |
| Glue record | NS-এর নাম zone-এর ভেতরে হলে parent-এ তার IP |
| ALIAS / CNAME flattening | Provider-এর apex-এ "CNAME-এর মতো" সুবিধা |
| SPF / DKIM / DMARC | Email-এর প্রেরক যাচাই (TXT) |
| CAA | কোন CA certificate দিতে পারবে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 CNAME-এর নিয়ম

Resolver কোনো নামে CNAME পেলে **সব ধরনের** প্রশ্নের জন্য লক্ষ্যে চলে যায় — MX, TXT, A সব। তাই একই নামে CNAME ও অন্য record থাকলে উত্তর অস্পষ্ট হয়, এবং RFC 1034 এটা নিষেধ করে।

MX ও NS-এর লক্ষ্য CNAME হতে পারে না (RFC 2181 §10.3)। কিছু mail server এমন MX প্রত্যাখ্যান করে।

### 8.2 Trailing dot

`app CNAME app.example.com` — শেষে `.` নেই, তাই relative। Origin যোগ হয়ে হয়ে যায় `app.example.com.example.com.`। Zone load-এ কোনো error হয় না — শুধু নামটা ভুল জায়গায় যায়। Web UI-ভিত্তিক DNS provider সাধারণত নিজে dot যোগ করে, কিন্তু zone file বা Terraform-এ (Module 12) এই ভুল খুব সাধারণ।

### 8.3 SPF

একটি নামে একাধিক `v=spf1` TXT থাকলে SPF-এর ফল `permerror` (RFC 7208 §3.2)। বেশিরভাগ receiver তখন SPF-কে অকার্যকর ধরে। নতুন email service যোগ করার সময় নতুন TXT নয় — পুরোনোটার ভেতরে `include:` যোগ করুন।

### 8.4 Web hosting-এর জন্য record পরিকল্পনা

| নাম | Record | কেন |
|---|---|---|
| `example.com` | A + AAAA (বা ALIAS) | Apex-এ CNAME নয় |
| `www` | CNAME → `example.com.` | এক জায়গায় IP |
| `taskflow` | A, TTL ৩০০ (migration-এর সময়) | দ্রুত বদল |
| `example.com` | CAA `issue "letsencrypt.org"` | অন্য CA ঠেকানো (L06-07) |
| `_acme-challenge` | TXT (প্রয়োজনে) | Wildcard certificate-এর DNS-01 |

> **Fedora-তে:** `dig`/`host` আসে `bind-utils` package থেকে (Ubuntu-তে `dnsutils`)। System resolver দুই distro-তেই `systemd-resolved` (`resolvectl query`)।

## 9. Practical demonstration

Files: [`code/L06-01/zone_lint.py`](code/L06-01/zone_lint.py), [`example-zone.txt`](code/L06-01/example-zone.txt) (হাতে তৈরি; ইচ্ছাকৃত ভুলসহ), [`test_l06_01.py`](code/L06-01/test_l06_01.py)।

### 9.1 Zone lint — আসল output

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-01
python3 zone_lint.py example-zone.txt; echo "exit=$?"
```

```text
WARNING line 0   no-caa                 no CAA at example.com. — any CA may issue certificates (RFC 8659)
ERROR   line 16  cname-at-apex          CNAME at zone apex example.com. (conflicts with SOA/NS) — use A/AAAA or provider ALIAS
WARNING line 18  mixed-ttl              api.example.com. A/AAAA records have different TTLs [60, 300]
ERROR   line 21  cname-and-other-data   api.example.com. has CNAME plus A, TXT (RFC 1034 §3.6.2)
ERROR   line 22  missing-trailing-dot   CNAME target 'app.example.com' has no trailing dot → becomes app.example.com.example.com.
ERROR   line 24  target-is-cname        MX target mail.example.com. is a CNAME (RFC 2181 §10.3)
ERROR   line 26  multiple-spf           example.com. has 2 SPF records — SPF permerror (RFC 7208 §3.2)
WARNING line 27  private-ip             internal.example.com. → 10.0.0.5 is private/loopback in a public zone
WARNING line 28  ttl-very-low           cdn.example.com. CNAME TTL 30s — resolver load, some ignore it
ERROR   line 29  target-is-cname        SRV target www.example.com. is a CNAME (RFC 2181 §10.3)
example.com.: 20 records, 6 error(s), 4 warning(s)
exit=1
```

শেষ লাইনটি সূক্ষ্ম: SRV-এর লক্ষ্য `www`, যা নিজে একটি CNAME। আলাদা আলাদা দেখলে দুটো record-ই ঠিক মনে হয়।

### 9.2 আসল lookup

```text
example.com ['104.20.23.154', '172.66.147.243'] 92 ms
www.example.com ['104.20.23.154', '172.66.147.243'] 54 ms
nonexistent-zz9.example.com gaierror: [Errno 11001] getaddrinfo failed 54 ms
```

(`socket.getaddrinfo`, ২০২৬-১০-২৭; IP সময়ের সাথে বদলাতে পারে।) অস্তিত্বহীন নামের উত্তরও দ্রুত এসেছে — negative উত্তরও cache হয়।

### 9.3 লেখার সময় ধরা পড়া bug

প্রথম সংস্করণে `ipaddress.ip_address(x).is_private` ব্যবহার করা হয়েছিল। ফলে `192.0.2.53`-এর মতো documentation IP-তেও "private" সতর্কতা আসছিল। আসলে চালিয়ে দেখা হলো:

```text
192.0.2.10 True      198.51.100.1 True      203.0.113.5 True      10.0.0.5 True      8.8.8.8 False
```

Python-এর `is_private` IANA-র special-purpose registry মানে, যেখানে documentation range-ও আছে। এটা **RFC 1918-এর সমার্থক নয়**। এখন স্পষ্ট তালিকা ব্যবহার হয়: 10/8, 172.16/12, 192.168/16, 100.64/10, loopback, link-local। একটি regression test আছে।

### 9.4 Ubuntu-তে (চালানো হয়নি)

```bash
sudo apt install dnsutils
dig +short example.com A
dig example.com SOA +noall +answer
dig +trace taskflow.example.com          # delegation-এর প্রতিটি ধাপ
dig @1.1.1.1 www.example.com +noall +answer +ttlid   # TTL কমতে দেখা — দুবার চালান
named-checkzone example.com example-zone.txt          # bind9-utils; BIND-এর নিজের যাচাই
```

`named-checkzone`-ও এই zone-এর apex CNAME ও CNAME-এর সাথে অন্য data প্রত্যাখ্যান করার কথা — তুলনা করুন।

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- Multi-line SOA, খালি owner column, TTL একক।
- Quote-এর ভেতরে `;`।
- পরিষ্কার zone।
- ৯টি নিয়মের প্রতিটি।
- Documentation IP private নয় (regression)।
- CAA/NS অনুপস্থিত।
- নমুনা zone।
- TTL পরিকল্পনা।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `strip_comment` (quote-সচেতন) | `;` comment বাদ | TXT-এর ভেতরের `;` রাখা (DKIM/DMARC-এ থাকে) |
| `logical_lines` | `( … )` জোড়া | SOA সাধারণত কয়েক লাইনে |
| `absolute()` | `@`, relative → absolute | তুলনা এক রূপে |
| `target_of` | CNAME/NS/MX/SRV-এর লক্ষ্য | Trailing dot ও CNAME-লক্ষ্য যাচাই |
| `INTERNAL_NETS` | RFC 1918 + CGNAT | `is_private`-এর ফাঁদ |
| `plan()` | TTL-ভিত্তিক সময়রেখা | Section 5 |
| Exit ১ error-এ | CI-তে zone file যাচাই | DNS-as-code (Module 12) |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `zone_lint.py example-zone.txt` | ৬টি error, ৪টি warning, exit ১ |
| `plan --old-ttl 86400 …` | পাঁচ ধাপের সময়রেখা |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Record বদলালাম, কিছু user পুরোনো IP-তে | TTL/cache | আগে TTL কমান; পুরোনো server চালু রাখুন |
| নতুন subdomain "নেই" দেখায় | Negative cache | SOA minimum পর্যন্ত অপেক্ষা; `dig @authoritative` দিয়ে যাচাই |
| Apex CNAME যোগ করতে দিচ্ছে না | RFC নিষেধ | A/AAAA বা provider-এর ALIAS |
| Mail spam-এ যাচ্ছে | দুটি SPF, বা DKIM/DMARC নেই | একটি SPF-এ `include:` |
| `app.example.com.example.com` | Trailing dot নেই | `.` যোগ |
| Domain হঠাৎ কাজ করছে না | Domain-এর মেয়াদ শেষ, বা registrar-এ NS বদলেছে | Registrar-এর auto-renew ও lock |
| Certificate issue ব্যর্থ | CAA অন্য CA-কে অনুমতি দেয় | CAA আপডেট (L06-07) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - **Dangling CNAME / subdomain takeover:** `shop CNAME old-app.cloudprovider.net.` রেখে cloud resource মুছে দিলে, অন্য কেউ সেই নাম নিয়ে আপনার subdomain-এ content দেখাতে পারে। Resource মুছলে record-ও মুছুন (Module 19)।
  - Registrar account-এ MFA ও registrar lock।
  - CAA।
  - DNSSEC বিবেচনা করুন।
  - Public zone-এ internal IP রাখলে network-এর ভেতরের মানচিত্র ফাঁস হয়।
- **Performance:**
  - কম TTL = বেশি query ও প্রথম request-এ বাড়তি latency (এখানে ৫৪–৯২ ms মাপা)।
  - Stable record-এ ঘণ্টা বা দিন; migration-এর সময় সাময়িক কম।
- **Cost:**
  - Managed DNS (Route 53) প্রতি zone ও প্রতি মিলিয়ন query-তে বিল করে — খুব কম TTL query বাড়ায় (Module 08)।
  - Domain renewal ভুলে গেলে মূল্যবান নাম হারানোর ঝুঁকি।

## 14. Hands-on exercise

1. `example-zone.txt`-এর সব error ঠিক করে `zone_lint.py` exit ০ করুন। Apex-এ কী বসালেন?
2. Ubuntu-তে `named-checkzone` ও `zone_lint.py`-এর ফল তুলনা করুন। কোন ভুল একটি ধরে, অন্যটি ধরে না?
3. `zone_lint.py`-এ DMARC যাচাই যোগ করুন: `_dmarc` TXT না থাকলে warning।
4. `dig +trace` দিয়ে একটি পরিচিত domain-এর delegation চেইন আঁকুন। কোন ধাপে কোন TTL?
5. Section 5-এর migration একটি checklist আকারে লিখুন, rollback-এর ধাপসহ।

## 15. Mini-project — DNS drift checker

`dns_drift.py zone.txt`:

- Zone file-এর প্রতিটি A/AAAA/CNAME-এর জন্য public resolver থেকে আসল উত্তর এনে তুলনা (L02-06-এর `dns_wire.py` বা `getaddrinfo`)।
- পার্থক্য (drift) ও NXDOMAIN দেখায়।
- CI-তে প্রতিদিন চালিয়ে "কেউ কি UI-তে হাতে record বদলেছে?" ধরা।

Module 12-এ DNS Terraform-এ গেলে এটা `terraform plan`-এর পরিপূরক।

## 16. Interview প্রশ্ন

1. `example.com`-এ CNAME কেন রাখা যায় না? বিকল্প কী?
2. DNS migration-এ TTL কীভাবে ব্যবহার করবেন? সময়রেখা বলুন।
3. Negative caching কী?
4. Subdomain takeover কী, এবং কীভাবে ঠেকাবেন?
5. A record বদলানোর পরেও একজন user পুরোনো site দেখছেন — কীভাবে debug করবেন?
6. CAA record কী কাজ করে?

## 17. Self-assessment প্রশ্ন

1. ঠিকানার খাতা analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ কোন দুটি ভুল হয়েছিল?
3. Trailing dot না থাকলে কী হয়, এবং কেন কোনো error আসে না?
4. `is_private` কেন private-IP যাচাইয়ের জন্য ভুল?
5. MX-এর লক্ষ্য কেন CNAME হতে পারে না?

## 18. সংক্ষিপ্ত সারাংশ

- Apex-এ A/AAAA (বা ALIAS); `www` ও অন্যগুলো CNAME।
- CNAME-এর সাথে আর কিছু নয়; MX/NS-এর লক্ষ্য CNAME নয়; trailing dot।
- Migration: আগে TTL কমান (পুরোনো TTL-এর আগে), দুই server-ই চালু রাখুন, log দেখে বন্ধ করুন।
- একটিই SPF; CAA রাখুন; dangling record মুছুন।
- Zone file-কে code হিসেবে রাখুন, CI-তে lint করুন।

## 19. Completion checklist

- [ ] নমুনা zone-এর সব error ঠিক করেছি
- [ ] Migration-এর সময়রেখা নিজে হিসাব করতে পারি
- [ ] (Ubuntu) `dig +trace` ও `named-checkzone` চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 1034 — Domain Names: Concepts and Facilities: https://www.rfc-editor.org/rfc/rfc1034
- RFC 1035 — Domain Names: Implementation and Specification: https://www.rfc-editor.org/rfc/rfc1035
- RFC 2181 — Clarifications to the DNS Specification: https://www.rfc-editor.org/rfc/rfc2181
- RFC 2308 — Negative Caching of DNS Queries: https://www.rfc-editor.org/rfc/rfc2308
- RFC 7208 — Sender Policy Framework (SPF): https://www.rfc-editor.org/rfc/rfc7208
- RFC 8659 — DNS Certification Authority Authorization (CAA): https://www.rfc-editor.org/rfc/rfc8659
- Python — `ipaddress`: https://docs.python.org/3/library/ipaddress.html
- BIND 9 Administrator Reference Manual: https://bind9.readthedocs.io/

---

**পরের lesson:** L06-02 — Nginx architecture: master, worker, event loop
