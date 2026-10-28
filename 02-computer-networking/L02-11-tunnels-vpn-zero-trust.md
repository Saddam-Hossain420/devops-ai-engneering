# L02-11 — SSH tunnel, VPN, WireGuard ও zero-trust connectivity

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Advanced |
| **আনুমানিক সময়** | ৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-13 — SSH](../01-linux-systems/L01-13-ssh-remote-access.md), [L02-04 — Routing/NAT](L02-04-routing-nat.md), [L02-09 — MTU](L02-09-dhcp-icmp-mtu.md), [L02-10 — Firewall](L02-10-firewalls.md) |
| **Label** | 🔗 MULTI — practical-এর জন্য দুটি VM (বা VM + host) লাগে |
| **Tested** | `port_forward.py` ও `wg_lint.py`: ৭টি test পাস — loopback-এ আসল forwarding (১৫০ KB, byte গণনা মেলানো), target বন্ধ থাকলে আচরণ, WireGuard config parse/lint (synthetic key) (Python 3.14, Windows)। `demo` ও `wg_lint.py sample-wg0.conf` চালানো হয়েছে — output Section 9-এ। `ssh -L/-R/-D/-J`, `wg-quick`, `wg show` **দুটি Ubuntu VM-এ চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Private network-এর ভেতরের service-এ বাইরে থেকে নিরাপদে পৌঁছানোর তিনটি পদ্ধতি: **SSH tunnel**, **VPN**, **zero-trust access**।
- SSH port forwarding: `-L` (local), `-R` (remote), `-D` (SOCKS), `-J` (ProxyJump / bastion)।
- VPN-এর ধরন: remote-access ও site-to-site; IPsec, OpenVPN, **WireGuard**।
- WireGuard-এর মূল ধারণা: key pair, **cryptokey routing (AllowedIPs)**, UDP, keepalive, MTU।
- Zero trust: "network-এ আছে বলে বিশ্বাস নয়" — identity-ভিত্তিক, প্রতিটি request-এ যাচাই।
- Python দিয়ে port forwarder (tunnel-এর মূল কৌশল) ও WireGuard config linter।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L02-10-এ শিখেছেন database, admin panel, SSH Internet-এ খোলা রাখা যাবে না। কিন্তু engineer-দের সেগুলোতে পৌঁছাতে হয়:

- Private subnet-এর PostgreSQL-এ migration চালানো বা query।
- Internal Grafana/Prometheus dashboard দেখা।
- Office network ও cloud VPC-কে যুক্ত করা।
- ১০০ জন engineer, contractor, CI runner — কে কোথায় পৌঁছাবে, কে কখন কী করেছে?

ভুল পদ্ধতির পরিণতি: "সাময়িকভাবে" খোলা security group যা কেউ বন্ধ করে না; সবার জন্য একটি shared VPN যার মাধ্যমে একটি চুরি যাওয়া laptop পুরো network-এ পৌঁছায়; key কারো পুরোনো laptop-এ রয়ে যায়।

## 3. সহজ ভাষায় পরিচয়

### SSH tunnel — "একটি নির্দিষ্ট port-এর জন্য গোপন পাইপ"

```bash
ssh -L 15432:db.internal:5432 user@bastion.example.com
```

অর্থ: "আমার laptop-এর `127.0.0.1:15432`-এ যা আসবে, SSH connection দিয়ে bastion-এ নিয়ে যাও, তারপর bastion থেকে `db.internal:5432`-এ পাঠাও।" এরপর `psql -h 127.0.0.1 -p 15432` চালালে আপনি private database-এ।

| Flag | নাম | দিক | ব্যবহার |
|---|---|---|---|
| `-L lport:host:hport` | Local forward | Local → remote-এর পাশের host | Private DB/dashboard-এ পৌঁছানো |
| `-R rport:host:hport` | Remote forward | Remote → আপনার পাশের host | NAT-এর পেছনের machine থেকে কিছু দেখানো (সাবধান!) |
| `-D port` | Dynamic (SOCKS proxy) | যেকোনো গন্তব্য | Browser-কে remote network দিয়ে চালানো |
| `-J bastion` | ProxyJump | Bastion পার হয়ে আরেকটি host-এ SSH | Private instance-এ SSH |
| `-N` | কোনো command নয় | — | শুধু tunnel |

