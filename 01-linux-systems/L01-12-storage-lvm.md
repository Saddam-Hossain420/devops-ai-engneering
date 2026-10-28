# L01-12 — Storage: partition, filesystem, LVM, disk usage

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-11 — cron ও systemd timer](L01-11-scheduling-jobs.md), [L01-03 — filesystem, mount](L01-03-filesystem-hierarchy.md) |
| **Label** | 🖥️ VM · ⚠️ **DESTRUCTIVE** — partition/LVM/mkfs ভুল device-এ চালালে data মুছে যায়। এই lesson-এর lab শুধু **loop device** (একটি file-কে নকল disk বানিয়ে) ব্যবহার করে। |
| **Tested** | `storage_report.py`: ৬টি test পাস; `lsblk`, `lvm`, `forecast` নমুনা data-য় চালানো (Python 3.14, Windows)। নমুনা JSON হাতে তৈরি (lsblk/LVM-এর JSON format অনুসরণে)। **loop device, pvcreate, lvextend ইত্যাদি lab Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- Block device, partition table (**GPT** বনাম MBR), partition।
- Filesystem (ext4, xfs, btrfs) তৈরি ও mount — L01-03-এর পরের ধাপ।
- **LVM:** Physical Volume (PV) → Volume Group (VG) → Logical Volume (LV); কেন production server-এ LVM।
- চলমান অবস্থায় disk **বড় করা** (`lvextend -r`) — সবচেয়ে প্রচলিত storage কাজ।
- Disk usage: `df`, `du`, `lsblk`, `findmnt`; disk-full **পূর্বাভাস**।
- Python দিয়ে lsblk tree, LVM capacity বিশ্লেষণ ও "কবে disk পূর্ণ হবে" হিসাব।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

"Disk পূর্ণ" সম্ভবত সবচেয়ে সাধারণ production incident (L01-03)। দীর্ঘমেয়াদি সমাধানের জন্য জানতে হয়:

- নতুন disk যোগ করলে সেটি কীভাবে ব্যবহারযোগ্য করবেন?
- Database-এর partition ছোট পড়লে — downtime ছাড়া কীভাবে বাড়াবেন?
- কবে disk পূর্ণ হবে, যাতে আগেই ব্যবস্থা নেওয়া যায়?

Partition সরাসরি ব্যবহার করলে আকার বদলানো কঠিন ও ঝুঁকিপূর্ণ। **LVM** একটি নমনীয় স্তর যোগ করে: একাধিক disk একটি pool-এ, এবং সেখান থেকে প্রয়োজনমতো "volume" কাটা ও চলমান অবস্থায় বড় করা। Cloud-এ (AWS EBS, Module 08) disk বড় করার পরেও OS-এর ভেতরে এই ধাপগুলোই লাগে।

## 3. সহজ ভাষায় পরিচয়

**Block device** — byte-এর ব্লক হিসেবে পড়া-লেখা যায় এমন device: `/dev/sda` (SATA/SCSI/virtual disk), `/dev/nvme0n1` (NVMe), `/dev/vda` (KVM virtio), `/dev/loop0` (file-কে disk হিসেবে)।

**Partition** — একটি disk-কে আলাদা অংশে ভাগ; **partition table** (GPT আধুনিক, MBR পুরোনো) এই ভাগের তালিকা disk-এর শুরুতে রাখে। `/dev/sda1`, `/dev/sda2` ...; NVMe-তে `/dev/nvme0n1p1`।

**Filesystem** — একটি partition বা volume-এর ভেতরে file ও directory সাজানোর পদ্ধতি (L01-03-এর inode ইত্যাদি)। `mkfs` দিয়ে তৈরি — আগের data মুছে যায়।

**LVM-এর তিন স্তর:**

