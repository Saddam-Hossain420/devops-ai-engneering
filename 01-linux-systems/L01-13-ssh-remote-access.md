# L01-13 — SSH, SSH key, agent forwarding ও নিরাপদ remote access

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-12 — Storage ও LVM](L01-12-storage-lvm.md); [L01-05 — sudo](L01-05-acl-sudo.md) |
| **Label** | 🔗 দুটি machine সুবিধাজনক (host + VM যথেষ্ট) · ⚠️ sshd পরিবর্তনে নিজেকে বাইরে আটকে ফেলার ঝুঁকি — Section 9.5-এর নিয়ম মানুন |
| **Tested** | `ssh_audit.py`: ৯টি test পাস; `sshd` ও `keys` audit নমুনায় চালানো (Python 3.14, Windows)। নমুনা public key **synthetic** (সঠিক wire format, random সংখ্যা — আসল key নয়, কোনো private key নেই)। `ssh-keygen`, `ssh-copy-id`, `sshd -T`, sshd reload **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- SSH কী করে: encrypted channel, **server-এর পরিচয় যাচাই** (host key), **user-এর পরিচয় যাচাই** (key বা password)।
- **Key pair** (public/private), `ssh-keygen`, passphrase, `ssh-agent`।
- `authorized_keys`, `known_hosts`, `~/.ssh/config` — কোনটি কোথায়, কী কাজ।
- "REMOTE HOST IDENTIFICATION HAS CHANGED" — কখন বিপদ, কখন স্বাভাবিক।
- **Agent forwarding-এর ঝুঁকি** ও নিরাপদ বিকল্প **ProxyJump**।
- Port forwarding (`-L`, `-R`) — ক্ষমতা ও ঝুঁকি।
- **sshd hardening** নিরাপদে (lockout ছাড়া), drop-in ও "প্রথম মান জেতে" নিয়ম।
- Python দিয়ে sshd config ও authorized_keys audit (RSA key-এর আসল bit সংখ্যা সহ)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Server data center বা cloud-এ — আপনি সামনে নেই। প্রয়োজন: দূর থেকে command চালানো, file পাঠানো, এবং সেটা এমনভাবে যাতে মাঝপথে কেউ (public Wi-Fi, ISP, আক্রমণকারী) পড়তে বা বদলাতে না পারে এবং ভুল server-এ password না দিয়ে ফেলেন।

পুরোনো `telnet`/`rsh` সব কিছু — password সহ — plain text-এ পাঠাত (L01-02-এর scenario-তে telnetd কেন বিপজ্জনক ছিল)। **SSH** encryption, integrity ও দুই দিকের authentication দেয়।

কিন্তু SSH নিজেই সবচেয়ে বেশি আক্রান্ত service: internet-এ খোলা প্রতিটি port 22-এ প্রতিদিন হাজার হাজার password-guessing চেষ্টা হয়। সঠিক configuration (key-only, root login বন্ধ) ছাড়া এটি সবচেয়ে বড় প্রবেশপথ।

## 3. সহজ ভাষায় পরিচয়

**Key pair:**

- **Private key** — আপনার কাছে গোপন (`~/.ssh/id_ed25519`)। কখনো কাউকে দেবেন না, কোথাও copy বা commit করবেন না।
- **Public key** — নির্ভয়ে শেয়ার করা যায় (`~/.ssh/id_ed25519.pub`)। Server-এর `~/.ssh/authorized_keys`-এ রাখলে, যার কাছে মিলে যাওয়া private key আছে সে login করতে পারে।

Login-এর সময় server একটি চ্যালেঞ্জ দেয়; আপনার client private key দিয়ে **sign** করে; server public key দিয়ে যাচাই করে। Private key কখনো network-এ যায় না।

**Host key:** Server-এরও একটি key pair থাকে। প্রথম connection-এ client server-এর public host key-এর fingerprint দেখায় ও `~/.ssh/known_hosts`-এ রাখে। পরে প্রতিবার মেলায় — না মিললে সতর্ক করে (হয়তো আক্রমণকারী মাঝে বসে আছে: **man-in-the-middle**)।

