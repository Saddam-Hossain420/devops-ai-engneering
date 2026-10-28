# L01-18 — Software update, boot process ও system recovery

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-17 — AppArmor ও SELinux](L01-17-apparmor-selinux.md); [L01-02 — package management](L01-02-package-management.md); [L01-10 — systemd](L01-10-systemd-services.md) |
| **Label** | 🖥️ VM বাধ্যতামূলক (boot ও recovery experiment) · ⚠️ boot ভাঙার experiment — **আগে snapshot** |
| **Tested** | `boot_report.py`: ৭টি test পাস; নমুনা data-য় `boot` ও `reboot` চালানো (Python 3.14, Windows)। নমুনা `systemd-analyze` output হাতে তৈরি (আসল format অনুসরণে)। **Update, reboot, GRUB, emergency mode experiment Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- নিরাপদ **update কৌশল**: security update, `unattended-upgrades`, phased update, service restart (`needrestart`), kernel update ও **কখন reboot লাগে**।
- **Boot process**: firmware (UEFI) → bootloader (GRUB) → kernel + initramfs → systemd → target।
- Boot সময় বিশ্লেষণ (`systemd-analyze`) ও একটি প্রচলিত ৬০-সেকেন্ডের boot বিলম্ব।
- **Recovery**: পুরোনো kernel-এ boot, rescue/emergency target, ভাঙা `/etc/fstab`, ভুলে যাওয়া password, filesystem check।
- Python দিয়ে boot timing ও "reboot দরকার কিনা" যাচাই।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

দুটি পরস্পরবিরোধী চাপ:

- **নিরাপত্তা:** প্রকাশিত vulnerability-র fix দ্রুত install করতে হবে — না করলে আক্রমণ (L01-02-এর পুরোনো OpenSSL)।
- **স্থিতিশীলতা:** update কখনো কিছু ভাঙে; reboot মানে downtime।

আর যখন সত্যিই কিছু ভাঙে — server boot হয় না — তখন SSH নেই, স্বাভাবিক tool নেই। সেই মুহূর্তে boot process বোঝা ও recovery-র ধাপ জানা থাকলে মিনিটে ঠিক হয়; না জানলে ঘণ্টা বা নতুন করে install।

DevOps-এ এর গুরুত্ব আরো বেশি: অনেক server-এ update automation (Module 13), rolling reboot (Module 14), এবং "immutable infrastructure"-এ পুরোনো server-এ update-এর বদলে নতুন image (Module 12) — সবকিছুর ভিত্তি এই lesson।

## 3. সহজ ভাষায় পরিচয়

**Update-এর ধরন (Ubuntu):**

| Pocket | কী |
|---|---|
| `noble-security` | Security fix — সবচেয়ে জরুরি |
| `noble-updates` | Bug fix (ও security fix-এর copy) |
| `noble-backports` | নতুন version-এর software (ঐচ্ছিক) |

**কখন reboot লাগে:** Kernel update (নতুন kernel শুধু boot-এর সময় load হয়), কিছু core library (যেমন `libc6`) — যদিও library-র ক্ষেত্রে প্রায়ই শুধু সংশ্লিষ্ট service restart যথেষ্ট। Ubuntu reboot দরকার হলে `/var/run/reboot-required` file তৈরি করে।

**Boot process — ছয়টি ধাপ:**

1. **Firmware (UEFI/BIOS):** hardware পরীক্ষা, boot device খোঁজা।
2. **Bootloader (GRUB):** কোন kernel চালাবে (menu), kernel ও initramfs memory-তে load।
3. **Kernel:** hardware initialize, driver।
4. **initramfs:** ছোট অস্থায়ী root filesystem — আসল root disk mount করার জন্য দরকারি driver (LVM, encryption) এখানে।
5. **systemd (PID 1):** আসল root-এ switch, unit চালু।
6. **Target:** `multi-user.target` (server) বা `graphical.target` (desktop)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### গাড়ি চালু করা ও গ্যারেজ