```text
 Physical Volume (PV)   = LVM-এর জন্য প্রস্তুত disk বা partition   (/dev/sdb, /dev/sda3)
          ▼  এক বা একাধিক PV মিলে
 Volume Group (VG)      = একটি storage pool                       (data-vg)
          ▼  pool থেকে কাটা
 Logical Volume (LV)    = "নমনীয় partition" — এর উপর filesystem   (/dev/data-vg/postgres)
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### জমি ও প্লট

- **Disk** = একটি জমি। **Partition** = জমিতে দেয়াল তুলে স্থায়ী ভাগ — পরে একটি ভাগ বড় করতে দেয়াল ভাঙতে হয়, পাশের ভাগ ছোট করতে হয়।
- **LVM** = সমবায় সমিতি: কয়েকটি জমি (PV) মিলে একটি বড় জমির ভাণ্ডার (VG); সদস্যরা (LV) প্রয়োজনমতো প্লট পান, দরকার হলে ভাণ্ডারের খালি অংশ থেকে প্লট বাড়ানো যায় — দেয়াল ভাঙতে হয় না। নতুন জমি কিনে (নতুন disk) ভাণ্ডারে যোগ করা যায়।
- **Filesystem** = প্লটে বাড়ি; প্লট বড় হলে বাড়িটিও বাড়াতে হয় (`resize2fs`/`xfs_growfs`) — `lvextend -r` দুটো একসাথে করে।

### Analogy কোথায় মেলে না

- জমি ভাগ করলে কোন অংশ কোথায় তা চোখে দেখা যায়। LVM-এ একটি LV-এর data **একাধিক disk-এ ছড়ানো** থাকতে পারে — একটি disk নষ্ট হলে পুরো LV (এবং তার filesystem) ক্ষতিগ্রস্ত হতে পারে। LVM নিজে redundancy নয় — RAID বা backup আলাদা দরকার।
- প্লট বড় করা সহজ, ছোট করা জমিতেও কঠিন। Filesystem **ছোট করা** আরো কঠিন: ext4 শুধু unmount অবস্থায় ছোট হয়, **xfs একেবারেই ছোট হয় না**। তাই LV শুরুতে মাঝারি আকারে রাখুন, দরকারমতো বাড়ান।

## 5. Real-world engineering scenario — "/ মাত্র ২৫ GB কেন?"

**পরিস্থিতি:** একটি নতুন Ubuntu Server VM-এ ৫০ GB disk দেওয়া হলো। কয়েক সপ্তাহ পরে alert: `/` ৯০% পূর্ণ। Engineer অবাক: `df -h`-এ `/`-এর আকার মাত্র ২৫ GB।

**তদন্ত (এই lesson-এর নমুনা data-ই এই পরিস্থিতি):**

```text
sda                          50.0 GiB  disk  -            -
├─sda1                        1.0 GiB  part  vfat         /boot/efi
├─sda2                        2.0 GiB  part  ext4         /boot
└─sda3                       46.9 GiB  part  LVM2_member  -
  └─ubuntu--vg-ubuntu--lv    25.0 GiB  lvm   ext4         /
```

```text
VG ubuntu-vg: size 46.9 GiB, free 21.9 GiB (46.7%)
```

Ubuntu Server installer প্রায়ই guided LVM setup-এ পুরো VG ব্যবহার না করে root LV ছোট রাখে (বাকিটা ভবিষ্যতের জন্য VG-তে খালি)। ফলে VG-তে ২১.৯ GiB পড়ে আছে, কেউ জানে না।

**সমাধান (downtime ছাড়া, চলমান অবস্থায়):**

```bash
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
```

**সাথে দ্বিতীয় সতর্কতা:** `data-vg` মাত্র ৫% খালি — সেখানে বাড়ানোর জায়গা নেই; নতুন disk (PV) যোগ করে VG বাড়াতে হবে (Section 9.3)।

**পূর্বাভাস:** `/`-এ ৫০ GB-এর মধ্যে ৪১ GB ব্যবহৃত, দিনে ০.৬ GB বাড়ছে → ১৫ দিনে পূর্ণ, ৬.৭ দিনে ৯০% critical। এমন সংখ্যা দিয়ে "এই সপ্তাহে ব্যবস্থা নিতে হবে" সিদ্ধান্ত সহজ হয় (Module 18 capacity planning)।

## 6. Diagram — LVM ও resize

```text
  /dev/sdb (20 GiB)    /dev/sdc (20 GiB, নতুন)
       │ pvcreate           │ pvcreate
       ▼                    ▼
   ┌──────────── VG data-vg (40 GiB) ─────────────┐
   │ [ LV postgres 15G ][ LV backups 4G ][ free ] │   vgextend data-vg /dev/sdc
   └──────────────────────────────────────────────┘
            │ lvextend -r -L +10G /dev/data-vg/postgres
            ▼
   LV postgres 25G ──► filesystem (ext4) ও বড় হলো (-r = resizefs)
            │
            ▼ mounted at /var/lib/postgresql   (L01-03)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Block device | ব্লকে পড়া-লেখা যায় এমন device (`/dev/sda`) |
