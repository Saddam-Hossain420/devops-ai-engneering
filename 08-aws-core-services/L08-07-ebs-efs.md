# L08-07 — EBS ও EFS

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L08-06 — EC2](L08-06-ec2.md), [L01-12 — Storage ও LVM](../01-linux-systems/L01-12-storage-lvm.md), [L05-12 — Backup যাচাই](../05-python-for-infrastructure/L05-12-healthcheck-backup-verify.md) |
| **Label** | 💰 EBS volume (provisioned GiB, attach না থাকলেও), snapshot (stored GiB) ও EFS (ব্যবহৃত GiB, throughput mode অনুযায়ী) — সবই চার্জযোগ্য; pricing page দেখুন |
| **Tested** | `ebs_audit.py` ও `fstab_lint.py`: ৬টি test পাস (Python 3.14.5, Windows)। Input **হাতে তৈরি** — `describe-volumes`/`describe-snapshots`-এর রূপে, এবং একটি নমুনা `/etc/fstab`। EFS-এর NFS option-এর তালিকা AWS EFS documentation-এর সুপারিশ অনুযায়ী। **আসল EC2-এ volume attach, mount বা reboot পরীক্ষা করা হয়নি।** |

---

## 1. এই lesson-এ যা শিখবেন

- EBS: একটি AZ-এর network block device; volume type (gp3, gp2, io2, st1); snapshot; encryption।
- Volume attach → partition/format → mount → `fstab`; online resize।
- **Nitro instance-এ device-এর নাম** — কেন `/dev/xvdf` লিখলে বিপদ, আর কেন `nofail` বাধ্যতামূলক।
- EFS: বহু-AZ, বহু-instance shared NFS; mount target ও security group; `hard` বনাম `soft`।
- Instance store: দ্রুত, কিন্তু stop করলে হারায়।
- `ebs_audit.py` (খরচ ও encryption) ও `fstab_lint.py` (boot-নিরাপত্তা)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

TaskFlow-এর SQLite file root volume-এ আছে (L08-06)। এতে কয়েকটি প্রশ্ন ওঠে:

- Instance terminate হলে data কোথায় থাকবে?
- Backup কীভাবে নেবেন?
- দুটি instance একই upload file দেখবে কীভাবে?

আর পরিচিত দুর্ঘটনা:

- `/etc/fstab`-এ `/dev/xvdf`, `nofail` ছাড়া। Volume detach হয়ে গেল বা নাম বদলাল; reboot-এর পরে instance emergency mode-এ আটকে গেল। SSH নেই, console keyboard নেই।
- পরীক্ষার পরে ২০০ GiB volume detach করা হলো, মোছা হলো না — বিল চলতে থাকল।
- Encrypt-না-করা volume-এর snapshot ভুল করে public share হলো।

## 3. সহজ ভাষায় পরিচয়

| Storage | কী | পরিধি | কয়টি instance | Linux-এ দেখায় |
|---|---|---|---|---|
| EBS | Network block device | **একটি AZ** | সাধারণত ১টি (io1/io2-এ multi-attach ব্যতিক্রম) | `/dev/nvme1n1` (Nitro) |
| Instance store | Host-এর local disk | Instance | ১টি | `/dev/nvme…` — **stop করলে মুছে যায়** |
| EFS | Managed NFS (v4.1) | Region (প্রতি AZ-এ mount target) | হাজার | `fs-…:/` NFS mount |
| S3 | Object storage (L08-08) | Region | যেকোনো client | Filesystem নয় |

| EBS type | বৈশিষ্ট্য | কখন |
|---|---|---|
| gp3 | IOPS ও throughput আকার থেকে আলাদা করে ঠিক করা যায় | ডিফল্ট পছন্দ |
| gp2 | IOPS আকারের সাথে বাড়ে, burst credit | পুরোনো; gp3-এ বদলান |
| io2 | উচ্চ, স্থির IOPS | Database-এর কঠিন চাহিদা |
| st1 / sc1 | HDD, throughput-ভিত্তিক | Log, বড় sequential data |