- **Boot** = গাড়ি চালু: চাবি ঘোরানো (firmware), ইঞ্জিন স্টার্টার (bootloader), ইঞ্জিন চালু (kernel), প্রথমে ছোট ব্যাটারি থেকে শক্তি (initramfs), তারপর পূর্ণ ইঞ্জিনে (systemd), গাড়ি চলার জন্য প্রস্তুত (target)।
- **Update** = নিয়মিত servicing: ব্রেক প্যাড বদলানো (security fix) জরুরি; কিন্তু হাইওয়েতে চলার সময় নয় — গ্যারেজে (maintenance window)।
- **Recovery mode** = গাড়ি চালু না হলে মেকানিকের সরাসরি ইঞ্জিনে কাজ — সব আরামদায়ক সুবিধা ছাড়া, শুধু মৌলিক tool দিয়ে।
- **পুরোনো kernel-এ boot** = নতুন যন্ত্রাংশে সমস্যা হলে আগের যন্ত্রাংশ ফিরিয়ে লাগানো — Linux সাধারণত পুরোনো kernel রেখে দেয় ঠিক এই কারণে।

### Analogy কোথায় মেলে না

- গাড়ির servicing হলে তখনই নতুন যন্ত্রাংশ কাজ করে। Linux-এ update install হলেও **চলমান process পুরোনো code চালাতেই থাকে** (পুরোনো library memory-তে, L01-03-এর deleted-but-open-এর মতো) — restart বা reboot না হওয়া পর্যন্ত vulnerability থেকে যায়। "Update করেছি" ≠ "সুরক্ষিত"।
- গাড়ি চালু না হলে মেকানিক হাতে পান। Cloud server-এ console নাও থাকতে পারে — boot ভাঙলে recovery অনেক কঠিন (cloud-এর serial console বা disk অন্য instance-এ attach করে মেরামত, Module 08)। তাই অনেক team ভাঙা server ঠিক করার বদলে **নতুন image থেকে নতুন server** (immutable infrastructure)।

## 5. Real-world engineering scenario — "Server boot-এ ৭৩ সেকেন্ড লাগে"

**পরিস্থিতি:** Ubuntu server-এ প্রতিটি reboot-এ এক মিনিটের বেশি অপেক্ষা। Rolling reboot-এ ২০টি server × ১ মিনিট = অনেক সময় ও ঝুঁকি।

**Diagnosis (এই lesson-এর নমুনা data-য় আসল ফল):**

```text
total boot: 73.6s
  firmware      3.2s    4.4%
  loader        2.1s    2.9%
  kernel        1.8s    2.5%
  userspace    66.4s   90.3%
slowest units (top 4):
   60.20s  systemd-networkd-wait-online.service
    3.12s  snapd.service
    2.51s  cloud-init.service
    1.40s  dev-mapper-ubuntu\x2d\x2dvg\x2dubuntu\x2d\x2dlv.device
```

৯০% সময় userspace-এ, তার মধ্যে ৬০ সেকেন্ড একটি unit: `systemd-networkd-wait-online` — **সব** network interface "online" হওয়ার অপেক্ষা করে, default timeout প্রায় ২ মিনিট পর্যন্ত। Server-এ একটি অব্যবহৃত interface (cable নেই) configure করা আছে → প্রতিবার timeout পর্যন্ত অপেক্ষা।

**সমাধান:** Netplan-এ অব্যবহৃত interface-কে `optional: true` চিহ্নিত করা (বা configuration থেকে সরানো) — Module 02-এ network configuration। সতর্কতা: সব network ছাড়া চালু হওয়া কিছু service-এর জন্য সমস্যা হতে পারে — কোনটি সত্যিই network-online দরকার (L01-10-এর `After=network-online.target`) তা আগে দেখুন।

**`critical-chain`** দিয়ে নিশ্চিত হোন এটি আসলে boot-কে আটকাচ্ছে কিনা (blame-এ বেশি সময় মানেই critical path নয় — অনেক unit parallel চলে):

```bash
systemd-analyze critical-chain
```

## 6. Diagram

### Boot sequence