| Partition table (GPT/MBR) | Disk-এর ভাগের তালিকা; GPT আধুনিক, বড় disk ও বেশি partition সমর্থন করে |
| `mkfs` | Filesystem তৈরি — ⚠️ আগের data মুছে যায় |
| PV / VG / LV | LVM-এর তিন স্তর (Section 3) |
| Physical Extent (PE) | LVM-এর ক্ষুদ্রতম বরাদ্দ একক (default ৪ MiB) |
| `lvextend -r` | LV বড় করে এবং filesystem-ও বড় করে |
| Thin provisioning | প্রকৃত ব্যবহারের অনুপাতে জায়গা নেওয়া (overcommit, সাবধানে) |
| LVM snapshot | LV-এর নির্দিষ্ট মুহূর্তের copy-on-write চিত্র (backup-এর আগে consistent অবস্থা) |
| Loop device | একটি সাধারণ file-কে block device হিসেবে দেখানো (`/dev/loop0`) |
| Device mapper | Kernel-এর স্তর যা LV-কে `/dev/mapper/vg-lv` হিসেবে দেখায় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Device naming ও স্থায়ী পরিচয়

- `/dev/sda`, `/dev/sdb` নাম **boot-এর ক্রমে** দেওয়া হয় — disk যোগ/সরালে বদলাতে পারে। তাই `/etc/fstab`-এ **UUID** (L01-03)।
- LV-র দুটি নাম: `/dev/data-vg/postgres` ও `/dev/mapper/data--vg-postgres` (device mapper-এ নামের ভেতরের `-` দ্বিগুণ হয়ে `--` — যাতে vg ও lv-এর সীমা বোঝা যায়)। নমুনার `ubuntu--vg-ubuntu--lv` এই কারণেই।

### 8.2 Filesystem বেছে নেওয়া

| Filesystem | বড় করা | ছোট করা | কোথায় default | মন্তব্য |
|---|---|---|---|---|
| ext4 | online | শুধু offline | Ubuntu | পরিপক্ক, সর্বজনীন |
| xfs | online | **সম্ভব নয়** | RHEL/Rocky | বড় file ও parallel I/O-তে ভালো |
| btrfs | online | online | Fedora Workstation | snapshot, subvolume, checksum built-in |

> **Fedora-তে:** Workstation-এ default btrfs (LVM ছাড়া, subvolume দিয়ে); Fedora Server-এ default সাধারণত LVM + xfs। `lsblk -f` দিয়ে আপনার layout দেখুন।

### 8.3 Disk বড় করার পূর্ণ শৃঙ্খল (cloud-এ সাধারণ)

1. Cloud console/API-তে disk বড় (যেমন EBS 50 → 80 GB) — OS এখনো পুরোনো আকার দেখে।
2. `lsblk` — disk নতুন আকার দেখায় কিনা; না দেখালে rescan।
3. Partition বড় করা — `growpart /dev/sda 3` (cloud-utils)।
4. PV বড় করা — `pvresize /dev/sda3`।
5. LV + filesystem — `lvextend -r -l +100%FREE ...`।

LVM ছাড়া: ধাপ ৩-এর পরে সরাসরি `resize2fs /dev/sda3` বা `xfs_growfs /mountpoint`।

### 8.4 Disk usage মাপা

- `df -h` — filesystem স্তরে (L01-03-এর deleted-but-open এখানে দেখা যায়)।
- `du -xsh /var/* | sort -h` — directory স্তরে, একই filesystem-এ (`-x`)।
- `ncdu` — interactive (install লাগে)।
- পূর্বাভাসের জন্য সময়ের সাথে মাপ জমাতে হয় — monitoring (Module 17); এই lesson-এর `forecast` হিসাবটির ভিত্তি।

## 9. Practical demonstration — loop device lab (⚠️ শুধু VM-এ, snapshot নিন)

Loop device দিয়ে আসল disk না ছুঁয়ে পুরো LVM অনুশীলন করা যায়।

### 9.1 পর্যবেক্ষণ (read-only)

```bash
lsblk -f
sudo pvs; sudo vgs; sudo lvs
df -hT
findmnt --real
```