**Linux-এর তুলনা (L01-12):** EBS = একটি নতুন disk; সেই একই `lsblk` → `mkfs` → `mount` → `fstab`। Local-এ loop device দিয়ে অনুশীলন করা যায় (Section 9.1)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### Pen drive বনাম শেয়ার করা network folder

- **EBS** = একটি pen drive — একবারে এক computer-এ লাগে, অন্য ঘরে (AZ) নেওয়া যায় না।
- **Snapshot** = pen drive-এর ছবি তুলে লকারে রাখা; সেখান থেকে যেকোনো ঘরে নতুন pen drive বানানো যায়।
- **EFS** = অফিসের shared folder — সব ঘর থেকে একসাথে।

### Analogy কোথায় মেলে না

- **Pen drive লাগালেই নাম একই থাকে।** Nitro instance-এ EBS NVMe device হিসেবে আসে (`/dev/nvme1n1`), আর একাধিক volume-এর ক্রম boot-ভেদে বদলাতে পারে। Console-এ দেওয়া `/dev/sdf` নামটি OS-এ ওই নামে নাও থাকতে পারে। তাই `fstab`-এ `UUID=`।
- **Pen drive না থাকলে computer চালু হয়।** `fstab`-এ `nofail` ছাড়া একটি volume না পেলে systemd boot থামিয়ে emergency shell দেয়। Cloud-এ সেই shell-এ পৌঁছানোর keyboard নেই, তাই instance অচল (L01-18-এর recovery এখানে অনেক কঠিন)।
- **ছবি তুলতে পুরো জিনিস copy হয়।** Snapshot incremental — প্রথমটি পূর্ণ, পরেরগুলো শুধু পরিবর্তিত block। আর restore করা volume প্রথমবার পড়ার সময় ধীর (lazy load)।

## 5. Real-world engineering scenario — "Reboot-এর পরে instance আর ফিরল না"

TaskFlow-এর upload-এর জন্য একটি data volume যোগ হলো। Engineer console-এ device `/dev/sdf` দেখে `fstab`-এ লিখলেন `/dev/xvdf /data ext4 defaults 0 2`। সব চলল, কারণ mount হাতে করা ছিল। এক মাস পরে kernel update-এর reboot (L01-18): instance status check ব্যর্থ, ALB-এ unhealthy।

`get-console-output`-এ দেখা গেল: `Timed out waiting for device /dev/xvdf` → `You are in emergency mode`।

`fstab_lint.py`-এর আসল output (নমুনা `fstab`):

```text
line 4   ERROR  /data: device name /dev/xvdf — on Nitro instances names/order can change; use UUID= (blkid) or LABEL=
line 4   ERROR  /data: no 'nofail' — if this volume is missing the instance stops in emergency mode and never becomes reachable
line 6   WARN   /shared: no _netdev — systemd infers it from the nfs type, but AWS recommends it for EFS
line 6   ERROR  /shared: 'soft' — on a timeout writes can fail silently; use 'hard'
line 6   WARN   /shared: NFS options missing rsize=1048576, wsize=1048576, retrans=2, noresvport (AWS-recommended set)
line 6   INFO   /shared: consider 'nofail' so an EFS outage does not block boot
line 7   INFO   /uploads: consider 'nofail' so an EFS outage does not block boot
3 error(s), 4 other finding(s)
```

**Recovery:** instance stop → root volume detach → অন্য একটি instance-এ attach → `fstab` ঠিক → ফেরত attach → start। এক ঘণ্টার কাজ।

**প্রতিরোধ:** `fstab_lint.py` user data বা CI-তে।

## 6. Diagram

