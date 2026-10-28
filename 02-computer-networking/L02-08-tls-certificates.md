# L02-08 — TLS, certificate ও HTTPS

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-07 — HTTP](L02-07-http.md) |
| **Label** | — |
| **Tested** | `tls_inspect.py`: ৮টি test পাস — `openssl` CLI (OpenSSL 3.5, Git Bash) দিয়ে **temporary directory-তে** নিজের CA ও server certificate তৈরি করে loopback TLS server-এ: সফল verify, IP SAN, hostname mismatch, untrusted CA, expiry warning (Python 3.14, Windows)। `lab` ও **আসল site-এ inspect** চালানো হয়েছে (২০২৬-১০-২৬): `example.com`, `expired.badssl.com`, `wrong.host.badssl.com` — output Section 9-এ। `openssl s_client`, certbot ও Ubuntu CA store-এ CA যোগ **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- TLS তিনটি জিনিস দেয়: **গোপনীয়তা** (encryption), **অখণ্ডতা** (integrity), **পরিচয়** (authentication)।
- TLS 1.3 handshake-এর মূল ধাপ; SNI ও ALPN।
- Certificate কী: public key + পরিচয় + issuer-এর সই; **SAN**, মেয়াদ।
- **Chain of trust**: root CA → intermediate → leaf; trust store।
- Client verify-তে কী কী যাচাই করে — এবং `verify=False` কেন বিপজ্জনক।
- নিজের CA দিয়ে certificate তৈরি (lab), `openssl s_client` ও `openssl x509` দিয়ে diagnosis।
- Certificate মেয়াদ শেষ হওয়া — সবচেয়ে প্রতিরোধযোগ্য outage — এবং monitoring।
- mTLS-এর পরিচয়।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L02-07-এ plain HTTP-র প্রতিটি byte পথের যে কেউ (Wi-Fi, ISP, compromised router) পড়তে ও বদলাতে পারে — password, token, API key সহ। এছাড়া আপনি কীভাবে জানবেন `bank.example`-এর সাথেই কথা বলছেন, নকলের সাথে নয়?

DevOps-এ TLS-সম্পর্কিত কাজ ও incident:

- Certificate expire হয়ে পুরো site বা internal API বন্ধ — বড় বড় কোম্পানিতেও বহুবার ঘটেছে।
- `x509: certificate signed by unknown authority` — container-এ CA bundle নেই বা internal CA trust করা হয়নি।
- Load balancer-এ TLS termination, backend-এ re-encryption।
- Kubernetes: cert-manager, Ingress TLS, service mesh mTLS (Module 14, 19)।
- Intermediate certificate বাদ পড়ায় কিছু client-এ কাজ করে, কিছুতে করে না।

## 3. সহজ ভাষায় পরিচয়

**TLS** (Transport Layer Security) = TCP-র (বা QUIC-এর) উপর একটি স্তর যা data encrypt করে ও server-এর পরিচয় প্রমাণ করে। **HTTPS** = HTTP over TLS (port ৪৪৩)। SSL হলো পুরোনো, এখন অনিরাপদ পূর্বসূরি — নামটা রয়ে গেছে।

**Certificate** (X.509) = একটি সই-করা দলিল:

| অংশ | উদাহরণ |
|---|---|
| Subject | `CN=example.com` |
| **Subject Alternative Name (SAN)** | `DNS:example.com, DNS:*.example.com` — **আসলে এটাই** hostname যাচাইয়ে ব্যবহৃত হয় |
| Public key | EC P-256 বা RSA 2048+ |
| Issuer | কে সই করেছে — `Cloudflare TLS Issuing ECC CA 3` |
| মেয়াদ | `notBefore` … `notAfter` |
| Extension | CA কিনা, কী কাজে ব্যবহার করা যাবে (serverAuth) |
| সই | Issuer-এর private key দিয়ে |

**Private key** server-এর কাছে গোপন থাকে; certificate (public key সহ) সবাইকে দেখানো হয়।

**Chain of trust:**