Python tree — File: [`code/L01-12/storage_report.py`](code/L01-12/storage_report.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-12
lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS > /tmp/lsblk.json
python3 storage_report.py lsblk /tmp/lsblk.json
python3 storage_report.py lsblk sample-lsblk.json
```

**নমুনা দিয়ে আসল output:** Section 5-এ দেখানো tree (sdb ও loop0 সহ)।

> পুরোনো `lsblk` version-এ `MOUNTPOINTS` (বহুবচন) না থাকলে `MOUNTPOINT` দিন — script দুটোই সামলায়।

### 9.2 নকল disk তৈরি করে LVM

```bash
LAB=$(mktemp -d)
truncate -s 1G "$LAB/disk1.img" "$LAB/disk2.img"        # দুটি ১ GB file (sparse — আসলে প্রায় জায়গা নেয় না)
D1=$(sudo losetup -f --show "$LAB/disk1.img")            # যেমন /dev/loop10
D2=$(sudo losetup -f --show "$LAB/disk2.img")
echo "$D1 $D2"                                           # ⚠️ নিশ্চিত হোন এগুলো loop device
lsblk "$D1" "$D2"
```

**⚠️ পরের প্রতিটি command-এ `$D1`/`$D2` ব্যবহার করুন — কখনো `/dev/sda` টাইপ করবেন না।**

```bash
sudo pvcreate "$D1"
sudo vgcreate lab-vg "$D1"
sudo lvcreate -n data -L 500M lab-vg
sudo mkfs.ext4 -q /dev/lab-vg/data                        # ⚠️ শুধু নতুন LV-তে
sudo mkdir -p /mnt/labdata
sudo mount /dev/lab-vg/data /mnt/labdata
df -h /mnt/labdata                                        # ~470M (filesystem overhead বাদে)
sudo vgs lab-vg
```

### 9.3 Online বড় করা ও নতুন disk যোগ

```bash
# ১. VG-র খালি জায়গা থেকে বাড়ানো — mount থাকা অবস্থায়
sudo lvextend -r -L +300M /dev/lab-vg/data
df -h /mnt/labdata                                        # এখন ~770M

# ২. VG পূর্ণ করা এবং তারপর নতুন disk যোগ
sudo lvextend -r -l +100%FREE /dev/lab-vg/data
sudo vgs lab-vg                                           # VFree ≈ 0
sudo pvcreate "$D2"
sudo vgextend lab-vg "$D2"
sudo vgs lab-vg                                           # VFree ≈ 1G
sudo lvextend -r -l +100%FREE /dev/lab-vg/data
df -h /mnt/labdata                                        # ~1.9G — দুই "disk" জুড়ে
sudo pvs                                                  # দুটি PV, একটি VG
```

`-L +300M` = নির্দিষ্ট পরিমাণ; `-l +100%FREE` = VG-র সব খালি extent। `-r` না দিলে LV বড় হয় কিন্তু filesystem পুরোনো আকারেই থাকে — `df`-এ পরিবর্তন দেখাবে না (একটি সাধারণ বিভ্রান্তি)।

**LVM capacity — Python:**

```bash
sudo vgs --reportformat json --units b --nosuffix -o vg_name,vg_size,vg_free > /tmp/vgs.json
sudo lvs --reportformat json --units b --nosuffix -o lv_name,vg_name,lv_size > /tmp/lvs.json
python3 storage_report.py lvm /tmp/vgs.json /tmp/lvs.json
python3 storage_report.py lvm sample-vgs.json sample-lvs.json; echo "exit=$?"
```

**নমুনা দিয়ে আসল output:**

```text
VG ubuntu-vg: size 46.9 GiB, free 21.9 GiB (46.7%)
  LV ubuntu-lv    25.0 GiB
VG data-vg: size 20.0 GiB, free 1.0 GiB (5.0%)
  LV postgres     15.0 GiB
  LV backups      4.0 GiB
WARN VG data-vg has <10% free — নতুন disk (PV) যোগ বা LV ছোট করার পরিকল্পনা করুন
exit=1
```

### 9.4 Disk-full পূর্বাভাস

```bash
python3 storage_report.py forecast --size-gb 50 --used-gb 41 --growth-gb-per-day 0.6
```

**আসল output:**

```text
reach 80% (warning)  : already reached
reach 90% (critical) : 6.7 days
reach 100% (full)    : 15.0 days
```

হিসাব: ৯০% = ৪৫ GB; বাকি (৪৫ − ৪১) = ৪ GB ÷ ০.৬ GB/দিন = ৬.৬৭ দিন। ১০০%: ৯ ÷ ০.৬ = ১৫ দিন। (বাস্তবে বৃদ্ধি সরলরৈখিক নাও হতে পারে — L00-06-এর measurement নীতি: একাধিক দিনের data দিয়ে হার মাপুন।)

### 9.5 Cleanup (⚠️ ক্রম গুরুত্বপূর্ণ)

```bash
sudo umount /mnt/labdata
sudo lvremove -y lab-vg/data
sudo vgremove -y lab-vg
sudo pvremove "$D1" "$D2"
sudo losetup -d "$D1" "$D2"
rm -r "$LAB"; sudo rmdir /mnt/labdata
unset LAB D1 D2
lsblk | grep loop                                         # lab-এর loop device আর নেই
```

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_storage_report.py`](code/L01-12/test_storage_report.py)-এর ৬টি test: human-readable একক, lsblk tree (LVM সহ), LVM সারাংশ ও <১০% সতর্কতা, পূর্বাভাসের হিসাব (ইতিমধ্যে পৌঁছানো, অসীম), ভুল input, ও CLI exit code। (একটি test-এ আমার প্রত্যাশিত মান ৪৬.৮% ভুল ছিল; আসল ৪৬.৭৪৯…% → ৪৬.৭ — code সঠিক ছিল।)

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `lsblk -J -b` | JSON, byte-এ | Text output parse করার চেয়ে নির্ভরযোগ্য; একক নিজে রূপান্তর |
| `dev.get("mountpoints") or [dev.get("mountpoint")]` | নতুন ও পুরোনো lsblk | Version-নিরপেক্ষ |
| Recursive `walk()` | disk → part → lvm | `children` nested |
| `label:<26` | prefix সহ মোট প্রস্থ | Column সোজা রাখতে (প্রথম version-এ prefix-এর কারণে সরে যাচ্ছিল) |
| `vgs --reportformat json --units b --nosuffix` | যন্ত্র-পাঠযোগ্য | `20.00g` জাতীয় text parse এড়ানো |
| `days_until_full` | `(size × threshold − used) ÷ rate` | সরলরৈখিক পূর্বাভাস; rate ০ হলে `inf` |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `lvextend -r` এর পরে `df -h` | নতুন আকার, unmount ছাড়াই |
| দুই PV-র পরে `pvs` | দুটি PV, VG `lab-vg` |
| Cleanup-এর পরে `lsblk` | lab loop device নেই |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| LV বড় হলো, `df` পুরোনো আকার | filesystem resize হয়নি | `lvs` বনাম `df` | `resize2fs`/`xfs_growfs` বা ভবিষ্যতে `-r` |
| Cloud-এ disk বড় করলাম, OS দেখে না | partition বা PV বড় হয়নি | `lsblk` | `growpart` → `pvresize` → `lvextend -r` |
| `Insufficient free space` | VG-তে জায়গা নেই | `vgs` | নতুন PV + `vgextend` |
| `Device /dev/sdX excluded by a filter` | disk-এ পুরোনো signature/partition table | `sudo wipefs /dev/sdX` (শুধু দেখায়) | ⚠️ নিশ্চিত হলে `wipefs -a` (সব মুছে) |
| `umount: target is busy` | কেউ directory ব্যবহার করছে | `sudo lsof +D /mnt/labdata`, `fuser -m` | process বন্ধ, `cd` বের হন |
| xfs ছোট করতে চাই | সম্ভব নয় | — | নতুন ছোট LV-তে data copy (পরিকল্পনা আগেই) |
| ভুল device-এ `mkfs` | ⚠️ | — | Snapshot/backup থেকে restore — এজন্য প্রতিটি command-এ device দুবার যাচাই |