```text
 AZ a                                              Region
 ┌──────────────────────────────┐        ┌───────────────────────────┐
 │ EC2 i-app-a                  │        │ S3 (AWS-managed)          │
 │  /dev/nvme0n1 ← vol-root     │──snap─►│  snap-nightly (incremental)│──copy──► অন্য region
 │  /dev/nvme1n1 ← vol-data     │        └───────────────────────────┘
 │  /shared ── NFS 2049 ──┐     │                    │ restore (যেকোনো AZ-এ নতুন volume)
 └────────────────────────┼─────┘                    ▼
                          ▼
              EFS fs-0123 mount target (AZ a) ── একই filesystem ── mount target (AZ b) ◄── i-app-b
              sg-efs: inbound 2049 from sg-app
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Volume | EBS-এর একটি network disk, AZ-নির্দিষ্ট |
| Snapshot | Volume-এর point-in-time, incremental copy (S3-এ, AWS-পরিচালিত) |
| IOPS / throughput | প্রতি সেকেন্ডে I/O সংখ্যা / MiB |
| Elastic Volumes | Online-এ আকার বা type বদল |
| Mount target | একটি AZ-এ EFS-এর network endpoint (ENI, SG) |
| `hard` / `soft` | NFS server সাড়া না দিলে চিরকাল চেষ্টা / সময় পেরোলে error |
| `nofail` | Device না পেলেও boot চলবে |
| `_netdev` | Network filesystem — network-এর পরে mount |
| Lazy loading | Snapshot থেকে restore-এর পরে প্রথম read S3 থেকে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Nitro ও NVMe নাম

Nitro instance-এ EBS NVMe controller দিয়ে আসে।

- Ubuntu-তে `/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol…` symlink-এ volume id থাকে — কোন disk কোন volume, তা এখান থেকে নিশ্চিত হন।
- Filesystem-এর UUID (`blkid`) volume-এর সাথেই থাকে, তাই `fstab`-এর জন্য সবচেয়ে নিরাপদ।

### 8.2 Resize

```bash
aws ec2 modify-volume --volume-id vol-… --size 20      # online
# instance-এ:
sudo growpart /dev/nvme1n1 1      # partition থাকলে
sudo resize2fs /dev/nvme1n1p1     # ext4;  xfs-এ: sudo xfs_growfs /data
```

আকার শুধু বাড়ানো যায়, কমানো যায় না।

### 8.3 Snapshot ও backup

- Snapshot crash-consistent। Database-এর জন্য app-স্তরের backup, বা freeze/flush (L05-12-এর মতো যাচাইসহ) ভালো।
- নিয়মিত snapshot-এর জন্য Data Lifecycle Manager বা AWS Backup।
- Restore করে যাচাই না করা backup, backup নয়।

### 8.4 EFS

- Regional; প্রতিটি AZ-এ mount target, প্রতিটির SG-তে client-এর SG থেকে TCP 2049।
- `amazon-efs-utils`-এর `efs` mount type দিলে `tls` (in-transit encryption) ও `iam` সহজ হয়। Ubuntu-তে এই package build বা install করতে হতে পারে — AWS documentation দেখুন।
- সাধারণ NFS client দিয়ে mount করলে AWS-এর সুপারিশ: `nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport`।
- `soft` mount-এ timeout হলে write নীরবে ব্যর্থ হতে পারে, তাই data নষ্টের ঝুঁকি।

> **Fedora-তে:** `nfs-utils` (Ubuntu-তে `nfs-common`); `growpart` আসে `cloud-utils-growpart` package-এ (Ubuntu-তে `cloud-guest-utils`)। বাকি command একই।

## 9. Practical demonstration

Files:

- [`code/L08-07/ebs_audit.py`](code/L08-07/ebs_audit.py), [`fstab_lint.py`](code/L08-07/fstab_lint.py)
- [`sample/`](code/L08-07/sample/) — volumes, snapshots, encryption-default, fstab (হাতে তৈরি)
- [`test_l08_07.py`](code/L08-07/test_l08_07.py)

### 9.1 Local অনুশীলন — loop device (Ubuntu VM-এ; এখানে চালানো হয়নি)

```bash
truncate -s 1G ~/fake-ebs.img
LOOP=$(sudo losetup --find --show ~/fake-ebs.img)
sudo mkfs.ext4 -L fakedata "$LOOP"
sudo mkdir -p /mnt/fakedata
echo "LABEL=fakedata /mnt/fakedata ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
python3 fstab_lint.py /etc/fstab
sudo mount -a && df -h /mnt/fakedata
# পরিষ্কার: fstab থেকে লাইন মুছুন → sudo umount /mnt/fakedata → sudo losetup -d "$LOOP" → rm ~/fake-ebs.img
```

`nofail` সরিয়ে loop device detach করে reboot করলে কী হয়? শুধু snapshot-সহ VM-এ চেষ্টা করুন (L00-07)।

### 9.2 EBS audit — আসল output (হাতে তৈরি নমুনায়)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-07
python3 ebs_audit.py sample/volumes.json sample/snapshots.json \
  --encryption-default sample/encryption-default.json --today 2026-10-28; echo "exit=$?"
```

