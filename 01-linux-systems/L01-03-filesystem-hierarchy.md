# L01-03 — Filesystem hierarchy, mount point, inode ও link

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-02 — Package management](L01-02-package-management.md) |
| **Label** | — (সব experiment temporary directory-তে) |
| **Tested** | `fs_explorer.py`: ৪টি unit test পাস; `links`, `mounts`, `fhs` চালানো (Python 3.14, Windows/Git Bash)। Windows-এ symlink বিশেষ অধিকার ছাড়া তৈরি হয়নি — script তা "skipped" বলেছে; hard link অংশ চালানো হয়েছে। `sample-mounts.txt` হাতে তৈরি (Ubuntu-র `/proc/mounts`-এর format-এ)। `ls -li`, `df`, `findmnt`, `lsof` ইত্যাদি **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- Linux-এর **একক directory tree** ও **Filesystem Hierarchy Standard (FHS)** — কোন জিনিস কোথায়, কেন।
- **Mount** — একটি disk বা filesystem tree-এর কোনো জায়গায় যুক্ত করা; `/etc/fstab`।
- **Inode** — file-এর আসল পরিচয়; নাম আর data আলাদা কেন।
- **Hard link** ও **symbolic link** — পার্থক্য ও ব্যবহার।
- দুটি বিখ্যাত production সমস্যা: **inode শেষ** এবং **মুছে ফেলা কিন্তু খোলা file**।
- Python দিয়ে FHS lookup, mount table বিশ্লেষণ ও link experiment।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Windows-এ প্রতিটি disk আলাদা অক্ষর পায় (`C:`, `D:`)। Linux-এ **একটিমাত্র tree**, শুরু `/` থেকে; প্রতিটি disk বা partition সেই tree-এর কোনো directory-তে "mount" হয়। এই নকশার সুবিধা: application জানে না বা পরোয়া করে না `/var/lib/postgresql` কোন disk-এ — admin পরে বড় disk mount করে দিলেও path একই থাকে।

FHS না থাকলে প্রতিটি distribution ও program নিজের মতো file রাখত — log কোথায়, config কোথায়, কেউ জানত না। FHS-এর কারণে যেকোনো Linux server-এ গিয়েই আপনি জানেন: config `/etc`-এ, log `/var/log`-এ, service data `/var/lib`-এ।

Inode ও link বোঝা জরুরি কারণ বাস্তবে "disk full" incident-এর বড় অংশ এখানেই রহস্যময় হয়ে ওঠে: `df` বলে disk পূর্ণ, কিন্তু `du` সব যোগ করে অনেক কম পায় — কেন? এই lesson-এর শেষে উত্তর জানবেন।

## 3. সহজ ভাষায় পরিচয়

### FHS-এর গুরুত্বপূর্ণ directory

| Directory | কী থাকে | DevOps-এ মনে রাখার কথা |
|---|---|---|
| `/etc` | System-wide configuration | Backup ও version control-এর প্রধান লক্ষ্য |
| `/var/log` | Log | Disk পূর্ণ হওয়ার এক নম্বর কারণ |
| `/var/lib` | Service-এর স্থায়ী data (DB, package database) | **Backup করুন**; মুছবেন না |
| `/var/cache` | পুনরায় তৈরিযোগ্য cache | মুছলে ক্ষতি নেই |
| `/tmp`, `/var/tmp` | অস্থায়ী file | `/tmp` reboot-এ মুছতে পারে |
| `/run` | চলমান অবস্থা (PID file, socket) | RAM-এ (tmpfs), reboot-এ মুছে যায় |
| `/home`, `/root` | User-দের home | |
| `/usr` | Installed software | Package manager-এর এলাকা — হাতে বদলাবেন না |
| `/usr/local`, `/opt` | Package manager-এর বাইরের software | হাতে install করা জিনিস এখানে |
| `/srv` | এই server যে data serve করে | যেমন website-এর file |
| `/proc`, `/sys`, `/dev` | Kernel-এর virtual filesystem | Disk-এ নেই, kernel তৈরি করে |
| `/boot` | Kernel ও bootloader | পূর্ণ হলে kernel update ব্যর্থ |

আধুনিক Ubuntu ও Fedora-তে `/bin`, `/sbin`, `/lib` আসলে `/usr/bin`, `/usr/sbin`, `/usr/lib`-এর symbolic link ("usr merge")।