### VPN — "পুরো network-এর জন্য গোপন রাস্তা"

VPN একটি virtual network interface তৈরি করে (যেমন `wg0`); routing table (L02-04) অনুযায়ী নির্দিষ্ট গন্তব্যের packet এই interface দিয়ে encrypt হয়ে যায়। Application-কে কিছু জানতে হয় না।

| ধরন | উদাহরণ |
|---|---|
| Remote access | Engineer-এর laptop → office/VPC |
| Site-to-site | Office router ↔ cloud VPC (AWS Site-to-Site VPN, IPsec) |

| Protocol | বৈশিষ্ট্য |
|---|---|
| IPsec | পুরোনো, standard, cloud ও router-এ সর্বত্র; configuration জটিল |
| OpenVPN | TLS-ভিত্তিক, নমনীয়, user-space — তুলনামূলক ধীর |
| **WireGuard** | ছোট codebase, Linux kernel-এ অন্তর্ভুক্ত (5.6+), আধুনিক cryptography, UDP, সরল config |

### Zero trust — "network নয়, পরিচয়"

পুরোনো model: VPN-এ ঢুকলেই "ভেতরের মানুষ" — সব কিছুতে পৌঁছানো যায় (castle-and-moat)। **Zero trust**: প্রতিটি request-এ যাচাই — **কে** (identity, SSO, MFA), **কোন device** (device posture), **কোন resource**, **এখন অনুমতি আছে কি** — এবং শুধু সেই নির্দিষ্ট application-এ access। উদাহরণ: identity-aware proxy, AWS Systems Manager Session Manager (SSH port খোলাই লাগে না), Tailscale/Cloudflare Access-এর মতো product, Kubernetes-এ mTLS service mesh (L02-08)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ব্যাংকের ভল্ট

- **SSH tunnel** = নির্দিষ্ট একটি লকারে পৌঁছানোর জন্য একজন প্রহরী (bastion) আপনাকে নিয়ে যান। প্রতি লকারের জন্য আলাদা অনুরোধ।
- **VPN** = ব্যাংকের ভেতরে ঢোকার চাবি — ঢুকলে করিডোরের সব দরজার সামনে যেতে পারেন।
- **Zero trust** = প্রতিটি দরজায় আলাদা পরিচয়-যাচাই — ভেতরে থাকলেও; এবং প্রতিটি প্রবেশ লেখা থাকে।
- **WireGuard-এর AllowedIPs** = প্রতিটি চাবির গায়ে লেখা "এই চাবি দিয়ে শুধু এই ঘরগুলো" — এবং কোন ঘরের চিঠি কোন চাবিধারীর কাছে যাবে।

### Analogy কোথায় মেলে না

- ভল্টে প্রবেশ মানুষ দেখে। Network-এ "পরিচয়" = একটি key বা token — **চুরি হলে চোর হুবহু আপনি**। তাই key-র মেয়াদ, MFA, device binding, এবং দ্রুত revoke করার ক্ষমতা গুরুত্বপূর্ণ।
- `ssh -R` analogy-তে নেই এমন ঝুঁকি: এটি **উল্টো দিকে** দরজা খোলে — remote machine-এর মানুষ আপনার network-এ ঢুকতে পারে। Corporate network থেকে বাইরে `-R` প্রায়ই নীতিবিরুদ্ধ।
- VPN tunnel "নিরাপদ পাইপ" — কিন্তু tunnel-এর অপর প্রান্তের network compromise হলে পাইপ দিয়ে আক্রমণও আসে। Encryption ≠ authorization।

## 5. Real-world engineering scenario — VPN দিয়ে ছড়িয়ে পড়া

**পরিস্থিতি:** একটি startup-এ সব engineer একটি WireGuard VPN ব্যবহার করে, AllowedIPs = পুরো VPC (`10.0.0.0/16`)। একজন contractor-এর laptop malware-আক্রান্ত হয়। Attacker VPN দিয়ে VPC-র internal service scan করে, একটি পুরোনো admin panel (কোনো authentication নেই, "শুধু internal") পায়, সেখান থেকে database credential।

**কী ভুল ছিল:**