```text
CRITICAL  vol-data-old         100 GiB not encrypted — data at rest unprotected; snapshot → copy with --encrypted → new volume
WARN      account              EBS encryption by default is off in this region — aws ec2 enable-ebs-encryption-by-default
WARN      snap-before-upgrade  snapshot not encrypted — and it could be shared publicly by mistake
WARN      snap-before-upgrade  286 days old, source volume vol-0deleted no longer exists — 50 GiB billed (incremental); still needed?
WARN      vol-forgotten        200 GiB not attached to anything (created 119 days ago) — billed; snapshot if needed, then delete
WARN      vol-forgotten        no Project tag — cleanup and cost reports cannot attribute it
INFO      snap-ami-base        269 days old, backs an AMI — deregister the AMI first if it is unused
INFO      vol-data-old         gp2 — gp3 decouples IOPS/throughput from size and is often cheaper per GiB; modify-volume --volume-type gp3 works online (check pricing)
INFO      vol-data-old         DeleteOnTermination=false on i-app-a — survives terminate
3 volume(s), 3 snapshot(s): 1 critical; 200 GiB in unattached volumes
exit=1
```

AMI-র snapshot-কে "অনাথ" বলা হয় না — AMI থাকলে snapshot মোছা যায় না (test-এ যাচাই)।

### 9.3 আপনার account-এ (চালানো হয়নি)

```bash
aws ec2 get-ebs-encryption-by-default > encryption-default.json
aws ec2 enable-ebs-encryption-by-default          # region-প্রতি; নতুন volume encrypted হয়
aws ec2 describe-volumes > volumes.json
aws ec2 describe-snapshots --owner-ids self > snapshots.json
python3 ebs_audit.py volumes.json snapshots.json --encryption-default encryption-default.json

# data volume (💰): instance-এর AZ-এই
AZ=$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)
VOL=$(aws ec2 create-volume --availability-zone "$AZ" --size 1 --volume-type gp3 --encrypted \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=Project,Value=lab08}]' --query VolumeId --output text)
aws ec2 wait volume-available --volume-ids "$VOL"
aws ec2 attach-volume --volume-id "$VOL" --instance-id "$IID" --device /dev/sdf
aws ec2 create-snapshot --volume-id "$VOL" --description lab08 \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Project,Value=lab08}]'
```

Instance-এর ভেতরে (Session Manager থাকলে): `lsblk`, `ls -l /dev/disk/by-id/ | grep Elastic`, তারপর Section 9.1-এর মতো `mkfs` ও `UUID=…,nofail`।

**Cleanup:**

1. `umount`।
2. `detach-volume`।
3. `delete-volume`।
4. `delete-snapshot`।
5. `ebs_audit.py`-এ `0 GiB in unattached volumes`।