### Inode কী?

প্রতিটি file-এর একটি **inode** থাকে — একটি data structure যাতে আছে: file-এর ধরন, permission, owner, size, সময় (modify, change, access), link সংখ্যা, এবং data কোন disk block-এ আছে তার তালিকা। **File-এর নাম inode-এ থাকে না।** নাম থাকে **directory**-তে: directory আসলে একটি তালিকা — "নাম → inode নম্বর"।

### Hard link ও symbolic link

- **Hard link:** একই inode-এর আরেকটি নাম। দুটি নামই সমান — কোনটি "আসল" নেই। একটি নাম মুছলে data থাকে, যতক্ষণ অন্তত একটি নাম আছে।
- **Symbolic (soft) link:** একটি আলাদা ছোট file যাতে আরেকটি **path** লেখা থাকে। Target মুছলে symlink "ঝুলে" থাকে (dangling)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### লাইব্রেরি

- **Inode** = বইয়ের তাকের নির্দিষ্ট অবস্থান ও বইটির কার্ড (লেখক, পাতা সংখ্যা, কোথায় আছে)।
- **Directory** = catalog — "বইয়ের নাম → তাক নম্বর"।
- **Hard link** = catalog-এ একই তাক নম্বরের জন্য দুটি নাম ("Pather Panchali" ও "পথের পাঁচালী")। একটি entry মুছলেও বই তাকে থাকে, অন্য নাম দিয়ে পাওয়া যায়। সব entry মুছলে তবেই বই সরানো হয়।
- **Symbolic link** = একটি চিরকুট: "পথের পাঁচালী দেখুন"। বইটি সরিয়ে ফেললে চিরকুট থাকে, কিন্তু অর্থহীন।
- **Mount** = লাইব্রেরির নতুন ভবন মূল ভবনের একটি দরজার সাথে জুড়ে দেওয়া — পাঠক জানেন না তারা অন্য ভবনে ঢুকেছেন।

### Analogy কোথায় মেলে না

- লাইব্রেরিতে বই নেওয়া থাকলে (কেউ পড়ছেন) catalog থেকে মুছলেও বই পাঠকের হাতে থাকে — এটি আসলে **মেলে**, এবং Linux-এর একটি গুরুত্বপূর্ণ আচরণ: কোনো process file খোলা রাখলে নাম মুছলেও data disk-এ থাকে যতক্ষণ না process file বন্ধ করে। এটিই "disk full কিন্তু file খুঁজে পাই না" রহস্যের কারণ (Section 5)।
- Hard link **একই filesystem-এর** ভেতরে সীমিত — inode নম্বর শুধু সেই filesystem-এ অর্থবহ। লাইব্রেরির catalog অন্য ভবনের তাকও দেখাতে পারত। Symlink filesystem পেরিয়েও কাজ করে, কারণ এটি শুধু path।
- Directory-র hard link সাধারণত অনুমোদিত নয় (loop তৈরি হতে পারে) — বইয়ের ক্ষেত্রে এমন কোনো নিয়ম নেই।

## 5. Real-world engineering scenario — "df বলে ১০০%, du বলে ৪০%"

**পরিস্থিতি:** রাত ৩টায় alert: `/` partition ১০০% পূর্ণ। Web server log লিখতে পারছে না, database write ব্যর্থ।

**ঘটনার ক্রম:**

1. On-call engineer দেখলেন `/var/log/app/debug.log` ৩০ GB। দ্রুত `rm /var/log/app/debug.log` করলেন।
2. `df -h /` — এখনো ১০০%!
3. `du -sh /` সব যোগ করে মাত্র ৪০%-এর হিসাব পায়।

**কারণ:** Application process তখনো `debug.log` **খোলা রেখেছে**। `rm` শুধু directory থেকে নাম মুছেছে (inode-এর link সংখ্যা ১ → ০), কিন্তু খোলা file descriptor থাকায় kernel inode ও data মুছে না। `du` নাম ধরে হাঁটে — নামহীন file দেখে না; `df` filesystem-এর আসল ব্যবহার দেখে।

**Diagnosis:**

```bash
sudo lsof +L1          # link সংখ্যা < 1 অথচ খোলা file — "deleted"
```

উদাহরণ output:

```text
COMMAND   PID   USER  FD  TYPE DEVICE    SIZE/OFF NLINK  NODE NAME
python3  1234   app   3w  REG  253,0  32212254720     0 81921 /var/log/app/debug.log (deleted)
```

**সমাধান:**

- Process restart (file বন্ধ হবে, জায়গা মুক্ত)। অথবা restart সম্ভব না হলে খোলা file খালি করা: `: > /proc/1234/fd/3` (⚠️ সাবধানে — ভুল fd দিলে অন্য data নষ্ট)।
- ভবিষ্যতে: চলমান log `rm` নয়, **truncate** (`: > file`) বা **logrotate** (L01-14) দিয়ে, যা app-কে নতুন file খুলতে signal দেয়।

**দ্বিতীয় রহস্য — inode শেষ:** কখনো `df -h` বলে ৫০% খালি, অথচ "No space left on device"। কারণ: লাখ লাখ ছোট file (cache, session, mail queue) সব **inode** খরচ করে ফেলেছে। `df -i` দিয়ে দেখুন। প্রতিটি filesystem তৈরির সময় inode-এর নির্দিষ্ট সংখ্যা ঠিক হয় (ext4-এ)।

## 6. Diagram

### Directory, inode ও data block

```text
 Directory "/home/sami"  (নাম → inode তালিকা)
 ┌────────────────────┬────────┐
 │ notes.txt          │ 81921  │──┐
 │ notes-backup.txt   │ 81921  │──┤   hard link: একই inode
 │ shortcut           │ 81950  │──┼──────────────────────┐
 └────────────────────┴────────┘  │                      │
                                  ▼                      ▼
                    inode 81921                    inode 81950 (symlink)
                    ┌──────────────────────┐       ┌───────────────────────┐
                    │ type: regular file   │       │ type: symbolic link   │
                    │ mode: rw-r--r--      │       │ data: "notes.txt"     │──► (path ধরে আবার খোঁজে)
                    │ owner: sami          │       └───────────────────────┘
                    │ size: 4096           │
                    │ links: 2             │
                    │ blocks: [5310, 5311] │──► disk-এর data block
                    └──────────────────────┘
```

### একক tree-তে mount