1. **Flat access:** contractor-এর শুধু একটি staging service দরকার ছিল, কিন্তু পুরো VPC পেয়েছিল।
2. **"Internal = নিরাপদ"** ধারণা: admin panel-এ authentication নেই।
3. **Shared/দীর্ঘস্থায়ী credential:** contractor চলে যাওয়ার পরেও key সক্রিয়।
4. **Log নেই:** কে VPN দিয়ে কোথায় গেছে তা জানা যায়নি।

**উন্নতি:**

- প্রতিটি peer-এর **AllowedIPs ও server-side firewall** শুধু দরকারি subnet/port-এ (least privilege, L02-10)।
- Internal application-এও authentication (SSO) — zero trust।
- Admin/DB access → **identity-aware proxy বা Session Manager**, সময়-সীমিত, audit log সহ।
- Offboarding checklist-এ VPN peer মুছে ফেলা; key rotation।

**শিক্ষা:** VPN = connectivity, security model নয়। "কে, কী, কখন" — প্রতিটি resource-এ যাচাই করুন।

## 6. Diagram

```text
SSH local forward (-L 15432:db.internal:5432)

 laptop                                bastion (public subnet)          db.internal (private subnet)
 psql → 127.0.0.1:15432 ═══ SSH (TCP 22, encrypted) ═══► sshd ──── plain TCP ───► :5432
        └── ssh client listens                            └── opens connection to db

WireGuard remote-access VPN

 laptop                                       VPN server (UDP 51820)               VPC
 app → route 10.0.0.0/16 via wg0 ─► wg0 ══ UDP, encrypted ══► wg0 ─► routing/NAT ─► 10.0.5.20
        (AllowedIPs = 10.0.0.0/16)                             (peer AllowedIPs = 10.8.0.2/32)

Zero-trust access

 laptop ─ HTTPS ─► identity-aware proxy ──(SSO + MFA + device check + policy)──► only app X
                         └── প্রতিটি request log; network-এ আর কিছু দেখা যায় না
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Bastion / jump host | Private network-এ প্রবেশের একমাত্র নিয়ন্ত্রিত দরজা |
| Port forwarding | এক port-এর traffic অন্যত্র পাঠানো |
| SOCKS proxy | যেকোনো গন্তব্যের জন্য সাধারণ proxy protocol (`ssh -D`) |
| ProxyJump | Bastion দিয়ে পরের host-এ SSH (`-J`) |
| VPN | Encrypted virtual network link |
| Site-to-site / remote access | দুটি network যুক্ত / একজন user যুক্ত |
| Split tunnel / full tunnel | শুধু নির্দিষ্ট route VPN দিয়ে / সব traffic VPN দিয়ে |
| Cryptokey routing | WireGuard-এ public key ↔ AllowedIPs: কোন address কোন peer-এর |
| PersistentKeepalive | NAT mapping জীবিত রাখতে নিয়মিত ছোট packet |
| Zero trust | Network location নয়, identity ও context দিয়ে প্রতিটি access |
| Identity-aware proxy | SSO-র পরে নির্দিষ্ট application-এ access দেয় |
| Least privilege | দরকারের বেশি কিছুতে access নয় |
| Just-in-time access | সময়-সীমিত, অনুরোধ-ভিত্তিক access |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 SSH forwarding

SSH একটি encrypted TCP connection-এর ভেতরে একাধিক **channel** চালায়। `-L` দিলে ssh client local port-এ listen করে; প্রতিটি নতুন connection-এর জন্য একটি `direct-tcpip` channel খোলে; sshd অপর প্রান্তে আসল TCP connection খোলে ও byte copy করে। এই lesson-এর `port_forward.py` ঠিক এই "accept → নতুন connection → দুই দিকে copy" অংশটি দেখায়, শুধু মাঝখানের encryption ছাড়া।

গুরুত্বপূর্ণ বিবরণ:

- Default-এ `-L` শুধু `127.0.0.1`-এ listen করে। `-L 0.0.0.0:15432:...` দিলে আপনার network-এর যে কেউ database-এ পৌঁছায় — করবেন না।
- sshd-এ `AllowTcpForwarding`, `PermitOpen`, `GatewayPorts` দিয়ে নিয়ন্ত্রণ (L01-13-এর hardening)।
- TCP-over-TCP: SSH tunnel দিয়ে অনেক data পাঠালে loss-এ দুই স্তরের retransmission — VPN (UDP-ভিত্তিক) এ সমস্যা নেই।

### 8.2 WireGuard

- প্রতিটি node-এর একটি **Curve25519 key pair**; peer-রা একে অপরের public key জানে। কোনো certificate/CA নেই — key বিতরণ আপনার দায়িত্ব।
- **Cryptokey routing:**
  - **পাঠানোর সময়:** destination IP কোন peer-এর AllowedIPs-এ পড়ে? সেই peer-এর key দিয়ে encrypt।
  - **গ্রহণের সময়:** decrypt করার পরে source IP কি ঐ peer-এর AllowedIPs-এ? না হলে drop। তাই **AllowedIPs একই সাথে routing table ও access control list**, এবং দুই peer-এর AllowedIPs overlap করতে পারে না (এই lesson-এর linter এটাই ধরে)।
- UDP-এর উপর (default port ৫১৮২০)। কোনো "connection" নেই — peer IP বদলালে (Wi-Fi → mobile) শেষ বৈধ packet-এর source-এ উত্তর যায় (roaming)।
- NAT-এর পেছনে থাকলে বাইরে থেকে কেউ প্রথমে packet পাঠাতে পারে না, আর NAT mapping কিছুক্ষণ পরে মুছে যায় (L02-04) — `PersistentKeepalive = 25`।
- Overhead ৬০ (IPv4) / ৮০ (IPv6) byte → default MTU ১৪২০ (L02-09)।
- `wg-quick` = config পড়ে interface, address, route ও (ঐচ্ছিক) DNS সেট করার helper।

### 8.3 Zero trust-এর উপাদান

1. **Strong identity:** SSO + MFA; service-এর জন্য workload identity (mTLS certificate, cloud IAM role)।
2. **Device posture:** OS আপডেট, disk encryption, managed device।
3. **Per-request policy:** কে, কোন resource, কোন context-এ।
4. **Least privilege, just-in-time:** স্থায়ী access-এর বদলে সময়-সীমিত।
5. **সব কিছুর audit log।**
6. **Micro-segmentation:** network-এর ভেতরেও firewall/NetworkPolicy।

VPN পুরোপুরি বাদ যায় না — site-to-site ও কিছু legacy কাজে থাকে — কিন্তু মানুষের access ক্রমশ identity-aware proxy-তে যায়।

## 9. Practical demonstration

### 9.1 Port forwarder — tunnel-এর মূল কৌশল

File: [`code/L02-11/port_forward.py`](code/L02-11/port_forward.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-11
python3 port_forward.py demo
```