## 13. Security, performance ও cost বিবেচনা

- **Security:** `mkfs`, `wipefs -a`, `pvcreate` ভুল device-এ = data ধ্বংস — device নাম variable-এ রেখে আগে `lsblk` দিয়ে যাচাই। Sensitive data-র জন্য disk encryption (LUKS) — Module 19। Disk ফেলে দেওয়ার আগে নিরাপদে মুছুন।
- **Performance:** LVM-এর overhead সাধারণত নগণ্য; একাধিক PV-তে ছড়ানো LV-এর I/O পূর্বানুমেয় নাও হতে পারে; database ও log আলাদা LV/disk-এ।
- **Cost:** Cloud-এ অপ্রয়োজনীয় বড় disk-এর জন্য প্রতি মাসে বিল — ছোট শুরু করে বাড়ান (LVM ও cloud resize এটি সম্ভব করে)। পূর্বাভাস দিয়ে "জরুরি বড় করা" এড়ানো যায়।

## 14. Hands-on exercise

1. নিজের VM-এ `storage_report.py lsblk` চালিয়ে root VG-তে খালি জায়গা আছে কিনা দেখুন। থাকলে (snapshot নিয়ে) `lvextend -r -l +100%FREE` দিয়ে root বড় করুন।
2. Loop lab-এ LV-তে xfs তৈরি করে (`mkfs.xfs`; `xfsprogs` package) বড় করুন, তারপর ছোট করার চেষ্টা করুন — কী error?
3. LVM snapshot: `sudo lvcreate -s -n data-snap -L 100M lab-vg/data`, তারপর মূল LV-তে file বদলান, snapshot mount করে পুরোনো version দেখুন।
4. `storage_report.py`-তে `--json` output যোগ করুন (lvm command-এ)। Test লিখুন।
5. প্রতি ঘণ্টায় `df --output=used -B1 /` লিখে একটি CSV বানানোর systemd timer (L01-11) তৈরি করুন — কয়েক দিন পরে সেখান থেকে বৃদ্ধির হার হিসাব করে `forecast`-এ দিন।