```text
 /                        ← /dev/mapper/ubuntu--vg-ubuntu--lv (ext4)
 ├── boot                 ← /dev/sda2 (ext4)
 │   └── efi              ← /dev/sda1 (vfat)
 ├── proc                 ← proc (virtual)
 ├── run                  ← tmpfs (RAM)
 ├── var
 │   └── lib/postgresql   ← (চাইলে আলাদা দ্রুত disk mount করা যায়)
 └── mnt/backup disk      ← /dev/sdb1 (ext4, read-only)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| FHS | Linux-এ কোন file কোন directory-তে থাকবে তার standard |
| Filesystem | Disk-এ data সংগঠনের পদ্ধতি (ext4, xfs, btrfs, vfat) — এবং tree-এর অর্থেও ব্যবহৃত |
| Mount / mount point | Filesystem-কে tree-এর একটি directory-তে যুক্ত করা / সেই directory |
| `/etc/fstab` | Boot-এর সময় কোন filesystem কোথায় mount হবে তার তালিকা |
| UUID | Filesystem-এর স্থায়ী অনন্য পরিচয় (device নাম `/dev/sdb` বদলাতে পারে) |
| Inode | File-এর metadata ও data-র অবস্থান রাখা structure |
| Link count | একটি inode-এর কতগুলো নাম (hard link) আছে |
| Hard link | একই inode-এর অতিরিক্ত নাম; একই filesystem-এ সীমিত |
| Symbolic link | অন্য path নির্দেশকারী আলাদা file |
| Dangling symlink | Target নেই এমন symlink |
| Virtual filesystem | Disk-এ নেই, kernel তৈরি করে (`proc`, `sysfs`, `tmpfs`) |
| VFS | Kernel-এর Virtual File System স্তর — সব filesystem-কে একই interface দেয় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Path resolution

`cat /home/sami/notes.txt` চালালে kernel:

1. `/`-এর inode থেকে শুরু (root directory-র inode জানা)।
2. `/`-এর directory তালিকায় `home` খুঁজে তার inode পায়।
3. সেখানে mount আছে কিনা দেখে (থাকলে অন্য filesystem-এর root-এ চলে যায়)।
4. `home` → `sami` → `notes.txt` — প্রতিটি ধাপে directory-র **execute (x) permission** লাগে (L01-04)।
5. শেষ inode পেলে permission যাচাই করে file খোলে।

Symlink পেলে kernel তার ভেতরের path দিয়ে আবার resolution শুরু করে (loop আটকাতে সীমা আছে — `ELOOP` error)।

### 8.2 কখন data আসলে মুছে যায়

একটি inode-এর data মুক্ত হয় যখন **link count = 0 এবং কোনো process file খোলা রাখেনি**। `rm` আসলে `unlink` system call (L01-01) — নাম মোছে, link count কমায়। এজন্য Linux-এ চলমান program-এর binary update করা যায়: পুরোনো program পুরোনো inode ধরে রাখে, নতুন নাম নতুন inode দেখায়।

### 8.3 Mount ও fstab

```text
# /etc/fstab (উদাহরণ)
UUID=3f1c...-...  /             ext4  defaults                 0 1
UUID=9a2b...-...  /boot         ext4  defaults                 0 2
UUID=77de...-...  /mnt/backup   ext4  defaults,nofail,noexec   0 2
```

| Column | অর্থ |
|---|---|
| ১ | কী mount হবে — UUID ব্যবহার করুন, `/dev/sdb1` নয় (disk-এর ক্রম বদলালে নাম বদলায়) |
| ২ | কোথায় |
| ৩ | Filesystem type |
| ৪ | Option: `ro` (শুধু পড়া), `noexec` (এখান থেকে program চালানো নিষেধ), `nosuid`, `nofail` (disk না থাকলেও boot চলবে) |
| ৫ | dump (পুরোনো, সাধারণত ০) |
| ৬ | Boot-এ fsck ক্রম (root = ১, অন্য = ২, না = ০) |

⚠️ `/etc/fstab`-এ ভুল লাইন boot আটকে দিতে পারে। সম্পাদনার পরে reboot-এর আগে `sudo mount -a` ও `sudo findmnt --verify` দিয়ে যাচাই করুন। পরিবর্তন L01-12-এ (VM-এ) অনুশীলন করবেন।

### 8.4 Performance ও security

- `noexec`, `nosuid`, `nodev` mount option দিয়ে `/tmp` বা data partition থেকে ক্ষতিকর program চালানো কঠিন করা যায় (hardening, L06-08)।
- `relatime` (default) access time কম লেখে — performance।
- লাখ লাখ ছোট file এক directory-তে থাকলে `ls` ধীর ও inode-এর চাপ — hierarchy (যেমন `ab/cd/abcdef...`) ব্যবহার করুন।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 Tree ও FHS

```bash
ls /
ls -ld /bin /sbin /lib       # usr merge: symlink কিনা দেখুন
man hier                     # FHS-এর বিবরণ (Linux-এর নিজস্ব manual)
```

Python lookup — File: [`code/L01-03/fs_explorer.py`](code/L01-03/fs_explorer.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-03
python3 fs_explorer.py fhs /var/log/nginx/access.log
python3 fs_explorer.py fhs /var/lib/postgresql/16/main
```

**আসল output (repository-তে চালানো):**

```text
/var/log/nginx/access.log
  belongs to /var/log: log file — disk পূর্ণ হওয়ার সাধারণ কারণ
/var/lib/postgresql/16/main
  belongs to /var/lib: service-এর স্থায়ী state (database, package database) — backup করুন
```

> Windows-এর Git Bash-এ এই command চালালে Git Bash `/var/...` path-কে Windows path-এ রূপান্তর করে ফেলে — এই repository লেখার সময় তাই হয়েছিল। সমাধান: `MSYS_NO_PATHCONV=1`। Linux-এ এই সমস্যা নেই।

### 9.2 Mount দেখা

```bash
findmnt --real               # শুধু আসল filesystem, tree আকারে
lsblk -f                     # disk, partition, filesystem type, UUID
df -hT                       # কোন mount-এ কত জায়গা ও type
df -i                        # inode ব্যবহার
cat /etc/fstab
```

Python দিয়ে `/proc/mounts` বিশ্লেষণ:

```bash
python3 fs_explorer.py mounts              # আপনার আসল /proc/mounts
python3 fs_explorer.py mounts sample-mounts.txt
```

**Sample data দিয়ে আসল output:**

```text
12 mounts, 4 on real/block filesystems:
  /                    ext4   rw  /dev/mapper/ubuntu--vg-ubuntu--lv
  /boot                ext4   rw  /dev/sda2
  /boot/efi            vfat   rw  /dev/sda1
  /mnt/backup disk     ext4   ro  /dev/sdb1
special (virtual / loop / overlay) types: cgroup2, devpts, devtmpfs, proc, squashfs, sysfs, tmpfs
```

লক্ষ্য করুন `/mnt/backup disk` — `/proc/mounts`-এ space লেখা থাকে `\040` হিসেবে; script সেটি রূপান্তর করে। আর `squashfs` (snap package) ও `tmpfs` disk partition নয়।

> **Fedora-তে:** default filesystem **btrfs** (Workstation), subvolume `/` ও `/home` — `findmnt` ও `lsblk -f`-এ দেখবেন। Ubuntu default **ext4**।

### 9.3 Inode ও link — হাতে

```bash
cd "$(mktemp -d)"            # temporary directory-তে কাজ
echo "data" > original.txt
ln original.txt hard.txt     # hard link
ln -s original.txt soft.txt  # symbolic link
ls -li                       # -i: inode নম্বর; দ্বিতীয় column: link count
stat original.txt
```

উদাহরণ output:

```text
81921 -rw-rw-r-- 2 sami sami  5 Oct 26 10:00 hard.txt
81921 -rw-rw-r-- 2 sami sami  5 Oct 26 10:00 original.txt
81950 lrwxrwxrwx 1 sami sami 12 Oct 26 10:00 soft.txt -> original.txt
```

- `original.txt` ও `hard.txt`-এর inode **একই** (81921), link count **২**।
- `soft.txt`-এর নিজস্ব inode, ধরন `l`, size = path-এর দৈর্ঘ্য (১২ অক্ষর)।

এখন original মুছুন:

```bash
rm original.txt
cat hard.txt                 # "data" — এখনো আছে
cat soft.txt                 # No such file or directory — dangling
ls -li
```

Python দিয়ে একই experiment (temporary directory-তে, শেষে নিজেই মোছে):

```bash
python3 fs_explorer.py links
```

**এই repository-তে (Windows-এ) চালিয়ে পাওয়া আসল output:**

```text
symlink: not permitted on this system (skipped)
original inode=10414574139026953 links=2
hard     inode=10414574139026953 same_inode=True
original deleted
hard still readable=True links=1
```

Windows-এ (NTFS) hard link ও "inode-এর মত" file index আছে, কিন্তু symlink তৈরিতে বিশেষ অধিকার লাগে — তাই skip। Ubuntu-তে symlink অংশও চলবে এবং `soft dangling=True` দেখাবে।

### 9.4 "Deleted but open" নিজে তৈরি করুন

```bash
cd "$(mktemp -d)"
python3 -c "import time; f=open('big.log','w'); f.write('x'*50_000_000); f.flush(); time.sleep(120)" &
sleep 1
df -h .                      # ব্যবহার দেখুন
rm big.log
df -h .                      # জায়গা এখনো ফেরত আসেনি!
sudo lsof +L1 | grep big.log # (deleted) হিসেবে দেখাবে
kill %1                      # background process বন্ধ
sleep 1; df -h .             # এখন জায়গা মুক্ত
```

`&` = background-এ চালানো; `%1` = প্রথম background job। ৫০ MB-র পরিবর্তন `df`-এ ছোট দেখাতে পারে — বড় disk-এ সূক্ষ্ম পার্থক্য দেখতে `df -m` (MB-তে) ব্যবহার করুন।

