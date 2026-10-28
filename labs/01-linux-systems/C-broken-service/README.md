# Lab 01-C — Broken service: diagnose and recover

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট (লক্ষ্য: diagnosis + fix ১৫ মিনিট — Milestone 1) |
| **Environment** | Ubuntu VM (systemd), **snapshot বাধ্যতামূলক** |
| **Label** | ⚠️ system user `labc`, unit `lab-c.service`, `/etc/lab-c`, `/srv/lab-c` ও একটি 1 MiB tmpfs তৈরি করে — `reset.sh` সব মোছে |

## Objective

একটি service-এ **স্তরে স্তরে লুকানো তিনটি সমস্যা** — বাস্তব incident-এর মতো একটি ঠিক করলে পরেরটি দেখা দেয় — শুধু প্রমাণ (journal, status, permission, disk) দিয়ে খুঁজে বের করে **least-privilege** উপায়ে ঠিক করা। `chmod 777`, root হিসেবে চালানো বা AppArmor বন্ধ করা নিষেধ।

## Prerequisites

- Lesson: [L01-03](../../../01-linux-systems/L01-03-filesystem-hierarchy.md), [L01-04](../../../01-linux-systems/L01-04-users-permissions.md), [L01-10](../../../01-linux-systems/L01-10-systemd-services.md), [L01-12](../../../01-linux-systems/L01-12-storage-lvm.md), [L01-14](../../../01-linux-systems/L01-14-logs-and-debugging.md)
- [Troubleshooting methodology](../../../troubleshooting/methodology.md)

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/01-linux-systems/C-broken-service
sudo bash break-it.sh --yes-i-am-in-a-vm
```

Files: [`break-it.sh`](break-it.sh), [`app.py`](app.py), [`check.sh`](check.sh), [`reset.sh`](reset.sh)। **Script খোলার আগে নিজেকে চ্যালেঞ্জ দিন — না পড়ে diagnose করুন।** (Script পড়ে ফেললে উত্তর জেনে যাবেন; বাস্তবে কেউ আপনাকে "কী ভাঙা হয়েছে" বলে দেয় না।)

## Steps

1. Timer চালু করুন (notebook-এ সময় লিখুন)।
2. **Symptom:** `systemctl status lab-c --no-pager` — কী অবস্থা, কোন exit status?
3. **Evidence:** `journalctl -u lab-c -n 30 --no-pager` — error message কী বলছে?
4. প্রতিটি সমস্যার জন্য L00-06-এর loop: hypothesis → read-only test (`ls -l`, `namei -l`, `sudo -u labc ...`, `df -h`, `findmnt`, `du`) → fix → `sudo systemctl restart lab-c` → আবার journal।
5. তিনটি সমস্যা ঠিক হলে যাচাই:

   ```bash
   sudo bash check.sh
   ```

6. Timer থামান; notebook-এ incident report ([template](../../../templates/incident-report-template.md)) — timeline, প্রতিটি সমস্যার প্রমাণ, fix ও কেন সেটি least-privilege।

## Expected behavior

- প্রথমে service চালুই হয় না; প্রতিটি fix-এর পরে নতুন ধরনের error।
- সব ঠিক হলে `check.sh`: `ALL CHECKS PASSED`, exit 0; heartbeat প্রতি ২ সেকেন্ডে বাড়ে।

## Verification

```bash
sudo bash check.sh; echo "exit=$?"            # 0
systemctl show -p NRestarts lab-c              # fix-এর সময় কতবার restart হয়েছিল
journalctl -u lab-c --since "5 min ago" | tail -3
```

## Troubleshooting (সূত্র — আটকে গেলে একটি একটি করে খুলুন)

<details><summary>সূত্র ১</summary>

`status=203/EXEC` — systemd program-টি **চালাতেই** পারেনি। File আছে কি? চালানোর অধিকার আছে কি? (L01-04, L01-06-এর exit 126)
</details>

<details><summary>সূত্র ২</summary>

App বলছে config পড়তে পারছে না। Service কোন user হিসেবে চলে? সেই user হিসেবে পরীক্ষা: `sudo -u labc cat /etc/lab-c/config.ini`। সমাধান কি file-কে সবার জন্য খোলা, নাকি শুধু সঠিক group-কে পড়ার অধিকার?
</details>

<details><summary>সূত্র ৩</summary>

`No space left on device` — কিন্তু `/` তো খালি? কোন filesystem-এ লেখা হচ্ছে: `findmnt --target /srv/lab-c/data`, `df -h /srv/lab-c/data`, `du -sh /srv/lab-c/data/*`। কোন file জায়গা নিচ্ছে এবং সেটি কি দরকারি?
</details>

## Cleanup / reset

```bash
sudo bash reset.sh --yes-i-am-in-a-vm
systemctl status lab-c 2>&1 | head -2            # "could not be found"
```

আবার অনুশীলন করতে: `break-it.sh` আবার চালান (script idempotent-ভাবে সব তৈরি করে)।

## Assessment

1. প্রতিটি সমস্যার জন্য: symptom, প্রমাণ (আসল command ও output), কারণ, fix।
2. Config সমস্যায় আপনার fix কীভাবে least privilege মানে? `chmod 644` বা `777` কেন খারাপ বিকল্প?
3. Disk সমস্যায় `df -h /` কেন বিভ্রান্তিকর ছিল?
4. কোন সমস্যা monitoring (Module 17) আগে থেকেই ধরতে পারত, কীভাবে?
5. মোট সময় কত লাগল? ১৫ মিনিটের লক্ষ্য পূরণ না হলে কোন ধাপে সময় গেল?