```text
 Power ─► UEFI firmware ─► EFI partition (/boot/efi) ─► GRUB
                                                         │ menu: কোন kernel? (Esc/Shift দিয়ে দেখা যায়)
                                                         ▼
                                   /boot/vmlinuz-6.8.0-48-generic + initrd.img-6.8.0-48-generic
                                                         │
                                         kernel ─► initramfs (LVM/crypt driver, root খোঁজা)
                                                         │ switch_root
                                                         ▼
                                         systemd (PID 1) ─► sysinit ─► basic ─► multi-user.target
                                                         │
                         ভাঙলে: emergency.target (শুধু root shell, root fs read-only)
                                rescue.target (single-user, মৌলিক service)
```

### নিরাপদ update প্রবাহ (একটি server)

```text
 snapshot/backup ─► apt update ─► apt list --upgradable (পড়ুন!) ─► apt upgrade
     ─► needrestart (কোন service পুরোনো library চালাচ্ছে) ─► service restart
     ─► reboot-required? ─► maintenance window-এ reboot ─► যাচাই (service, log, boot_report)
     ─► ভাঙলে: GRUB-এ পুরোনো kernel / snapshot rollback
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Security pocket | Security fix-এর আলাদা repository অংশ |
| `unattended-upgrades` | স্বয়ংক্রিয় (সাধারণত শুধু security) update |
| Phased update | Ubuntu নতুন update ধাপে ধাপে কিছু শতাংশ machine-এ দেয় — সমস্যা হলে থামায় |
| `needrestart` | কোন service পুরোনো library চালাচ্ছে চিহ্নিত ও restart প্রস্তাব |
| Livepatch | Reboot ছাড়া kernel-এ নির্দিষ্ট security fix (Canonical-এর service) |
| UEFI | আধুনিক firmware interface |
| GRUB | Bootloader — kernel বেছে নেয় ও load করে |
| initramfs / initrd | Boot-এর প্রথম অস্থায়ী root filesystem |
| Kernel command line | Kernel-কে boot-এ দেওয়া parameter (`/proc/cmdline`) |
| rescue.target / emergency.target | মেরামতের জন্য ন্যূনতম systemd অবস্থা |
| fsck | Filesystem consistency যাচাই ও মেরামত (unmounted অবস্থায়) |
| `systemd-analyze` | Boot সময় বিশ্লেষণ (`blame`, `critical-chain`) |
| Immutable infrastructure | Server বদলানোর বদলে নতুন image থেকে নতুন server |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Update install হলেও কেন পুরোনো code চলে

Process চালু হওয়ার সময় library (যেমন `libssl.so`) memory-তে map হয় (L01-09)। Update নতুন file লেখে (আসলে নতুন inode — L01-03), কিন্তু চলমান process পুরোনো inode ধরে থাকে। তাই:

```bash
sudo lsof -n | grep 'DEL.*\.so' | awk '{print $1}' | sort -u    # পুরোনো (মুছে ফেলা) library চালানো process
sudo needrestart -r l                                            # তালিকা (Ubuntu 22.04+-এ apt-এর পরে স্বয়ংক্রিয়ও চলে)
```

### 8.2 Kernel ও পুরোনো kernel রাখা

`apt` সাধারণত শেষ কয়েকটি kernel রাখে (`apt autoremove` পুরোনোগুলো সরায়, কিন্তু চলমান ও সর্বশেষটি রাখে)। নতুন kernel-এ সমস্যা হলে GRUB menu-তে **"Advanced options"** থেকে পুরোনো kernel বেছে নিন। Server-এ GRUB menu default-ভাবে লুকানো থাকতে পারে — boot-এর সময় `Esc` (UEFI) বা `Shift` (BIOS) চাপুন; VM console দরকার।

> **Fedora-তে:** `installonly_limit` (default ৩) অনুযায়ী kernel রাখে; GRUB menu সাধারণত দেখা যায়। `dnf history undo <id>` দিয়ে একটি update পুরো ফিরিয়ে নেওয়া যায় (L01-02)। Fedora Workstation-এ btrfs snapshot-ভিত্তিক rollback-ও সম্ভব (setup অনুযায়ী)।

### 8.3 Recovery পরিস্থিতি ও সমাধান

| পরিস্থিতি | লক্ষণ | সমাধান |
|---|---|---|
| ভুল `/etc/fstab` লাইন | Boot emergency mode-এ আটকে, "Give root password for maintenance" | Root password দিয়ে ঢুকে (বা GRUB-এ kernel cmdline দিয়ে) `mount -o remount,rw /`, fstab ঠিক, `systemctl daemon-reload`, reboot; ভবিষ্যতে অপ্রয়োজনীয় disk-এ `nofail` ও reboot-এর আগে `findmnt --verify` (L01-03) |
| নতুন kernel boot হয় না | Kernel panic বা driver সমস্যা | GRUB-এ পুরোনো kernel |
| Root password জানা নেই / sudo user lock | Login সম্ভব নয় | GRUB-এ `e` চেপে kernel line-এ `systemd.unit=rescue.target` বা `init=/bin/bash` যোগ করে boot, তারপর `passwd` |
| Filesystem error | "UNEXPECTED INCONSISTENCY; RUN fsck MANUALLY" | Emergency shell-এ `fsck -y /dev/...` (**unmounted** অবস্থায়) |
| ভাঙা package update | Service চালু হয় না | `/var/log/apt/history.log`, পুরোনো version install (`apt install pkg=version`), বা snapshot |

> **Fedora-তে:** root password ভুলে গেলে GRUB-এ `rd.break` যোগ করে initramfs shell-এ ঢুকে `/sysroot` mount করা হয়; আর **SELinux-এর জন্য পরে `touch /.autorelabel`** দিতে হয় (না দিলে পরিবর্তিত `/etc/shadow`-এর label ভুল থাকায় login ব্যর্থ — L01-17)।

⚠️ GRUB-এ `init=/bin/bash`-এর ক্ষমতা মানে **console access = root access**। Physical/console access-এর নিরাপত্তা (GRUB password, disk encryption) তাই গুরুত্বপূর্ণ (Module 19)।

### 8.4 Automatic update-এর নীতি

| পদ্ধতি | সুবিধা | ঝুঁকি |
|---|---|---|
| `unattended-upgrades` (security only) | দ্রুত সুরক্ষা, কম কাজ | বিরল ভাঙন; reboot নীতি আলাদা লাগে |
| নির্ধারিত window-এ হাতে/automation | নিয়ন্ত্রণ, পরীক্ষা | দেরি হলে vulnerability খোলা |
| Immutable image (নতুন server) | পূর্বানুমেয়, rollback সহজ | Pipeline লাগে (Module 11, 12) |

বাস্তবে প্রায়ই মিশ্রণ: security update স্বয়ংক্রিয়, reboot নিয়ন্ত্রিত window-এ rolling (একবারে একটি server, health check পাস করলে পরেরটি)।

## 9. Practical demonstration (Ubuntu VM — **আগে snapshot**)

### 9.1 Update পর্যবেক্ষণ ও নিরাপদ install

```bash
sudo apt update
apt list --upgradable                          # কী আসবে — পড়ুন
apt-cache policy openssl                       # কোন pocket থেকে
systemctl status unattended-upgrades --no-pager
cat /etc/apt/apt.conf.d/20auto-upgrades        # automatic update চালু কিনা
sudo unattended-upgrade --dry-run --debug 2>&1 | tail -20   # কী install করত (কিছু বদলায় না)
sudo apt upgrade                               # ⚠️ system বদলায়
sudo needrestart -r l                          # কোন service restart দরকার
ls /var/run/reboot-required* 2>/dev/null && cat /var/run/reboot-required.pkgs
```

> **Fedora-তে:** `sudo dnf check-update`; security only: `sudo dnf upgrade --security`; automatic: `dnf-automatic` (dnf5-এ `dnf5-plugin-automatic`) ও তার timer; reboot দরকার কিনা: `sudo dnf needs-restarting -r` (dnf plugin — dnf version অনুযায়ী `dnf-plugins-core` বা dnf5-এর সমতুল্য লাগতে পারে; `dnf needs-restarting --help` দিয়ে যাচাই করুন)।

### 9.2 Reboot দরকার কিনা — Python

File: [`code/L01-18/boot_report.py`](code/L01-18/boot_report.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-18
uname -r > /tmp/running.txt
ls /boot/vmlinuz-* > /tmp/kernels.txt
cat /var/run/reboot-required.pkgs > /tmp/pkgs.txt 2>/dev/null || : > /tmp/pkgs.txt
python3 boot_report.py reboot --running /tmp/running.txt --kernels /tmp/kernels.txt --pkgs /tmp/pkgs.txt
```