```text
Root CA  (self-signed; OS/browser-এর trust store-এ আগে থেকেই আছে)
   └─ সই করে → Intermediate CA  (server পাঠায়)
                  └─ সই করে → Leaf certificate: example.com  (server পাঠায়)
```

Client leaf থেকে উপরে উঠে এমন একটি root-এ পৌঁছাতে চায় যেটা সে আগে থেকেই বিশ্বাস করে।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### জাতীয় পরিচয়পত্র

- **Certificate** = NID কার্ড: নাম (SAN), ছবি (public key), মেয়াদ, ও নির্বাচন কমিশনের সিল (issuer-এর সই)।
- **CA** = নির্বাচন কমিশন — যাকে সবাই বিশ্বাস করে।
- **Verify** = ব্যাংক কর্মকর্তা দেখেন: সিল আসল? মেয়াদ আছে? কার্ডের নাম আর সামনের মানুষ একই?
- **Private key** = মানুষটি নিজে। কার্ডের ছবি আর মুখ মিলতে হবে — handshake-এ server প্রমাণ করে যে private key তার কাছেই আছে।

### Analogy কোথায় মেলে না

- কার্ড চুরি করলেও ছবি মিলবে না। কিন্তু **private key চুরি হলে** চোর নিখুঁতভাবে server সাজতে পারে, এবং certificate মেয়াদ পর্যন্ত বৈধ থাকে (revocation বাস্তবে দুর্বল)। তাই key-র নিরাপত্তা এবং **ছোট মেয়াদের certificate + স্বয়ংক্রিয় নবায়ন** এখনকার নিয়ম।
- পরিচয়পত্র যাচাই একবার হয়। TLS-এ প্রতিটি connection-এ যাচাই, আর এর পরে প্রতিটি byte encrypt ও integrity-check হয় — কার্ড দেখানোর পরে পুরো কথোপকথন একটি সিলমোহর-করা খামে।
- বিশ্বে "নির্বাচন কমিশন" একটি নয় — trust store-এ ১০০-র বেশি root CA, এবং **যেকোনো একটি** যেকোনো domain-এর জন্য certificate দিতে পারে। এই দুর্বলতা কমাতে Certificate Transparency log (সব issued certificate প্রকাশ্য) ও CAA DNS record।

## 5. Real-world engineering scenario — শুক্রবার রাতের expiry

**পরিস্থিতি:** Internal payment API (`pay.internal.example`) হঠাৎ সব client-এ ব্যর্থ। Client log: `certificate has expired`। এক বছর আগে কেউ হাতে certificate বসিয়েছিলেন; তিনি এখন অন্য team-এ। Calendar reminder ছিল তাঁর ব্যক্তিগত calendar-এ।

**তাৎক্ষণিক diagnosis:**

```bash
echo | openssl s_client -connect pay.internal.example:443 -servername pay.internal.example 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
# notAfter=... (গতকাল)
```

**তাৎক্ষণিক সমাধান:** নতুন certificate issue → load balancer/server-এ বসানো → reload। তারপর **chain সহ** পাঠানো হচ্ছে কিনা যাচাই (Section 12)।

**Postmortem-এর action item:**