### 9.4 লেখার সময়

- প্রথম সংস্করণ `nfs4` mount-এ `_netdev` না থাকাকে ERROR দিত ("network-এর আগে mount")। কিন্তু systemd `nfs`/`nfs4` type দেখে নিজেই network filesystem হিসেবে চেনে, তাই দাবিটা ভুল ছিল। এখন `nfs4`-এ WARN (AWS-এর সুপারিশ), আর `efs` type-এ ERROR।
- এই lesson-এর code-এ test নতুন কোনো bug পায়নি।

### 9.5 Test

```bash
python3 -m unittest -v
```

৬টি test:

- EBS নমুনা (ভালো volume ও snapshot পরিষ্কার)।
- AMI-র snapshot অনাথ নয়।
- বয়সের সীমা ও `Z` timestamp।
- fstab নমুনা।
- সঠিক লাইন পরিষ্কার।
- `efs` type ও NVMe নাম।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `State == available` | Attach না থাকা volume | সবচেয়ে সাধারণ অপচয় |
| Snapshot-এর source volume নেই + পুরোনো | অনাথ প্রার্থী | মোছার আগে মানুষের সিদ্ধান্ত |
| `CreateImage` description | AMI-র snapshot আলাদা | ভুল পরামর্শ নয় |
| `day()`-এ `Z` → `+00:00` | Timestamp-এর দুই রূপ | CLI ও SDK |
| `RAW_DEVICE` regex | `/dev/xvd*`, `/dev/sd*`, `/dev/nvme*` | Nitro-তে অস্থির নাম |
| System mount বাদ | `/`, `/boot/efi` | AMI-র নিজের লাইন ঠিক |
| `hard`/`soft` | Data-নিরাপত্তা | `soft` = নীরব ব্যর্থতা |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় `ebs_audit.py` | ১ critical, ২০০ GiB unattached, exit ১ |
| নমুনায় `fstab_lint.py` | ৩ error, exit ১ |
| নিজের instance-এর `/etc/fstab` | ০ error |
| Lab-এর পরে audit | `0 GiB in unattached volumes`, Project-এর snapshot নেই |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `attach-volume`: `InvalidVolume.ZoneMismatch` | Volume অন্য AZ-এ | Snapshot → সঠিক AZ-এ নতুন volume |
| Reboot-এর পরে instance অচল | `fstab`-এ `nofail` নেই বা ভুল device | Section 5-এর recovery; lint |
| Volume বড় করলেও `df` আগের মতো | Filesystem resize হয়নি | `growpart` + `resize2fs`/`xfs_growfs` |
| Restore করা DB প্রথমে খুব ধীর | Lazy loading | `fio`/`dd` দিয়ে আগে পড়ে নেওয়া, বা fast snapshot restore (চার্জযোগ্য) |
| EFS mount timeout | Mount target-এর SG-তে 2049 নেই, বা সেই AZ-এ mount target নেই | `sg_reach.py --port 2049` |
| `Stale file handle` / hang | `soft`, বা network-এর ঘটনা | `hard,noresvport` |
| Snapshot মোছা যায় না | AMI ব্যবহার করছে | `deregister-image` আগে |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Region-এ default encryption চালু রাখুন।
  - Snapshot কখনো public নয় — account-স্তরে "block public access for snapshots" setting আছে, documentation দেখুন।
  - EFS-এ `tls`।
  - EFS-এর SG-তে শুধু app SG থেকে 2049।
- **Performance:**
  - gp3-এ IOPS ও throughput আলাদাভাবে বাড়ানো যায়।
  - Instance type-এরও EBS bandwidth সীমা আছে।
  - EFS-এ ছোট ছোট অনেক file-এর metadata ধীর হতে পারে।
- **Cost:**
  - Volume provisioned GiB-এ বিল হয়, ব্যবহারে নয়।
  - Snapshot জমে।
  - EFS ব্যবহৃত GiB ও throughput mode অনুযায়ী।
  - নিয়মিত `ebs_audit.py` (L08-12-এর cleanup-এর input)।