**Key type:** নতুন key-এর জন্য **ed25519** সুপারিশকৃত (ছোট, দ্রুত, নিরাপদ)। RSA চলে কিন্তু কমপক্ষে ৩০৭২ bit সুপারিশ; ১০২৪-bit RSA দুর্বল; DSA আধুনিক OpenSSH-এ বাতিল।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### সিলমোহর ও স্বাক্ষর যাচাই

- **Private key** = আপনার নিজের সিলমোহর, শুধু আপনার কাছে।
- **Public key** = সেই সিলের ছাপের নমুনা, যা আপনি অফিসে (server) জমা দিয়েছেন (`authorized_keys`)।
- Login = অফিস একটি কাগজ দেয়, আপনি সিল মারেন, অফিস নমুনার সাথে মেলায়। সিল নিজে কখনো অফিসে যায় না।
- **Host key / known_hosts** = অফিসের নিজের সিলের নমুনা আপনার খাতায়; অফিস বদলে গেছে মনে হলে (নমুনা মেলে না) সন্দেহ করবেন — কেউ নকল অফিস খুলেছে কিনা।
- **Agent forwarding** = সিলমোহর এক বন্ধুর (মধ্যবর্তী server) কাছে ধার দেওয়া যাতে তিনি আপনার হয়ে অন্য অফিসে সিল মারতে পারেন — বন্ধু অসৎ হলে আপনার অজান্তে যেকোনো জায়গায় সিল মারতে পারেন।

### Analogy কোথায় মেলে না

- কাগজের সিল নকল করা সম্ভব; গাণিতিক signature (ed25519) private key ছাড়া নকল করা কার্যত অসম্ভব — **যদি private key গোপন থাকে**। দুর্বলতা প্রায় সবসময় মানুষের অভ্যাসে (key copy, passphrase ছাড়া, laptop চুরি), গণিতে নয়।
- Agent forwarding-এ বন্ধু আসলে সিলমোহর **নেন না** — তিনি শুধু আপনার connection চলাকালীন আপনার agent-কে অনুরোধ করতে পারেন। তাই ঝুঁকি সেই সময়সীমায় সীমিত — কিন্তু সেই সময়ে তিনি আপনার সব server-এ যেতে পারেন।

## 5. Real-world engineering scenario — bastion-এ agent forwarding

**পরিস্থিতি:** কোম্পানির private server-এ যেতে হয় একটি **bastion** (jump host) দিয়ে। Engineer-রা অভ্যাসবশত `ssh -A bastion` (agent forwarding) করে, তারপর bastion থেকে `ssh app-server`।

**ঘটনা:** Bastion-এ একটি পুরোনো vulnerability দিয়ে আক্রমণকারী root পেল। Root হিসেবে সে bastion-এ যুক্ত প্রতিটি engineer-এর agent socket (`/tmp/ssh-*/agent.*`) ব্যবহার করে তাদের নামে **সব production server-এ** login করল — কারো private key চুরি না করেই।

**কেন:** Agent forwarding মানে মধ্যবর্তী machine-এর root আপনার agent-কে signing-এর অনুরোধ পাঠাতে পারে, যতক্ষণ আপনি যুক্ত আছেন।

**নিরাপদ বিকল্প — ProxyJump:**

```bash
ssh -J bastion app-server
```

এখানে bastion শুধু encrypted TCP stream এগিয়ে দেয়; app-server-এর সাথে authentication **আপনার laptop থেকে সরাসরি** (end-to-end) হয়। Bastion কিছু sign করতে পারে না।

**শিক্ষা:** `ForwardAgent yes` প্রায় কখনো দরকার নেই; jump host-এর জন্য `ProxyJump`। Server-এ `AllowAgentForwarding no`।

## 6. Diagram

### SSH connection-এর ধাপ

```text
 client                                              server (sshd)
   │ ── TCP connect :22 ─────────────────────────────────►│
   │ ◄── version + algorithm negotiation ────────────────►│
   │ ◄── key exchange (shared secret, encryption শুরু) ──►│
   │ ◄── server host key + signature ─────────────────────│
   │  known_hosts-এর সাথে মিলাও (না মিললে থামো!)          │
   │ ── user auth: "sami, এই public key দিয়ে" ───────────►│ authorized_keys-এ আছে?
   │ ◄── challenge ───────────────────────────────────────│
   │ ── private key দিয়ে signature ───────────────────────►│ public key দিয়ে যাচাই
   │ ◄── অনুমোদিত, shell/session ─────────────────────────│
```