**নমুনা দিয়ে আসল output:**

```bash
python3 boot_report.py reboot --running sample-running.txt --kernels sample-kernels.txt --pkgs sample-reboot-required.pkgs; echo "exit=$?"
```

```text
running kernel  : 6.8.0-45-generic
installed       : 6.8.0-9-generic, 6.8.0-45-generic, 6.8.0-48-generic
reboot needed   : YES
  - newer kernel installed: 6.8.0-48-generic (running 6.8.0-45-generic)
  - packages requesting reboot: linux-image-6.8.0-48-generic, libc6
exit=1
```

লক্ষ্য করুন version-এর **সংখ্যাভিত্তিক** ক্রম: `-9 < -45 < -48`। সাধারণ string sort-এ `"6.8.0-9"` সবচেয়ে বড় হতো (কারণ অক্ষর '9' > '4') এবং ভুলভাবে "নতুন kernel" ধরা হতো। (L01-02: version তুলনা string তুলনা নয়।)

### 9.3 Boot বিশ্লেষণ

```bash
systemd-analyze
systemd-analyze blame | head -10
systemd-analyze critical-chain
cat /proc/cmdline                              # এই boot-এর kernel parameter
journalctl -b -1 -p err --no-pager | tail      # আগের boot-এর error
systemd-analyze > /tmp/analyze.txt; systemd-analyze blame > /tmp/blame.txt
python3 boot_report.py boot /tmp/analyze.txt /tmp/blame.txt
```