**আসল output (port প্রতিবার ভিন্ন):**

```text
echo server on 127.0.0.1:50404; forwarder 127.0.0.1:50405 -> 127.0.0.1:50404
sent     24 bytes via forwarder, got     24 back: b'HELLO THROUGH THE TUNNEL'
sent 100000 bytes via forwarder, got 100000 back: b'XXXXXXXXXXXXXXXXXXXXXXXX'
stats: {'connections': 2, 'failed': 0, 'bytes_up': 100024, 'bytes_down': 100024}
```

Client জানে না যে মাঝে forwarder আছে — সে শুধু `127.0.0.1:50405`-এ কথা বলে। `ssh -L`-এ এই forwarder-এর দুই অংশের মাঝে SSH-এর encrypted channel বসে।

### 9.2 WireGuard config lint

File: [`code/L02-11/wg_lint.py`](code/L02-11/wg_lint.py), [`sample-wg0.conf`](code/L02-11/sample-wg0.conf) — **synthetic key** (আসল নয়), ইচ্ছাকৃত ভুল সহ।

```bash
python3 wg_lint.py sample-wg0.conf; echo "exit=$?"
```

**আসল output:**

```text
INFO  PrivateKey is inline: keep the file mode 600 and never commit it (or load it from a file with PostUp = wg set %i private-key <path>)
WARN  MTU 1500 > 1420: may black-hole over IPv6 underlays or PPPoE (see L02-09)
INFO  line 17: Endpoint set but no PersistentKeepalive — behind NAT, inbound traffic stops after the NAT mapping expires (25 is common)
ERROR line 23: AllowedIPs 10.20.5.0/24 overlaps 10.20.0.0/16 of peer at line 17 — WireGuard routes each address to exactly one peer
3 peer(s), 2 error/warning(s)
exit=1
```