> **Fedora-তে:** একই; `lsof` না থাকলে `sudo dnf install lsof`। Ubuntu-তে `sudo apt install lsof`।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_fs_explorer.py`](code/L01-03/test_fs_explorer.py)-এর ৪টি test: দীর্ঘতম FHS prefix মেলানো, relative path প্রত্যাখ্যান, sample mount table (escape ও read-only সহ), এবং hard link মুছেও data টিকে থাকা (symlink অংশ platform অনুমতি দিলে)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `fhs_lookup()`: `[p, *p.parents]` | `/var/log/nginx/x` → `/var/log/nginx` → `/var/log` → ... | দীর্ঘতম মিল আগে — `/var/log` `/var`-এর চেয়ে নির্দিষ্ট |
| `PurePosixPath` | Linux-স্টাইল path, যেকোনো OS-এ | Windows-এ চালালেও `/` দিয়ে path ভাঙে |
| `unescape()` | `\040` → space | `/proc/mounts` field space দিয়ে আলাদা, তাই path-এর space escape করা থাকে |
| `os.link()` / `os.symlink()` | `link`/`symlink` system call | `ln` ও `ln -s`-এর সমতুল্য |
| `soft.lstat()` বনাম `stat()` | `lstat` symlink নিজেকে দেখে, `stat` target-কে | Symlink-এর নিজের inode দেখতে |
| `is_symlink() and not exists()` | Dangling চেনা | `exists()` link অনুসরণ করে |
| `except (OSError, NotImplementedError)` | Symlink না পারলে skip | Platform পার্থক্যে crash নয়, স্পষ্ট বার্তা |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `ls -li` hard link-এর পরে | একই inode, link count ২ |
| Original মোছার পরে `cat hard.txt` | data আছে |
| `cat soft.txt` | `No such file or directory` |
| `findmnt --real` | `/` ও `/boot` (আপনার setup অনুযায়ী) |
| `python3 -m unittest -v` | `Ran 4 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `No space left on device` কিন্তু `df -h`-এ জায়গা আছে | Inode শেষ | `df -i` | ছোট file-এর উৎস খুঁজুন (`find /var -xdev -type f \| cut -d/ -f2-4 \| sort \| uniq -c \| sort -n \| tail`) |
| `df` পূর্ণ কিন্তু `du` কম | Deleted-but-open file | `sudo lsof +L1` | Process restart/reload; logrotate |
| `ln: failed to create hard link ... Invalid cross-device link` | ভিন্ন filesystem-এ hard link | `df file1 file2` (ভিন্ন mount?) | Symlink ব্যবহার করুন |
| Symlink কাজ করে না অন্য directory থেকে | Relative target ভুল জায়গা থেকে resolve হয় | `readlink -f link` | Target-কে link-এর directory থেকে relative লিখুন বা absolute |
| Boot-এ emergency mode | `/etc/fstab`-এ ভুল | Console-এর বার্তা | Recovery mode-এ fstab ঠিক করুন; নতুন disk-এ `nofail` (L01-18) |
| `du` মাউন্ট-করা অন্য disk গুনছে | `du` mount পেরোয় | — | `du -x` (একই filesystem-এ থাকো) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Symlink attack: shared `/tmp`-এ আক্রমণকারী symlink তৈরি করে root-কে অন্য file overwrite করাতে পারে — তাই `mktemp` ব্যবহার করুন, নিজে `/tmp/fixed-name` নয় (L04-06)।
  - `noexec`/`nosuid` mount option।
  - `/etc` ও `/var/lib`-এর backup সংবেদনশীল (password hash, key থাকে) — encrypted রাখুন।
- **Performance:** একটি directory-তে লাখ লাখ file এড়ান; log ও data আলাদা disk-এ রাখলে একটির I/O অন্যটিকে ধীর করে না।
- **Cost:** Cloud-এ disk-এর আকার অনুযায়ী বিল; log rotation ও retention সীমা না থাকলে অপ্রয়োজনে বড় disk কিনতে হয় (Module 29)।

## 14. Hands-on exercise

1. নিজের VM-এ `df -i` চালিয়ে `/`-এর inode ব্যবহার কত শতাংশ দেখুন। একটি temporary directory-তে ১০,০০০ খালি file তৈরি করে (`touch f{1..10000}`) আবার দেখুন — কতটা বাড়লো? পরে directory মুছুন।
2. `find / -xdev -type l -xtype l 2>/dev/null | head` দিয়ে system-এ dangling symlink খুঁজুন (`-xtype l` = target symlink নিজেই বা নেই)।
3. `fs_explorer.py`-তে `largest` command যোগ করুন: একটি directory-র সবচেয়ে বড় ১০টি file (`os.scandir`, symlink অনুসরণ না করে)। Test লিখুন।
4. `stat` output-এ তিনটি সময় (Access, Modify, Change) আছে। `chmod` করলে কোনটি বদলায়? `echo >>` করলে? পরীক্ষা করে লিখুন।
5. `ls -l /proc/self/fd` চালান। কী দেখছেন এবং কেন 0, 1, 2 আছে (L01-01)?