নমুনার আসল output Section 5-এ।

### 9.4 Recovery অনুশীলন — ভাঙা fstab (⚠️ শুধু snapshot-যুক্ত VM-এ)

```bash
sudo cp /etc/fstab /etc/fstab.bak
echo 'UUID=00000000-0000-0000-0000-000000000000 /mnt/ghost ext4 defaults 0 2' | sudo tee -a /etc/fstab
sudo findmnt --verify                         # সতর্কতা দেখাবে — বাস্তবে এখানেই থামতেন
sudo reboot
```

প্রত্যাশিত: ~১ মিনিট ৩০ সেকেন্ড device-এর অপেক্ষা, তারপর **emergency mode**। VM console-এ:

```bash
# emergency shell-এ (root password দরকার — Ubuntu-তে root lock থাকলে নিচের বিকল্প দেখুন)
mount -o remount,rw /
cp /etc/fstab.bak /etc/fstab
systemctl daemon-reload
reboot
```

**Root password lock থাকলে (Ubuntu default):** GRUB menu-তে kernel entry-তে `e` → `linux ...` লাইনের শেষে `systemd.unit=rescue.target` বা (শেষ উপায়) `init=/bin/bash` যোগ → `Ctrl+X`। `init=/bin/bash`-এ systemd চলে না — `mount -o remount,rw /` করে fstab ঠিক, তারপর `exec /sbin/init` বা হার্ড reboot।

**শিক্ষা:** একটি লাইন পুরো server আটকাতে পারে — fstab বদলানোর পরে reboot-এর আগে `findmnt --verify` ও `mount -a`; অপ্রয়োজনীয় disk-এ `nofail`। আর console access ও snapshot ছাড়া এই experiment কখনো নয়।