- **Overlap:** karim-এর laptop-কে `10.20.5.0/24` দেওয়া মানে office router-এর পেছনের ঐ subnet-এর traffic এখন কোথায় যাবে তা অস্পষ্ট — WireGuard একটি address একটি peer-কেই দেয়। আর karim সেই address থেকে packet পাঠাতে পারবে (spoofing-এর পথ)।
- **MTU ১৫০০:** VPN-এ L02-09-এর black hole-এর রেসিপি।
- Linter **কখনো private key ছাপায় না** — secret-যুক্ত file নিয়ে কাজ করা tool-এর মৌলিক নিয়ম।

### 9.3 SSH tunnel (🔗 দুটি Ubuntu VM: `bastion` ও `app`)

`app` VM-এ একটি service যা শুধু localhost-এ শোনে:

```bash
# app VM-এ
python3 -m http.server 8000 --bind 127.0.0.1
```

Laptop/তৃতীয় VM থেকে:

```bash
ssh -N -L 18000:127.0.0.1:8000 user@app        # app-এর localhost:8000 → আমার :18000
curl -s http://127.0.0.1:18000/ | head -3

ssh -J user@bastion user@app                   # bastion পার হয়ে app-এ
ssh -N -D 1080 user@bastion                    # SOCKS proxy
curl --socks5-hostname 127.0.0.1:1080 http://app:8000/   # (app-এ 0.0.0.0-এ bind থাকলে)
```

`~/.ssh/config`-এ স্থায়ী করুন:

```text
Host app
    HostName 10.0.5.20
    User ubuntu
    ProxyJump bastion
    LocalForward 18000 127.0.0.1:8000
```

### 9.4 WireGuard (🔗 দুটি Ubuntu VM: `vpn-a` ১৯২.১৬৮.৫৬.১০, `vpn-b` ১৯২.১৬৮.৫৬.১১ — নিজের lab address বসান)

```bash
sudo apt install wireguard                     # Ubuntu
umask 077
wg genkey | tee ~/wg-private.key | wg pubkey > ~/wg-public.key   # private key 600, কখনো Git-এ নয়
```

`vpn-a`-তে `/etc/wireguard/wg0.conf` (mode ৬০০):

```text
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <vpn-a-এর private key>

[Peer]
PublicKey = <vpn-b-এর public key>
AllowedIPs = 10.8.0.2/32
```

`vpn-b`-তে বিপরীত (`Address = 10.8.0.2/24`, peer-এ `Endpoint = 192.168.56.10:51820`, `AllowedIPs = 10.8.0.1/32`, `PersistentKeepalive = 25`)। তারপর:

```bash
sudo python3 wg_lint.py /etc/wireguard/wg0.conf  # আগে lint
sudo ufw allow 51820/udp                          # vpn-a-তে (L02-10)
sudo wg-quick up wg0
sudo wg show                                      # latest handshake, transfer
ping -c 3 10.8.0.1                                # vpn-b থেকে
ip route get 10.8.0.1                             # dev wg0
sudo tcpdump -ni any udp port 51820               # বাইরে শুধু encrypted UDP (L02-15)
sudo wg-quick down wg0                            # lab শেষে
```