### Agent forwarding বনাম ProxyJump

```text
 Agent forwarding (ssh -A):
   laptop[agent] ══ssh══► bastion ══ssh══► app
                     ▲ bastion-এর root agent-কে sign করতে বলতে পারে ⚠️

 ProxyJump (ssh -J):
   laptop ══════════════ssh (end-to-end encrypted, auth laptop থেকে) ══════════► app
            └──► bastion শুধু TCP এগিয়ে দেয় ──┘
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Key pair | Private (গোপন) ও public (শেয়ারযোগ্য) key-এর জোড়া |
| Passphrase | Private key file encrypt করার password |
| `ssh-agent` | Unlock করা private key memory-তে রাখে, বারবার passphrase লাগে না |
| `authorized_keys` | Server-এ কোন public key দিয়ে কোন user-এ login করা যাবে |
| `known_hosts` | Client-এ বিশ্বস্ত server host key-এর তালিকা |
| Fingerprint | Key-এর ছোট hash, মানুষের যাচাইয়ের জন্য |
| Host key | Server-এর পরিচয়ের key |
| Man-in-the-middle | মাঝপথে বসে দুই পক্ষকে ধোঁকা দেওয়া |
| Bastion / jump host | Private network-এ ঢোকার নিয়ন্ত্রিত দরজা |
| Agent forwarding | দূরের server থেকে local agent ব্যবহার — ঝুঁকিপূর্ণ |
| ProxyJump (`-J`) | মধ্যবর্তী host দিয়ে end-to-end SSH |
| Local forward (`-L`) | Local port → দূরের network-এর একটি address |
| Remote forward (`-R`) | দূরের port → local network-এর address |
| `sshd -T` | কার্যকর (effective) sshd configuration দেখায় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 File permission — SSH কঠোর

SSH নিরাপত্তার জন্য permission যাচাই করে (`StrictModes yes`, default):

| Path | Permission | না হলে |
|---|---|---|
| `~/.ssh/` | `700` | server key login প্রত্যাখ্যান করতে পারে |
| `~/.ssh/authorized_keys` | `600` | ঐ |
| `~/.ssh/id_ed25519` (private) | `600` | client: "UNPROTECTED PRIVATE KEY FILE!" এবং ব্যবহার করে না |
| Home directory | অন্যরা লিখতে পারবে না | server key login প্রত্যাখ্যান |

### 8.2 sshd configuration-এর "প্রথম মান জেতে" নিয়ম

`sshd_config`-এ একই keyword একাধিকবার থাকলে বেশিরভাগ keyword-এ **প্রথমটি** কার্যকর (বেশিরভাগ config file-এর উল্টো!)। Ubuntu 24.04-এর `/etc/ssh/sshd_config`-এর শুরুতে:

```text
Include /etc/ssh/sshd_config.d/*.conf
```

তাই `/etc/ssh/sshd_config.d/10-hardening.conf`-এর মান মূল file-এর পরের মানকে override করে — এটাই সঠিক জায়গা নিজের পরিবর্তনের জন্য (package update-এ হারায় না)। সন্দেহ হলে কার্যকর মান দেখুন:

```bash
sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin'
```

`Match` block (যেমন `Match User backup`) শর্তসাপেক্ষে কিছু setting বদলায় — এই lesson-এর audit tool সরলতার জন্য শুধু global অংশ দেখে; `sshd -T -C user=backup,host=x,addr=y` দিয়ে নির্দিষ্ট শর্তের কার্যকর মান দেখা যায়।

### 8.3 authorized_keys option

একটি key-এর ক্ষমতা সীমিত করা যায় (automation-এর জন্য আদর্শ):

```text
from="10.0.0.0/8",command="/usr/local/bin/backup-receive",no-pty,no-port-forwarding ssh-ed25519 AAAA... backup@nas
```

| Option | অর্থ |
|---|---|
| `from=` | শুধু এই address থেকে |
| `command=` | যা-ই চাওয়া হোক, শুধু এই command চলবে |
| `no-pty`, `no-port-forwarding`, `no-agent-forwarding` | অতিরিক্ত ক্ষমতা বন্ধ |
| `restrict` | সব বন্ধ করে, তারপর দরকারিগুলো চালু (আধুনিক OpenSSH) |

### 8.4 Ubuntu 24.04-এ socket activation

Ubuntu 22.10 থেকে sshd **socket-activated** (`ssh.socket`) — connection এলে তবে sshd চালু হয়। ফলে `Port`/`ListenAddress` বদলালে শুধু `systemctl restart ssh` যথেষ্ট নাও হতে পারে; `systemctl daemon-reload` ও `systemctl restart ssh.socket` লাগতে পারে। পরিবর্তনের পরে `ss -tlnp | grep ssh` দিয়ে কোন port শুনছে যাচাই করুন। (বিস্তারিত Ubuntu-র documentation-এ।)

> **Fedora-তে:** service নাম `sshd` (socket activation default নয়); port বদলালে SELinux-কে জানাতে হয়: `sudo semanage port -a -t ssh_port_t -p tcp 2222` (L01-17), এবং firewalld-এ port খুলতে হয়।

## 9. Practical demonstration (host + Ubuntu VM)

### 9.1 Key তৈরি (client-এ)

```bash
ssh-keygen -t ed25519 -C "sami@laptop-2026" -f ~/.ssh/id_ed25519
```

| Option | অর্থ |
|---|---|
| `-t ed25519` | Key type |
| `-C` | Comment — কার key, কোন machine (access review-এ দরকার) |
| `-f` | File path |

Passphrase দিন (খালি নয়)। তারপর:

```bash
ls -l ~/.ssh/                       # id_ed25519 (600), id_ed25519.pub (644)
cat ~/.ssh/id_ed25519.pub           # এটি শেয়ারযোগ্য
ssh-keygen -lf ~/.ssh/id_ed25519.pub  # fingerprint
```

### 9.2 Key server-এ দেওয়া ও login

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub sami@VM_IP     # password দিয়ে একবার; key authorized_keys-এ যোগ হয়
ssh sami@VM_IP                                       # প্রথমবার host key fingerprint দেখাবে
```

**প্রথমবারের fingerprint যাচাই:** VM-এর console থেকে (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) মিলিয়ে তবে "yes" লিখুন। অন্ধভাবে "yes" — man-in-the-middle-এর দরজা খোলা।

**ssh-agent:**

```bash
eval "$(ssh-agent -s)"          # agent চালু (অনেক desktop-এ আগে থেকেই চলে)
ssh-add ~/.ssh/id_ed25519       # passphrase একবার
ssh-add -l                      # loaded key
```

### 9.3 `~/.ssh/config` — সুবিধা ও নিরাপদ default

```text
Host devlab
    HostName 192.168.56.10
    User sami
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

Host app-*
    ProxyJump bastion
    ForwardAgent no

Host *
    ForwardAgent no
    HashKnownHosts yes
```

এখন `ssh devlab` যথেষ্ট। `IdentitiesOnly yes` = শুধু নির্দিষ্ট key চেষ্টা করো (agent-এর সব key নয় — অনেক key থাকলে "Too many authentication failures" এড়ায়)।

### 9.4 Port forwarding (VM-এ L01-10-এর service থাকলে)

```bash
ssh -L 9090:127.0.0.1:8080 devlab
# অন্য terminal-এ, laptop থেকে:
curl -s http://127.0.0.1:9090/health
```

VM-এর `127.0.0.1:8080` (বাইরে খোলা নয়) laptop-এর `9090`-এ এলো — encrypted tunnel দিয়ে। ⚠️ একইভাবে কেউ আপনার server থেকে internal service বাইরে আনতে পারে — তাই অপ্রয়োজনে `AllowTcpForwarding no`।

### 9.5 sshd hardening — নিজেকে আটকে না ফেলে (⚠️)

**সোনালি নিয়ম:** sshd পরিবর্তনের সময় **একটি চলমান SSH session খোলা রাখুন** এবং **নতুন terminal থেকে** login পরীক্ষা করুন। চলমান session-এ কাজ চলতে থাকে, তাই ভুল হলে ঠিক করতে পারবেন। VM হলে snapshot ও console access হাতের কাছে রাখুন।

```bash
# VM-এ, প্রথম session-এ:
sudo groupadd -f ssh-users && sudo usermod -aG ssh-users "$USER"
sudo install -m 0644 ~/devops-ai-engineering/01-linux-systems/code/L01-13/sample-sshd-hardened.conf \
    /etc/ssh/sshd_config.d/10-hardening.conf
sudo sshd -t && echo "config syntax OK"                # syntax যাচাই — ভুল থাকলে reload করবেন না
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|allowgroups'
sudo systemctl reload ssh                               # Fedora-তে: sudo systemctl reload sshd

# laptop-এর নতুন terminal থেকে:
ssh devlab                                              # key দিয়ে কাজ করা উচিত
ssh -o PubkeyAuthentication=no devlab                   # password চেষ্টা — প্রত্যাখ্যান হওয়া উচিত
```

File: [`sample-sshd-hardened.conf`](code/L01-13/sample-sshd-hardened.conf)। `AllowGroups ssh-users` — আপনি group-এ না থাকলে **lockout**; তাই আগে নিজেকে যোগ করা (এবং L01-04: group পরিবর্তন নতুন login-এ কার্যকর)।

### 9.6 Audit — Python

File: [`code/L01-13/ssh_audit.py`](code/L01-13/ssh_audit.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-13
sudo sshd -T > /tmp/sshd-effective.txt
python3 ssh_audit.py sshd /tmp/sshd-effective.txt
python3 ssh_audit.py keys ~/.ssh/authorized_keys
rm /tmp/sshd-effective.txt
```

**নমুনা data দিয়ে আসল output:**

```bash
python3 ssh_audit.py sshd sample-sshd-effective.txt; echo "exit=$?"
```

```text
HIGH     PermitRootLogin yes — root password দিয়ে সরাসরি login
HIGH     PasswordAuthentication yes — brute-force ঝুঁকি; key-only করুন
LOW      X11Forwarding yes — server-এ সাধারণত দরকার নেই
LOW      AllowAgentForwarding yes — compromised server আপনার agent ব্যবহার করতে পারে
LOW      MaxAuthTries 6 — ৩-৪ যথেষ্ট
INFO     AllowUsers/AllowGroups নেই — কে login করতে পারে সীমিত করুন
summary: CRITICAL=0  HIGH=2  MEDIUM=0  LOW=3  INFO=1
exit=1
```

Hardened file (`sample-sshd-hardened.conf`): `summary: ... HIGH=0 ...`, `exit=0`।

```bash
python3 ssh_audit.py keys sample-authorized_keys; echo "exit=$?"
```

```text
HIGH     line 5 (legacy@2012): RSA 1024 bit — দুর্বল
HIGH     line 6 (ancient@server): DSA key — আধুনিক OpenSSH-এ বাতিল; ed25519 দিয়ে বদলান
MEDIUM   line 9 (sami@laptop-copy): duplicate of line 2
LOW      line 4 (deploy@ci): RSA 2048 bit — নতুন key হলে ed25519 বা RSA ≥3072
LOW      line 8 (no comment): comment নেই — key কার তা চেনা যায় না (access review কঠিন)
INFO     line 7 (backup@nas): options = from="10.0.0.0/8",command="/usr/local/bin/backup-receive",no-pty,no-port-forwarding
summary: CRITICAL=0  HIGH=2  MEDIUM=1  LOW=2  INFO=1
exit=1
```

RSA-এর bit সংখ্যা tool নিজে key-এর base64 blob decode করে মেপেছে (৪০৯৬-bit key-এ কোনো finding নেই)। Native সমতুল্য: `ssh-keygen -lf ~/.ssh/authorized_keys` (প্রতিটি key-এর bit ও fingerprint)।

### 9.7 Test

```bash
python3 -m unittest -v
```

[`test_ssh_audit.py`](code/L01-13/test_ssh_audit.py)-এর ৯টি test: প্রথম মান জেতে ও Match উপেক্ষা, অনিরাপদ ও hardened নমুনা, empty password = CRITICAL, wire format থেকে RSA ২০৪৮ bit, ভাঙা blob, নমুনা authorized_keys-এর সব finding, ভাঙা লাইন, ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `cfg.setdefault(key, value)` | প্রথম মান রাখে | sshd-এর first-value-wins নিয়ম |
| `key.lower()` | case-insensitive | sshd keyword-এ case নেই; `sshd -T` lowercase দেয় |
| `break` on `match` | শর্তসাপেক্ষ অংশ বাদ | Global নীতির audit |
| `read_string()` | ৪-byte দৈর্ঘ্য + data | SSH key-এর wire format (RFC 4253) |
| `n.lstrip(b"\x00")` | mpint-এর sign byte বাদ | না হলে bit সংখ্যা ৮ বেশি আসত |
| `(len(n)-1)*8 + n[0].bit_length()` | সঠিক bit দৈর্ঘ্য | শুধু byte×8 করলে শীর্ষ byte-এর অব্যবহৃত bit গোনা হতো |
| `KEY_RE` with options prefix | Option-যুক্ত লাইন | `from=...` সহ key চেনা |
| Synthetic test key | Random মান, সঠিক format | কোনো আসল key repository-তে রাখা হয়নি |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `ls -l ~/.ssh/id_ed25519` | `-rw-------` |
| Hardening-এর পরে password login | `Permission denied (publickey)` |
| Key login | সফল |
| `ssh -J bastion app` | Bastion হয়ে সরাসরি app-এ |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `Permission denied (publickey)` | key authorized_keys-এ নেই, ভুল user, permission | `ssh -v` (debug); server-এ `journalctl -u ssh` | `ssh-copy-id`; `chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys` |
| `WARNING: UNPROTECTED PRIVATE KEY FILE!` | private key-এর permission বেশি খোলা | `ls -l` | `chmod 600` |
| `REMOTE HOST IDENTIFICATION HAS CHANGED!` | Server reinstall/নতুন IP — অথবা **আক্রমণ** | Server-এর console থেকে fingerprint | নিশ্চিত হলে তবেই `ssh-keygen -R host` |
| `Too many authentication failures` | Agent-এর অনেক key চেষ্টা | `ssh-add -l` | `IdentitiesOnly yes` + `IdentityFile` |
| Config বদলালাম, প্রভাব নেই | first-value-wins / reload হয়নি | `sshd -T` | Drop-in file-এ লিখুন; `sshd -t` তারপর reload |
| Port বদলালাম, পুরোনো port-এ শোনে | Ubuntu socket activation | `ss -tlnp` | `daemon-reload` + `restart ssh.socket` |
| Connection timeout | Firewall/security group | `nc -vz host 22` (L02-16) | Firewall rule (L02-10) |

`ssh -vvv` — client-এর বিস্তারিত debug; কোন key চেষ্টা হলো, কোথায় প্রত্যাখ্যাত — প্রথম diagnosis tool।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Key-only, `PermitRootLogin no`, `AllowGroups`; private key-এ passphrase; প্রতিটি device-এর আলাদা key (একটি চুরি হলে শুধু সেটি revoke)।
  - Agent forwarding নয় — ProxyJump।
  - Automation key-এ `from=`, `command=`, `restrict`।
  - Brute-force কমাতে fail2ban/rate limiting (L06-08) এবং সম্ভব হলে SSH internet-এ খোলাই না রাখা (VPN, bastion, বা cloud-এর session manager — Module 08)।
  - নিয়মিত authorized_keys review (প্রাক্তন কর্মী, পুরোনো key) — এই lesson-এর audit।
  - Private key কখনো Git-এ নয় — repository-র [.gitignore](../.gitignore)-এ `id_ed25519*` আছে।
- **Performance:** `ControlMaster`/`ControlPersist` দিয়ে একাধিক session একই connection share করে (Ansible-এ বড় গতি, Module 13)।
- **Cost:** Bastion server-এর খরচ; cloud-এর managed session service বিবেচনা।

## 14. Hands-on exercise

1. ed25519 key তৈরি, `ssh-copy-id`, `~/.ssh/config`-এ alias, এবং VM-এ hardening drop-in প্রয়োগ — lockout ছাড়া।
2. দ্বিতীয় VM থাকলে প্রথমটিকে bastion বানিয়ে `ProxyJump` দিয়ে দ্বিতীয়টিতে যান। `ssh -v`-এ কোথায় authentication হচ্ছে দেখুন।
3. একটি automation key তৈরি করে `command="/usr/bin/uptime",restrict` দিয়ে authorized_keys-এ যোগ করুন। সেই key দিয়ে `ssh devlab ls` চালালে কী হয়?
4. `ssh_audit.py`-তে নতুন নিয়ম: `PermitRootLogin`-এর মান `prohibit-password` থাকলেও `AllowGroups`-এ root-এর group নেই কিনা ইত্যাদি — অথবা সহজতর: `AllowTcpForwarding yes` হলে LOW। Test লিখুন।
5. `journalctl -u ssh --since today | grep -c "Failed password"` — internet-এ খোলা VM-এ কত চেষ্টা? (শুধু নিজের VM, cloud হলে Module 08-এর পরে।)

## 15. Mini-project — SSH access review

Project 1-এর `ssh` subcommand-এর পরিকল্পনা: একটি script যা (read-only, sudo দিয়ে প্রস্তুত input থেকে) প্রতিটি login-সক্ষম user-এর (L01-04-এর `perm_tool.py users`) authorized_keys audit করে, `sshd -T`-এর finding যোগ করে, এবং একটি Markdown report দেয়: কার কয়টি key, কোন key দুর্বল/duplicate/comment-হীন, sshd-এর ঝুঁকি। L01-05-এর access review-এর সাথে যুক্ত করুন।

## 16. Interview প্রশ্ন

1. SSH public key authentication কীভাবে কাজ করে? Private key কি network-এ যায়?
2. Host key কী এবং "HOST IDENTIFICATION HAS CHANGED" দেখলে কী করবেন?
3. Agent forwarding কেন ঝুঁকিপূর্ণ? বিকল্প কী?
4. sshd harden করতে প্রথম পাঁচটি পদক্ষেপ কী?
5. sshd configuration বদলানোর সময় lockout কীভাবে এড়াবেন?
6. sshd_config-এ একই keyword দুবার থাকলে কোনটি কার্যকর?
7. Automation-এর জন্য SSH key কীভাবে সীমিত করবেন?

## 17. Self-assessment প্রশ্ন

1. সিলমোহর analogy কোথায় মেলে না?
2. Section 5-এর আক্রমণে কোনো private key চুরি হয়নি — তবু কীভাবে সম্ভব হলো?
3. Ubuntu-তে drop-in file কেন মূল file-কে override করে?
4. RSA bit সংখ্যা হিসাবে `lstrip(b"\x00")` কেন দরকার?
5. Fedora-তে SSH port বদলাতে অতিরিক্ত কোন দুটি কাজ লাগে?
6. Port forwarding-এর একটি বৈধ ব্যবহার ও একটি ঝুঁকি।

## 18. সংক্ষিপ্ত সারাংশ

- SSH = encryption + server যাচাই (host key, known_hosts) + user যাচাই (key)।
- Private key গোপন (৬০০, passphrase); public key `authorized_keys`-এ; নতুন key **ed25519**।
- Agent forwarding নয় — **ProxyJump**।
- sshd hardening: key-only, root login বন্ধ, `AllowGroups`; drop-in-এ (first value wins); `sshd -t` → reload; চলমান session খোলা রেখে নতুন session-এ পরীক্ষা।
- নিয়মিত key ও configuration audit।

## 19. Completion checklist

- [ ] ed25519 key (passphrase সহ) তৈরি ও `ssh-copy-id`
- [ ] Host key fingerprint console থেকে মিলিয়েছি
- [ ] `~/.ssh/config`-এ alias ও নিরাপদ default
- [ ] Port forward দিয়ে VM-এর local service দেখেছি
- [ ] Hardening drop-in প্রয়োগ, lockout ছাড়া; password login প্রত্যাখ্যাত যাচাই
- [ ] `ssh_audit.py` নিজের `sshd -T` ও authorized_keys-এ চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৯টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- OpenSSH manual pages: https://www.openssh.com/manual.html
- `sshd_config(5)`: https://man.openbsd.org/sshd_config
- `ssh_config(5)` (ProxyJump, ForwardAgent): https://man.openbsd.org/ssh_config
- `sshd(8)` — AUTHORIZED_KEYS FILE FORMAT: https://man.openbsd.org/sshd
- `ssh-keygen(1)`: https://man.openbsd.org/ssh-keygen
- RFC 4253 — SSH Transport Layer (wire format): https://www.rfc-editor.org/rfc/rfc4253
- Ubuntu Server — OpenSSH: https://documentation.ubuntu.com/server/

---

**পরের lesson:** L01-14 — Log, debugging ও resource inspection (journalctl, strace, lsof)