## 15. Mini-project — disk full investigator

একটি read-only Python script `disk_report.py` লিখুন যা একটি mount point নিয়ে:

1. ব্যবহৃত জায়গা ও inode-এর শতাংশ (`os.statvfs`)।
2. সবচেয়ে বড় ১০টি directory (একই filesystem-এ, `st_dev` মিলিয়ে — `du -x`-এর মতো)।
3. Linux-এ `/proc/*/fd`-এর symlink পড়ে "(deleted)" file খুঁজে (নিজের user-এর process; অন্যদের জন্য root লাগবে) — প্রতিটির PID ও size।

এটি Project 1-এর (Linux ops toolkit) `disk` subcommand-এর ভিত্তি হবে।

## 16. Interview প্রশ্ন

1. Inode কী? File-এর নাম কোথায় থাকে?
2. Hard link ও symbolic link-এর পার্থক্য কী? Hard link-এর সীমাবদ্ধতা কী?
3. `df` ও `du`-এর হিসাব না মিললে কী সন্দেহ করবেন এবং কীভাবে নিশ্চিত হবেন?
4. "No space left on device" কিন্তু disk-এ জায়গা আছে — কারণ কী?
5. `/etc/fstab`-এ device নামের বদলে UUID কেন?
6. `/var/lib` ও `/var/cache`-এর পার্থক্য কী? কোনটি backup করবেন?

## 17. Self-assessment প্রশ্ন

1. লাইব্রেরি analogy দিয়ে inode, directory, hard link ও symlink ব্যাখ্যা করুন; analogy কোথায় মেলে না?
2. `rm` আসলে কোন system call এবং কখন data সত্যিই মুক্ত হয়?
3. Section 5-এর incident-এ `rm`-এর বদলে কী করা উচিত ছিল?
4. Path resolution-এ directory-র কোন permission লাগে?
5. Script-এ `lstat` ও `stat`-এর পার্থক্য কেন গুরুত্বপূর্ণ?
6. Ubuntu ও Fedora-র default filesystem কী?

## 18. সংক্ষিপ্ত সারাংশ

- Linux-এ **একক tree** (`/`); disk ও virtual filesystem directory-তে **mount** হয়। **FHS** বলে কী কোথায়: config `/etc`, log `/var/log`, state `/var/lib`।
- **Inode** = file-এর metadata ও data-র ঠিকানা; **নাম directory-তে**।
- **Hard link** = একই inode-এর আরেক নাম (একই filesystem-এ); **symlink** = path লেখা আলাদা file, ঝুলে যেতে পারে।
- Data মুক্ত হয় link count ০ **এবং** কেউ খোলা না রাখলে — "df পূর্ণ, du কম" রহস্যের কারণ; `lsof +L1`।
- Inode শেষ হলেও disk "পূর্ণ" — `df -i`।

## 19. Completion checklist

- [ ] `findmnt`, `lsblk -f`, `df -hT`, `df -i` চালিয়ে নিজের disk layout বুঝেছি
- [ ] Hard link ও symlink তৈরি করে original মুছে আচরণ দেখেছি
- [ ] "Deleted but open" experiment করে `lsof +L1`-এ দেখেছি
- [ ] `fs_explorer.py`-এর তিনটি command চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৪টি test পাস
- [ ] Exercise ১ ও ৪ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `hier(7)` — Linux filesystem hierarchy: https://man7.org/linux/man-pages/man7/hier.7.html
- Filesystem Hierarchy Standard 3.0: https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html
- `inode(7)`: https://man7.org/linux/man-pages/man7/inode.7.html
- `ln(1)`: https://man7.org/linux/man-pages/man1/ln.1.html
- `fstab(5)`: https://man7.org/linux/man-pages/man5/fstab.5.html
- `findmnt(8)`: https://man7.org/linux/man-pages/man8/findmnt.8.html
- `lsof(8)`: https://man7.org/linux/man-pages/man8/lsof.8.html

---

**পরের lesson:** L01-04 — Users, groups, ownership ও permission