1. **স্বয়ংক্রিয় নবায়ন:** ACME (Let's Encrypt/certbot, cert-manager) বা cloud-managed certificate (AWS ACM-এর মতো, যেগুলো নিজে নবায়ন করে)।
2. **Monitoring:** প্রতিটি endpoint-এর `notAfter` নিয়মিত পরীক্ষা, ৩০/১৪/৭ দিনে alert — এই lesson-এর `tls_inspect.py inspect ... --warn-days 21` exit ১ দেয়, cron/CI-তে চালানো যায়।
3. **Inventory:** কোন certificate কোথায় — ব্যক্তির মাথায় নয়, repository-তে।

**শিক্ষা:** Certificate expiry হলো সম্পূর্ণ পূর্বানুমেয় outage — তারিখ certificate-এর ভেতরেই লেখা। শুধু automation আর monitoring দরকার।

## 6. Diagram — TLS 1.3 handshake (সরলীকৃত)

```text
Client                                                  Server
  │  TCP handshake (L02-05)                               │
  │── ClientHello ───────────────────────────────────────►│  সমর্থিত cipher, key share,
  │     SNI: example.com   ALPN: h2, http/1.1             │  SNI = কোন site চাই (একই IP-তে বহু site)
  │                                                       │
  │◄─ ServerHello (key share, cipher বাছাই) ──────────────│  ── এখান থেকে সব encrypted ──
  │◄─ Certificate (leaf + intermediate) ──────────────────│
  │◄─ CertificateVerify (private key দিয়ে সই) ──────────│  "key আমার কাছে আছে" প্রমাণ
  │◄─ Finished ───────────────────────────────────────────│
  │                                                       │
  │  Client verify: chain → trusted root? মেয়াদ? SAN-এ    │
  │  hostname? সই ঠিক? ─ কোনোটা ব্যর্থ = connection বন্ধ  │
  │── Finished ──────────────────────────────────────────►│
  │══ Application data (HTTP), encrypted ═════════════════│   TLS 1.3: ১ RTT (TLS 1.2: ২ RTT)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| TLS / SSL | Encryption স্তর / পুরোনো, পরিত্যক্ত নাম |
| Certificate (X.509) | Public key + পরিচয় + issuer-এর সই |
| CA | Certificate Authority — যে সই করে |
| Root / intermediate / leaf | Chain-এর শীর্ষ / মাঝের / server-এর নিজের |
| Trust store | যেসব root CA বিশ্বাস করা হয় (Ubuntu: `/etc/ssl/certs/`) |
| SAN | Certificate কোন কোন নামের জন্য বৈধ |
| SNI | ClientHello-তে কাঙ্ক্ষিত hostname |
| ALPN | TLS-এর ভেতরে protocol (h2/http1.1) আলোচনা |
| CSR | Certificate Signing Request — CA-র কাছে আবেদন |
| PEM / DER | Base64 text (`-----BEGIN CERTIFICATE-----`) / binary format |
| Cipher suite | কোন algorithm-এর সমষ্টি (যেমন `TLS_AES_256_GCM_SHA384`) |
| Forward secrecy | পরে key ফাঁস হলেও পুরোনো traffic decrypt করা যায় না (ephemeral key exchange) |
| TLS termination | Load balancer/proxy-তে TLS খোলা |
| mTLS | দুই পক্ষই certificate দেখায় |
| ACME | স্বয়ংক্রিয় certificate issue/নবায়নের protocol (Let's Encrypt) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Client verify-তে কী যাচাই হয়

1. **Chain:** leaf → intermediate → trust store-এর কোনো root পর্যন্ত, প্রতিটি সই বৈধ।
2. **মেয়াদ:** এখনকার সময় `notBefore`–`notAfter`-এর মধ্যে। (তাই ভুল system clock-এ TLS ভাঙে।)
3. **Hostname:** যে নামে connect করেছেন তা SAN-এ আছে (wildcard `*.example.com` শুধু এক স্তর মেলে — `a.example.com` হ্যাঁ, `a.b.example.com` না)। IP দিয়ে connect করলে SAN-এ `IP:` entry লাগে।
4. **ব্যবহার:** leaf-এ `serverAuth`, intermediate-এ `CA:TRUE`।

একটি ব্যর্থ = connection বন্ধ। **`verify=False` / `curl -k` / `InsecureSkipVerify`** এই সব বন্ধ করে — encryption থাকে, কিন্তু অপর পক্ষ কে তা অজানা, তাই man-in-the-middle সহজ। Production code-এ কখনো নয়; সঠিক সমাধান হলো সঠিক CA trust করা (`--cafile`)।

### 8.2 Key exchange ও symmetric encryption

Handshake-এ (EC)DHE দিয়ে দুই পক্ষ একটি গোপন session key তৈরি করে, যা নেটওয়ার্কে কখনো পাঠানো হয় না। এরপর দ্রুত symmetric cipher (AES-GCM, ChaCha20) দিয়ে data। Certificate-এর private key শুধু **পরিচয় প্রমাণে** (সই) লাগে — তাই key পরে ফাঁস হলেও পুরোনো recorded traffic decrypt করা যায় না (forward secrecy)।

### 8.3 TLS কোথায় শেষ হয়

```text
Client ══TLS══► Load balancer ──plain HTTP──► backend      (edge termination)
Client ══TLS══► Load balancer ══TLS══► backend             (re-encryption)
Client ══TLS══════════════════════════► backend            (passthrough, L4)
```

Termination-এর পরে internal network-এ plain HTTP — "internal = নিরাপদ" ধারণা zero-trust-এ বাতিল (L02-11, Module 19)। Service mesh সব pod-to-pod-এ স্বয়ংক্রিয় mTLS দেয়।

### 8.4 Ubuntu-তে trust store

- System CA bundle: `/etc/ssl/certs/ca-certificates.crt` (`ca-certificates` package)।
- Internal CA যোগ: `.crt` file `/usr/local/share/ca-certificates/`-এ রেখে `sudo update-ca-certificates`।
- Python `ssl` সাধারণত system store ব্যবহার করে; `requests` নিজের `certifi` bundle ব্যবহার করে (`REQUESTS_CA_BUNDLE` দিয়ে বদলানো যায়)। Container image-এ `ca-certificates` না থাকলে সব HTTPS ব্যর্থ।

> **Fedora-তে:** trust store `/etc/pki/ca-trust/`; internal CA যোগ: `/etc/pki/ca-trust/source/anchors/`-এ রেখে `sudo update-ca-trust`।

## 9. Practical demonstration

File: [`code/L02-08/tls_inspect.py`](code/L02-08/tls_inspect.py)

### 9.1 Lab — নিজের CA, নিজের server

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-08
python3 tls_inspect.py lab
```

Script `openssl` দিয়ে একটি **temporary directory**-তে Lab Root CA ও `localhost`-এর certificate (SAN: `DNS:localhost`, `IP:127.0.0.1`) তৈরি করে, loopback-এ TLS server চালায় ও তিনভাবে connect করে। শেষে সব key মুছে যায়।

**আসল output (২০২৬-১০-২৬):**

```text
1) trusted CA + correct name  -> OK
  protocol  TLSv1.3   cipher TLS_AES_256_GCM_SHA384
  subject   commonName=localhost
  issuer    commonName=Lab Root CA
  SAN       DNS:localhost, IP Address:127.0.0.1
  expires   Nov 25 15:50:31 2026 GMT  (30.0 days left)

2) trusted CA + WRONG name (api.example.com)  -> FAILED: Hostname mismatch, certificate is not valid for 'api.example.com'.

3) system CA store only (lab CA not trusted)  -> FAILED: unable to get local issuer certificate

temporary keys and certificates deleted
```

তিনটি পরিস্থিতিতে **একই server, একই certificate** — শুধু client-এর trust ও কাঙ্ক্ষিত নাম ভিন্ন। Production error message-গুলো (`unable to get local issuer certificate`, `Hostname mismatch`) এখানেই নিয়ন্ত্রিতভাবে দেখা যায়।

### 9.2 আসল site

```bash
python3 tls_inspect.py inspect example.com
python3 tls_inspect.py inspect expired.badssl.com;    echo "exit=$?"
python3 tls_inspect.py inspect wrong.host.badssl.com; echo "exit=$?"
```

`badssl.com` ইচ্ছাকৃতভাবে ভাঙা certificate-এর পরীক্ষার জন্য তৈরি public test site।

**আসল output (২০২৬-১০-২৬; issuer ও তারিখ সময়ের সাথে বদলায়):**

```text
example.com:443
  protocol  TLSv1.3   cipher TLS_AES_256_GCM_SHA384
  subject   commonName=example.com
  issuer    countryName=US, organizationName=SSL Corporation, commonName=Cloudflare TLS Issuing ECC CA 3
  SAN       DNS:example.com, DNS:*.example.com
  expires   Dec 25 22:56:35 2026 GMT  (60.3 days left)
exit=0
```

```text
VERIFY FAILED: certificate has expired
exit=1
VERIFY FAILED: Hostname mismatch, certificate is not valid for 'wrong.host.badssl.com'.
exit=1
```

**পর্যবেক্ষণ:** issuer একটি **intermediate** (Cloudflare-এর) — root নয়; L02-07-এ দেখা CDN-ই TLS terminate করছে। SAN-এ wildcard। মেয়াদ ৬০ দিন বাকি — ছোট মেয়াদের, স্বয়ংক্রিয়ভাবে নবায়ন হওয়া certificate-এর লক্ষণ।

### 9.3 `openssl` — দৈনন্দিন tool (Ubuntu VM)

```bash
# server কী পাঠাচ্ছে: পুরো chain, protocol, verify ফল
echo | openssl s_client -connect example.com:443 -servername example.com -showcerts 2>/dev/null | less
#   "Verify return code: 0 (ok)" খুঁজুন; "depth=" লাইনগুলোতে chain

# শুধু মেয়াদ ও নাম
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName

# local file পরীক্ষা
openssl x509 -in cert.pem -noout -text | less
openssl x509 -in cert.pem -noout -checkend $((21*86400)) && echo "21 দিনের বেশি বাকি"
openssl verify -CAfile ca.crt -untrusted intermediate.crt leaf.crt

# key ও certificate মেলে কিনা (একই public key)
openssl x509 -in leaf.crt -noout -pubkey | sha256sum
openssl pkey -in leaf.key -pubout | sha256sum

curl -v https://example.com/ -o /dev/null 2>&1 | grep -E 'SSL|TLS|subject|issuer|expire'
```

`-servername` (SNI) বাদ দিলে একই IP-তে বহু site থাকা server ভুল (default) certificate দিতে পারে — একটি প্রচলিত বিভ্রান্তি।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_tls_inspect.py`](code/L02-08/test_tls_inspect.py)-এর ৮টি test: days-left হিসাব, name format, client context কঠোর (CERT_REQUIRED, hostname check, TLS ≥ 1.2), এবং `openssl` থাকলে temporary CA দিয়ে: সফল verify, IP SAN, hostname mismatch, untrusted CA, CLI-র `--warn-days` exit code। `openssl` না থাকলে lab test skip হয়।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `ssl.create_default_context(cafile=...)` | Verify ও hostname check চালু | নিরাপদ default; কখনো বন্ধ নয় |
| `minimum_version = TLSv1_2` | পুরোনো protocol প্রত্যাখ্যান | TLS 1.0/1.1 অনিরাপদ |
| `wrap_socket(server_hostname=...)` | SNI পাঠায় ও hostname যাচাই করে | একটি parameter, দুটি কাজ |
| `getpeercert()` | Verified certificate-এর dict | Verify বন্ধ থাকলে খালি — তাই tool সবসময় verify করে |
| `SSLCertVerificationError.verify_message` | মানুষের পড়ার মতো কারণ | Alert-এ সরাসরি ব্যবহারযোগ্য |
| `make_ca_and_leaf` | `openssl req -x509` (CA) → CSR → `x509 -req` (SAN সহ sign) | আসল CA-র কাজের ছোট সংস্করণ |
| `tempfile.TemporaryDirectory` | Key শুধু temp-এ, শেষে মুছে | Private key কখনো repository-তে নয় |
| Server-এ `except ssl.SSLError` | Client verify ব্যর্থ হলে handshake ভাঙে | প্রত্যাশিত, server থামে না |

**Python কেন এখানে, কোথায় নয়:** monitoring script ও automation-এ ভালো (exit code, alert)। Certificate তৈরিতে production-এ `openssl`/ACME client/cert-manager/cloud certificate service; key ব্যবস্থাপনায় secret manager বা HSM/KMS (Module 19)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `tls_inspect.py lab` | 1) OK, 2) Hostname mismatch, 3) unable to get local issuer |
| `inspect example.com` | TLSv1.2/1.3, issuer একটি intermediate, exit ০ |
| `inspect expired.badssl.com` | `certificate has expired`, exit ১ |
| `openssl s_client ...` | `Verify return code: 0 (ok)` |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `certificate has expired` | মেয়াদ শেষ — বা client-এর ঘড়ি ভুল | `openssl x509 -dates`; `date`, `timedatectl` | নবায়ন; NTP (L01-18) |
| `unable to get local issuer certificate` | Server intermediate পাঠায় না, বা root trust store-এ নেই | `s_client -showcerts` — কয়টি cert? | Server-এ **full chain** দিন; internal CA trust store-এ যোগ |
| Browser-এ ঠিক, `curl`/Python-এ ব্যর্থ | Intermediate নেই — browser cache থেকে পূরণ করে | উপরের মতো | Full chain |
| `Hostname mismatch` | SAN-এ নাম নেই / ভুল SNI / IP দিয়ে connect | `-ext subjectAltName` | সঠিক নাম বা SAN-সহ নতুন cert |
| Container-এ সব HTTPS ব্যর্থ | Image-এ CA bundle নেই | `ls /etc/ssl/certs` | `ca-certificates` install |
| `key values mismatch` (server চালু হয় না) | ভুল key-cert জোড়া | Section 9.3-এর pubkey hash | সঠিক জোড়া |
| `wrong version number` | TLS port-এ plain HTTP, বা উল্টো | `curl http://` বনাম `https://` | সঠিক scheme/port |
| Corporate network-এ সব site-এর issuer একটি অচেনা CA | TLS-inspecting proxy | issuer দেখুন | Organization-এর CA trust (নীতি অনুযায়ী) |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Private key-র permission `600`, কখনো Git-এ নয় (এই repository-র `.gitignore`-এ `*.key`, `*.pem`); ছোট মেয়াদ + স্বয়ংক্রিয় নবায়ন; TLS ≥ 1.2, পুরোনো cipher বন্ধ; `verify=False` code review-তে আটকান (Module 19-এর static analysis-এ ধরা যায়); HSTS header; CAA record (কোন CA আপনার domain-এ issue করতে পারবে)। Key ফাঁস হলে: নতুন key + নতুন certificate + revoke।
- **Performance:** TLS 1.3-এ ১ RTT; session resumption; ECDSA key RSA-র চেয়ে দ্রুত; keep-alive (L02-07) handshake খরচ ভাগ করে। আধুনিক CPU-তে encryption খরচ সামান্য — "performance-এর জন্য TLS বন্ধ" আজকাল যুক্তিসঙ্গত নয়।
- **Cost:** Let's Encrypt ও cloud-managed public certificate (যেমন ACM, load balancer-এর সাথে) সাধারণত বিনামূল্যে; private CA service-এর মাসিক খরচ আছে (Module 08)। সবচেয়ে বড় খরচ expiry outage।

## 14. Hands-on exercise

1. `lab`-এর পরে নিজে হাতে Section 9.3-এর `openssl` command দিয়ে একটি CA ও leaf বানান (একটি `~/tls-lab/` directory-তে, repository-র বাইরে)। `openssl verify` দিয়ে chain যাচাই করুন।
2. `python3 -m http.server`-কে TLS দিয়ে মোড়ানো একটি ছোট script লিখুন (`ssl.SSLContext.wrap_socket`)। `curl --cacert ca.crt https://localhost:8443/` সফল, `curl https://localhost:8443/` ব্যর্থ — দুটির error লিখুন।
3. Ubuntu VM-এ Lab CA-কে system trust store-এ যোগ করুন (Section 8.4), এবার `curl` `--cacert` ছাড়াই কাজ করে কিনা দেখুন। **তারপর সরিয়ে ফেলুন** (`sudo rm` + `sudo update-ca-certificates --fresh`) — lab CA বিশ্বাস করে রাখা নিরাপত্তা ঝুঁকি।
4. পাঁচটি পরিচিত site-এ `tls_inspect.py inspect` চালিয়ে issuer, মেয়াদ বাকি ও SAN সংখ্যা তুলনা করুন।
5. `badssl.com`-এর আরো কয়েকটি subdomain (`self-signed`, `untrusted-root`, `incomplete-chain`) পরীক্ষা করে error message-এর তালিকা বানান।

## 15. Mini-project — Certificate expiry monitor

একটি `endpoints.txt` (host:port প্রতি লাইনে) পড়ে প্রতিটি endpoint `inspect` করবে; table আকারে issuer, মেয়াদ বাকি, অবস্থা (OK / WARN / CRITICAL / VERIFY FAILED) দেখাবে; সবচেয়ে খারাপ অবস্থা অনুযায়ী exit code। systemd timer (L01-11) দিয়ে প্রতিদিন চালান। Module 20-এ এটি Prometheus metric হবে (blackbox exporter-এর `probe_ssl_earliest_cert_expiry`-এর ধারণা)।

## 16. Interview প্রশ্ন

1. TLS handshake-এ কী কী ঘটে (TLS 1.3)?
2. Client certificate verify করার সময় কী কী যাচাই করে?
3. Chain of trust ও intermediate certificate কী? Intermediate বাদ পড়লে কী হয়?
4. SNI কী এবং কেন দরকার?
5. TLS termination load balancer-এ করার সুবিধা ও ঝুঁকি।
6. mTLS কী, কোথায় ব্যবহার হয়?
7. Certificate expiry কীভাবে প্রতিরোধ করবেন?
8. `verify=False` ব্যবহার কেন ভুল এবং সঠিক বিকল্প কী?

## 17. Self-assessment প্রশ্ন

1. NID কার্ড analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Lab-এর তিনটি পরিস্থিতিতে server একই — তাহলে ফল ভিন্ন কেন?
3. Forward secrecy কী এবং certificate-এর private key কোন কাজে লাগে?
4. Browser-এ কাজ করে কিন্তু `curl`-এ ব্যর্থ — সবচেয়ে সম্ভাব্য কারণ?
5. Section 5-এর তিনটি action item কী?

## 18. সংক্ষিপ্ত সারাংশ

- TLS = encryption + integrity + server-এর পরিচয়; HTTPS = HTTP over TLS।
- Certificate = public key + SAN + issuer-এর সই + মেয়াদ; chain → trusted root।
- Verify: chain, মেয়াদ, hostname (SAN), ব্যবহার — একটি ব্যর্থ মানেই বন্ধ। `verify=False` নয়, সঠিক CA trust।
- Server-এ **full chain**; private key গোপন ও Git-এর বাইরে।
- Expiry = পূর্বানুমেয় outage — automation (ACME/managed) + monitoring।
- Diagnosis: `openssl s_client -servername`, `openssl x509 -dates`।

## 19. Completion checklist

- [ ] `tls_inspect.py lab` চালিয়ে তিনটি পরিস্থিতি ব্যাখ্যা করতে পারি
- [ ] আসল site ও badssl-এ inspect চালিয়েছি
- [ ] হাতে CA ও leaf বানিয়ে `openssl verify` করেছি (Exercise ১)
- [ ] Trust store-এ CA যোগ করে **আবার সরিয়েছি** (Exercise ৩)
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 8446 — TLS 1.3: https://www.rfc-editor.org/rfc/rfc8446
- RFC 5280 — X.509 certificate profile: https://www.rfc-editor.org/rfc/rfc5280
- RFC 8555 — ACME: https://www.rfc-editor.org/rfc/rfc8555
- Python `ssl`: https://docs.python.org/3/library/ssl.html
- OpenSSL command documentation: https://docs.openssl.org/master/man1/
- Let's Encrypt — How it works: https://letsencrypt.org/how-it-works/
- badssl.com (test site): https://badssl.com/
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/

---

**পরের lesson:** L02-09 — DHCP, ICMP, MTU ও path MTU discovery