শেষে snapshot-এ ফিরে যাওয়াও একটি বৈধ "recovery" — এবং production-এ এর সমতুল্য হলো image থেকে নতুন server।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_boot_report.py`](code/L01-18/test_boot_report.py)-এর ৭টি test: duration parse (`1min 6.401s`, `812ms` ...), নমুনা analyze ও blame, অসম্পূর্ণ boot, সংখ্যাভিত্তিক kernel sort, Fedora kernel নাম (rescue বাদ, `10 > 4`), reboot সিদ্ধান্ত, ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `TIME_RE` + `fullmatch` | `min`, `s`, `ms`-এর যেকোনো মিশ্রণ | systemd-এর duration format |
| `parse_analyze` regex | "Startup finished in ... = total" | Phase-গুলো `(name)` বন্ধনীতে |
| `parse_blame`: `rpartition(" ")` | শেষ space-এ ভাগ — unit নাম ডানে | Duration-এ space থাকে (`1min 0.204s`) |
| `version_key()` | সংখ্যা অংশ int | String sort-এর ভুল এড়ানো (`-9` বনাম `-45`) |
| `"rescue" not in name` | Fedora-র rescue kernel বাদ | Rescue image নিয়মিত kernel নয় |
| Exit 1 = reboot দরকার | Monitoring/automation-এ ব্যবহারযোগ্য | Rolling reboot script-এর ভিত্তি |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `apt list --upgradable` | আসন্ন update-এর তালিকা |
| Kernel update-এর পরে `boot_report.py reboot` | YES, exit 1; reboot-এর পরে no, exit 0 |
| `systemd-analyze critical-chain` | Boot-এর আসল বাধা |
| fstab experiment | Emergency mode, তারপর পুনরুদ্ধার |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Update-এর পরেও scanner পুরোনো version দেখায় | Process restart হয়নি | `needrestart`, `lsof \| grep DEL` | Service restart / reboot |
| Boot ধীর | একটি unit-এর অপেক্ষা | `systemd-analyze critical-chain` | কারণ ঠিক (Section 5) |
| `/boot` পূর্ণ, kernel update ব্যর্থ | অনেক পুরোনো kernel | `df -h /boot`, `dpkg -l 'linux-image*'` | `sudo apt autoremove --purge` |
| Emergency mode | fstab, filesystem error | Console বার্তা, `journalctl -xb` | Section 8.3 |
| নতুন kernel-এ boot হয় না | Driver/regression | — | GRUB-এ পুরোনো kernel; bug report |
| GRUB menu দেখা যায় না | Timeout ০/hidden | — | Boot-এ Esc/Shift; `/etc/default/grub` (`GRUB_TIMEOUT_STYLE=menu`) তারপর `sudo update-grub` |

> **Fedora-তে:** GRUB configuration পরিবর্তনের পরে `sudo grub2-mkconfig -o /boot/grub2/grub.cfg` (UEFI-তেও আধুনিক Fedora-তে এই path) বা `grubby` দিয়ে kernel argument।

## 13. Security, performance ও cost বিবেচনা

- **Security:** Security update দ্রুত — এবং restart/reboot নিশ্চিত; "installed" ≠ "active"। Console/GRUB access = root — GRUB password, disk encryption, cloud console-এর access নিয়ন্ত্রণ। Recovery-র সময় নেওয়া shortcut (যেমন SELinux autorelabel ভুলে যাওয়া) পরে নতুন সমস্যা তৈরি করে।
- **Performance:** Boot সময় কম = দ্রুত autoscaling ও rolling update (Module 14); অপ্রয়োজনীয় service (যেমন server-এ snapd/cloud-init দরকার না হলে) বিবেচনা — তবে প্রতিটির ভূমিকা বুঝে।
- **Cost:** ভাঙা server মেরামতে engineer-এর ঘণ্টা বনাম image থেকে নতুন server-এর মিনিট — immutable infrastructure-এর অর্থনৈতিক যুক্তি।

## 14. Hands-on exercise

1. `unattended-upgrade --dry-run --debug` চালিয়ে কোন package স্বয়ংক্রিয়ভাবে আসত তালিকা করুন; `/etc/apt/apt.conf.d/50unattended-upgrades`-এ কোন origin অনুমোদিত দেখুন।
2. একটি kernel update থাকলে install করে `boot_report.py reboot` চালান, reboot করে আবার চালান — ফল তুলনা।
3. `systemd-analyze critical-chain`-এ শীর্ষ বাধা চিহ্নিত করে তার কারণ ব্যাখ্যা লিখুন (ঠিক করা ঐচ্ছিক)।
4. `boot_report.py`-তে `chain` command যোগ করুন যা `systemd-analyze critical-chain`-এর output (`@` ও `+` সময়) parse করে সবচেয়ে বড় `+` সময়ের unit দেখায়। Test লিখুন।
5. VM-এ fstab recovery experiment (Section 9.4) সম্পূর্ণ করুন এবং notebook-এ incident report (L00-06 format) লিখুন।

## 15. Mini-project — rolling update plan

তিনটি VM (বা একটি VM-এ ধারণাগত) জন্য একটি লিখিত ও script-সমর্থিত পরিকল্পনা: (১) প্রতিটিতে `apt upgrade` → `needrestart` → `boot_report.py reboot`; (২) reboot দরকার হলে একবারে একটি; (৩) reboot-এর পরে health check (L01-10-এর `/health`); (৪) ব্যর্থ হলে থামো ও alert; (৫) rollback পথ (পুরোনো kernel / snapshot)। Module 13 (Ansible)-এ এটি automate হবে।

## 16. Interview প্রশ্ন

1. Linux boot process-এর ধাপগুলো বলুন। initramfs কেন দরকার?
2. Security update install করার পরে কেন service restart বা reboot লাগে?
3. নতুন kernel-এ server boot হচ্ছে না — কী করবেন?
4. ভুল `/etc/fstab`-এ server emergency mode-এ — কীভাবে ঠিক করবেন এবং কীভাবে প্রতিরোধ করবেন?
5. Boot ধীর — কীভাবে তদন্ত করবেন?
6. Automatic security update-এর সুবিধা ও ঝুঁকি কী? কীভাবে নিরাপদে চালাবেন?
7. Immutable infrastructure কী এবং এটি update ও recovery-কে কীভাবে বদলায়?

## 17. Self-assessment প্রশ্ন

1. গাড়ি analogy কোথায় মেলে না?
2. Section 5-এ ৯০% সময় কোথায় এবং কেন?
3. `version_key` না থাকলে কোন ভুল সিদ্ধান্ত হতো?
4. Fedora-তে root password reset-এর পরে `.autorelabel` কেন?
5. `init=/bin/bash`-এর নিরাপত্তা অর্থ কী?
6. Update প্রবাহের ধাপগুলো (snapshot থেকে যাচাই পর্যন্ত)।

## 18. সংক্ষিপ্ত সারাংশ

- Security update দ্রুত; কিন্তু **restart/reboot** ছাড়া চলমান process পুরোনো code চালায় — `needrestart`, `reboot-required`।
- Boot: UEFI → GRUB → kernel + initramfs → systemd → target; `systemd-analyze blame/critical-chain`।
- Recovery: পুরোনো kernel, rescue/emergency target, fstab ঠিক, `fsck`, password reset — console access দরকার, তাই snapshot ও immutable image।
- Version তুলনা সংখ্যাভিত্তিক — string নয়।

## 19. Completion checklist

- [ ] `apt list --upgradable`, `unattended-upgrade --dry-run`, `needrestart` চালিয়েছি
- [ ] `boot_report.py reboot` ও `boot` নিজের VM-এ চালিয়েছি
- [ ] `systemd-analyze blame` ও `critical-chain` পড়েছি
- [ ] (snapshot সহ) fstab recovery experiment সম্পন্ন
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [Module 01 lab](../labs/01-linux-systems/README.md) ও [quiz](../assessments/01-linux-systems/quiz.md)
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Ubuntu Server — Automatic updates / package management: https://documentation.ubuntu.com/server/
- `systemd-analyze(1)`: https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html
- `bootup(7)` — systemd boot process: https://www.freedesktop.org/software/systemd/man/latest/bootup.html
- `systemd.special(7)` — rescue.target, emergency.target: https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html
- GNU GRUB manual: https://www.gnu.org/software/grub/manual/grub/
- Kernel docs — kernel command line parameters: https://docs.kernel.org/admin-guide/kernel-parameters.html
- Fedora — DNF: https://docs.fedoraproject.org/en-US/quick-docs/dnf/

---

**Module 01 সম্পন্ন!** এখন: [Module 01-এর lab](../labs/01-linux-systems/README.md) ও [module quiz](../assessments/01-linux-systems/quiz.md)।

**পরের lesson:** L02-01 — OSI ও TCP/IP model