## 14. Hands-on exercise

1. Section 9.1-এর loop device অনুশীলন একটি Ubuntu VM-এ করুন, `fstab_lint.py`-এ ০ error।
2. Section 9.3: 1 GiB volume বানিয়ে attach, format, `UUID=…,nofail` mount, snapshot, তারপর সম্পূর্ণ cleanup।
3. Snapshot থেকে অন্য AZ-এ volume বানিয়ে data আছে কিনা যাচাই করুন (L05-12-এর নীতি: restore-test)।
4. `ebs_audit.py`-তে নতুন নিয়ম: gp3-এ IOPS > 3000 বা throughput > 125 হলে INFO — "baseline-এর বেশি কেনা; সত্যিই দরকার?"
5. `fstab_lint.py`-তে `x-systemd.device-timeout=` option চিনতে শিখান: `nofail` থাকলে timeout ছোট রাখার পরামর্শ।

## 15. Mini-project — TaskFlow-এর data volume

TaskFlow-এর SQLite file root volume থেকে আলাদা একটি encrypted gp3 volume-এ সরান:

- user data-য় `UUID=…,nofail` mount;
- systemd unit-এ `RequiresMountsFor=/data`;
- রাতের snapshot (DLM);
- restore-test script।

Instance বদলালে data volume নতুন instance-এ যাবে (একই AZ)। পরের ধাপে managed database কেন ভালো, তার যুক্তি লিখুন।

## 16. Interview প্রশ্ন

1. EBS, instance store ও EFS-এর পার্থক্য কী? কখন কোনটা?
2. EBS volume কেন অন্য AZ-এর instance-এ attach করা যায় না? কীভাবে সরাবেন?
3. Snapshot incremental — এর মানে কী? মুছলে কী হয়?
4. `fstab`-এ `nofail` ও `UUID=` কেন?
5. gp2 থেকে gp3-এ কেন যাবেন?
6. EFS-এ `soft` mount কেন বিপজ্জনক?

## 17. Self-assessment প্রশ্ন

1. Pen-drive analogy কোথায় মেলে না?
2. Section 5-এর recovery-র ধাপগুলো কী?
3. AMI-র snapshot কেন মোছা যায় না?
4. Volume বড় করার পরে OS-এ কী করতে হয়?
5. EFS mount target-এর SG-তে কী নিয়ম লাগে?

## 18. সংক্ষিপ্ত সারাংশ

- EBS: AZ-নির্দিষ্ট, একটি instance, snapshot-এ backup, ডিফল্টে encrypted রাখুন, gp3।
- `fstab`: `UUID=` ও `nofail` — নইলে reboot-এ instance হারাতে পারেন।
- EFS: shared NFS, প্রতি AZ-এ mount target, `hard` ও `tls`।
- Detach মানে মোছা নয় — `ebs_audit.py` দিয়ে unattached volume ও পুরোনো snapshot খুঁজুন।

## 19. Completion checklist

- [ ] Loop device অনুশীলন শেষ, `fstab_lint.py`-এ ০ error
- [ ] Region-এ EBS default encryption চালু
- [ ] Lab-এর volume ও snapshot মুছে audit পরিষ্কার
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Amazon EBS — What is Amazon EBS: https://docs.aws.amazon.com/ebs/latest/userguide/what-is-ebs.html
- Amazon EBS — Volume types: https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html
- Amazon EBS — Snapshots: https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html
- Amazon EBS — NVMe volumes: https://docs.aws.amazon.com/ebs/latest/userguide/nvme-ebs-volumes.html
- Amazon EFS — What is Amazon EFS: https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html
- Amazon EFS — Mounting file systems: https://docs.aws.amazon.com/efs/latest/ug/mounting-fs.html

---

**পরের lesson:** L08-08 — S3