## 15. Mini-project — disk growth runbook

[Runbook template](../templates/runbook-template.md) অনুসরণ করে `runbooks/disk-almost-full.md`-এর খসড়া আপনার notebook-এ লিখুন: alert-এর অর্থ, প্রথম ৫ মিনিটের read-only যাচাই (`df`, `df -i`, `du -x`, `lsof +L1`), নিরাপদ mitigation (log rotate, cache পরিষ্কার), LVM/cloud দিয়ে বাড়ানোর ধাপ, এবং rollback। Module 18-এ এটি চূড়ান্ত হবে।

## 16. Interview প্রশ্ন

1. PV, VG ও LV কী? LVM কেন ব্যবহার করবেন?
2. চলমান server-এ একটি filesystem কীভাবে বড় করবেন? cloud-এ disk বড় করার পরে কী কী ধাপ?
3. ext4 ও xfs-এর resize-এ পার্থক্য কী?
4. `/etc/fstab`-এ `/dev/sdb1` কেন নয়?
5. LVM কি redundancy দেয়?
6. Disk কবে পূর্ণ হবে কীভাবে অনুমান করবেন?

## 17. Self-assessment প্রশ্ন

1. জমি-সমবায় analogy কোথায় মেলে না?
2. Section 5-এর দুটি সমস্যা ও সমাধান।
3. `ubuntu--vg-ubuntu--lv`-এ `--` কেন?
4. `lvextend` ও `lvextend -r`-এর পার্থক্য।
5. Loop device কেন lab-এর জন্য নিরাপদ?
6. Forecast-এ ৯০%-এ পৌঁছানোর হিসাব হাতে দেখান।

## 18. সংক্ষিপ্ত সারাংশ

- Block device → partition (GPT) → filesystem → mount; নাম নয়, UUID।
- **LVM**: PV → VG (pool) → LV; online বড় করা, নতুন disk যোগ; কিন্তু redundancy নয়।
- `lvextend -r` = LV + filesystem; cloud-এ growpart → pvresize → lvextend।
- ext4 online বড়, offline ছোট; **xfs ছোট হয় না**; Fedora Workstation btrfs।
- Disk-এর **পূর্বাভাস** দিয়ে আগে থেকে ব্যবস্থা; ⚠️ destructive command-এ device দুবার যাচাই।

## 19. Completion checklist

- [ ] `lsblk -f`, `pvs/vgs/lvs`, `df -hT` দিয়ে নিজের layout বুঝেছি
- [ ] Loop device lab: PV, VG, LV, mkfs, mount
- [ ] Online `lvextend -r` ও নতুন PV যোগ করে বড় করেছি
- [ ] Cleanup সম্পন্ন, loop device মুক্ত
- [ ] `storage_report.py`-এর তিনটি command চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `lvm(8)`: https://man7.org/linux/man-pages/man8/lvm.8.html
- `lvextend(8)`: https://man7.org/linux/man-pages/man8/lvextend.8.html
- `lsblk(8)`: https://man7.org/linux/man-pages/man8/lsblk.8.html
- `losetup(8)`: https://man7.org/linux/man-pages/man8/losetup.8.html
- Ubuntu Server — storage / LVM: https://documentation.ubuntu.com/server/
- Fedora — btrfs: https://docs.fedoraproject.org/en-US/quick-docs/
- Red Hat — Configuring and managing logical volumes (LVM-এর বিস্তারিত গাইড): https://docs.redhat.com/

---

**পরের lesson:** L01-13 — SSH, SSH key, agent forwarding ও নিরাপদ remote access