> **Fedora-তে:** `sudo dnf install wireguard-tools`; firewall: `sudo firewall-cmd --add-port=51820/udp` (তারপর permanent)। Fedora-তে NetworkManager-ও WireGuard profile import করতে পারে: `nmcli connection import type wireguard file /etc/wireguard/wg0.conf`।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l02_11.py`](code/L02-11/test_l02_11.py)-এর ৭টি test: forwarder দিয়ে ১৫০ KB ও byte গণনা, target বন্ধ থাকলে client-এর connection বন্ধ ও `failed` গণনা, HOST:PORT parse, sample-এর তিনটি finding ও **output-এ private key নেই**, key format যাচাই, পরিষ্কার client config-এ শুধু INFO (full tunnel), parse error।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `Forwarder._handle` | প্রতিটি client-এর জন্য target-এ নতুন connection | `ssh -L`-এর প্রতি-connection channel |
| দুটি `_pipe` (একটি thread-এ) | দুই দিকে একসাথে copy | TCP full-duplex; একদিকে অপেক্ষা করলে deadlock |
| `shutdown(SHUT_WR)` | একদিক শেষ হলে অপর দিকে EOF | Half-close (L02-05) — request শেষ হলেও উত্তর আসতে পারে |
| non-loopback warning | `0.0.0.0`-এ listen করলে সতর্কতা | Tunnel-কে network-এ উন্মুক্ত করা প্রচলিত ভুল |
| `wg_lint.parse` নিজে | একাধিক `[Peer]` | `configparser` duplicate section মানে না |
| `valid_key` | base64 → ঠিক ৩২ byte | Copy-paste-এ কাটা key ধরা |
| overlap check `n.overlaps(other)` | Peer-দের AllowedIPs | Cryptokey routing-এর মূল নিয়ম |
| কখনো key print নয় | — | Secret log/terminal history-তে যেন না যায় |

**Python কেন এখানে, কোথায় নয়:** config lint ও policy check CI-তে Python-এর ভালো কাজ। আসল tunnel/VPN-এ OpenSSH ও kernel WireGuard — নিজের লেখা forwarder production-এ নয় (encryption, authentication, performance কিছুই নেই)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `port_forward.py demo` | পাঠানো ও ফেরত byte সমান |
| `ssh -L` + `curl 127.0.0.1:18000` | app-এর localhost service-এর উত্তর |
| `wg show` | `latest handshake: N seconds ago`, transfer বাড়ছে |
| `tcpdump udp port 51820` | শুধু UDP, payload পড়া যায় না |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `bind: Address already in use` (ssh -L) | Local port ব্যস্ত | `ss -ltnp \| grep 15432` | অন্য port |
| `channel 2: open failed: administratively prohibited` | sshd-এ forwarding বন্ধ | sshd_config `AllowTcpForwarding` | নীতি অনুযায়ী `PermitOpen` দিয়ে সীমিত অনুমতি |
| `channel ... connect failed: Connection refused` | Bastion থেকে target পৌঁছায় না | Bastion-এ `nc -zv db.internal 5432` | Security group/firewall |
| `wg show`-এ handshake নেই | UDP ৫১৮২০ বন্ধ, ভুল endpoint, ভুল key | `tcpdump udp port 51820` দুই প্রান্তে | Firewall, key জোড়া পরীক্ষা |
| Handshake আছে, ping নেই | AllowedIPs ভুল বা route নেই | `ip route get`, `wg show` allowed ips | AllowedIPs, server-এ `ip_forward` |
| কিছুক্ষণ পরে বন্ধ হয়ে যায় | NAT mapping মুছে গেছে | Idle-এর পরে প্রথম packet-এ সমস্যা | `PersistentKeepalive = 25` |
| ছোট চলে, বড় ঝোলে | MTU | L02-09 | MTU ১৪২০ বা কম |
| VPN-এর পরে সব site বন্ধ | Full tunnel কিন্তু server-এ NAT নেই | `AllowedIPs = 0.0.0.0/0` | Server-এ masquerade বা split tunnel |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Private key `600`, প্রতি device আলাদা key (shared নয়) — চুরি হলে শুধু একটি revoke; offboarding-এ peer মুছুন; least-privilege AllowedIPs + server-side firewall; `ssh -R` ও `GatewayPorts` নিয়ন্ত্রণ; bastion-এ শুধু forwarding (shell নয়) ও audit; tunnel/VPN-কে কখনো application authentication-এর বিকল্প ভাববেন না।
- **Performance:** WireGuard kernel-এ, খুব দ্রুত; SSH tunnel TCP-over-TCP — বড় transfer-এ ধীর; MTU সঠিক না হলে throughput ভাঙে; full tunnel-এ সব traffic VPN server দিয়ে — bottleneck ও latency।
- **Cost:** Cloud managed VPN (site-to-site) ঘণ্টা ও data অনুযায়ী বিল; NAT gateway ও data transfer; bastion instance-এর খরচ বনাম Session Manager-এর মতো managed বিকল্প (Module 08)। ⚠️ Cloud-এ VPN gateway তৈরির আগে pricing দেখুন।

## 14. Hands-on exercise

1. `port_forward.py`-কে L02-07-এর `http_raw.py demo`-র server-এর সামনে বসান — HTTP keep-alive কি forwarder দিয়ে কাজ করে? `stats`-এ কয়টি connection?
2. `wg_lint.py`-তে নতুন check: একই `Endpoint` দুই peer-এ (সম্ভাব্য copy-paste ভুল); test লিখুন।
3. দুটি VM-এ Section 9.3 — `ssh -L`, `-J`, `-D` তিনটিই; প্রতিটিতে `ss -ltnp` দিয়ে দেখুন কোন process কোন port-এ শুনছে।
4. Section 9.4-এর WireGuard সেটআপ; তারপর ইচ্ছাকৃতভাবে vpn-b-এর AllowedIPs ভুল (`10.8.0.9/32`) দিয়ে কী হয় দেখুন — handshake হয়? ping?
5. একটি ছোট লেখা: আপনার (বা কাল্পনিক) team-এর জন্য "DB access policy" — কে, কীভাবে (tunnel/VPN/proxy), কতক্ষণ, কোন log।

## 15. Mini-project — Peer inventory ও offboarding

একটি script যা একটি WireGuard server config ও একটি `peers.csv` (নাম, মালিক, তৈরির তারিখ, মেয়াদ) মিলিয়ে: (১) config-এ আছে কিন্তু inventory-তে নেই এমন peer, (২) মেয়াদোত্তীর্ণ peer, (৩) `wg show dump`-এর (Ubuntu-তে) latest handshake ৩০ দিনের বেশি পুরোনো — রিপোর্ট দেয় ও মুছে ফেলার জন্য প্রস্তাবিত `wg set wg0 peer <key> remove` command **ছাপায়, চালায় না**। Module 19-এর access review-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. `ssh -L`, `-R`, `-D`-এর পার্থক্য উদাহরণ সহ।
2. Bastion host কী? এর বিকল্প কী?
3. WireGuard-এর AllowedIPs দুটি কী কাজ করে?
4. VPN থাকলেও internal service-এ authentication কেন দরকার?
5. Zero trust বলতে কী বোঝায়? বাস্তবে কীভাবে implement করবেন?
6. NAT-এর পেছনের WireGuard peer কিছুক্ষণ পরে unreachable — কেন?
7. Private database-এ developer-দের access কীভাবে design করবেন?

## 17. Self-assessment প্রশ্ন

1. ভল্ট analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর চারটি ভুল ও প্রতিটির প্রতিকার।
3. `port_forward.py`-তে দুই দিকের copy কেন একসাথে চলতে হয়?
4. Sample config-এ overlap কেন শুধু routing নয়, নিরাপত্তারও সমস্যা?
5. WireGuard-এর MTU কেন ১৪২০?

## 18. সংক্ষিপ্ত সারাংশ

- SSH tunnel: নির্দিষ্ট port-এর জন্য encrypted পাইপ (`-L`, `-R`, `-D`, `-J`); default-এ loopback-এ রাখুন।
- VPN: পুরো network-এ encrypted route; WireGuard — key pair, cryptokey routing (AllowedIPs = route + ACL), UDP, keepalive, MTU ১৪২০।
- VPN = connectivity, security model নয়; least privilege, প্রতি device key, offboarding।
- Zero trust: identity + device + per-request policy + audit, network location নয়।
- Secret-যুক্ত config-এর tool কখনো secret ছাপাবে না।

## 19. Completion checklist

- [ ] `port_forward.py demo` চালিয়ে `ssh -L`-এর সাথে সম্পর্ক ব্যাখ্যা করতে পারি
- [ ] দুটি VM-এ `ssh -L`, `-J`, `-D` করেছি
- [ ] WireGuard tunnel তৈরি করে `wg show` ও `tcpdump` দিয়ে যাচাই করেছি, তারপর বন্ধ করেছি
- [ ] `wg_lint.py` দিয়ে নিজের config lint করেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `ssh(1)` (OpenSSH): https://man.openbsd.org/ssh
- `ssh_config(5)`: https://man.openbsd.org/ssh_config
- `sshd_config(5)`: https://man.openbsd.org/sshd_config
- WireGuard — Quick start: https://www.wireguard.com/quickstart/
- WireGuard — Protocol & cryptography: https://www.wireguard.com/protocol/
- Ubuntu Server — WireGuard VPN: https://documentation.ubuntu.com/server/how-to/wireguard-vpn/
- NIST SP 800-207 — Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/final
- AWS Systems Manager Session Manager: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html

---

**পরের lesson:** L02-12 — Load balancing ও reverse proxy: L4 বনাম L7
