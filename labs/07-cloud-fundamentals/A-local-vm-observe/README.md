# Lab 07-A — Local VM তৈরি ও পর্যবেক্ষণ

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৯০ মিনিট (ISO/image download ছাড়া) |
| **Environment** | আপনার নিজের computer (host) + একটি Ubuntu VM (guest) — VirtualBox, KVM/virt-manager, Hyper-V বা Multipass |
| **Label** | 🖥️ VM — host-এ virtualization software install ও কয়েক GB disk লাগে; কোনো cloud খরচ নেই |
| **Tested** | `check_a.py` Windows-এ যাচাই করা: host দিক এই laptop-এর আসল `virt_probe.py --json` output; guest দিক একটি নকল DMI tree (QEMU) থেকে `virt_probe.py --root` দিয়ে বানানো — **আসল VM-এ চালানো হয়নি**। সঠিক input-এ ALL PASS; host-কে guest হিসেবে দিলে ও ভুল vCPU/snapshot-এ ৬টি FAIL। |

## Objective

নিজের machine-এ একটি VM বানিয়ে L07-01-এর ধারণাগুলো চোখে দেখা:

- Guest নিজেকে কীভাবে VM হিসেবে চেনে (DMI, cpuinfo-র `hypervisor` flag)।
- vCPU ও RAM ভাগাভাগির অনুপাত (overcommit)।
- Load-এর সময় CPU steal।
- Snapshot নেওয়া ও তাতে ফেরা।

এগুলো পরে cloud instance বোঝার ভিত্তি — cloud-এর VM-ও একই প্রযুক্তি, শুধু অন্য কারও hardware-এ।

## Prerequisites

- [L07-01 — Virtualization ও hypervisor](../../../07-cloud-fundamentals/L07-01-virtualization-hypervisor.md)
- Host-এ BIOS/UEFI-তে hardware virtualization (Intel VT-x / AMD-V) চালু
- কমপক্ষে ৮ GB RAM ও ২৫ GB খালি disk

## Environment setup

যেকোনো একটি tool বেছে নিন:

| Host | Tool | মন্তব্য |
|---|---|---|
| Ubuntu | KVM + virt-manager (`sudo apt install virt-manager`) | Linux-এ native |
| Fedora | KVM + virt-manager (`sudo dnf install virt-manager`) | একই |
| Windows Pro | Hyper-V Manager (Windows feature) | Hyper-V চালু থাকলে VirtualBox ধীর হতে পারে |
| যেকোনো | VirtualBox | Windows-এ Hyper-V-এর সাথে বিরোধ হতে পারে |
| যেকোনো | Multipass | Ubuntu image নিজে download করে; দ্রুততম |

> **Fedora-তে:** host Fedora হলে উপরের `dnf` লাইন; guest Ubuntu-ই রাখুন।

Ubuntu Server ISO শুধু অফিসিয়াল উৎস থেকে download করুন এবং checksum মেলান (L01)।

```bash
mkdir -p ~/lab07a
```

Repo-টি guest-এও লাগবে (git clone, বা shared folder, বা শুধু `virt_probe.py` copy)।

File: [`check_a.py`](check_a.py)।

## Steps

1. **Host পরিমাপ** (host-এ):

   ```bash
   python3 07-cloud-fundamentals/code/L07-01/virt_probe.py --json > ~/lab07a/host.json
   ```

   Host নিজেই VM হলে (`"virtualized": true`) — nested virtualization। চলবে, কিন্তু `observations.json`-এ `"nested_note"` লিখুন।

2. **VM তৈরি:** Ubuntu Server, **২ vCPU, ৪ GB RAM**, ২০ GB disk। Install শেষে update করুন।

3. **Snapshot:** পরিষ্কার VM-এর snapshot নিন (নাম `clean`)।

4. **Guest পরিমাপ** (VM-এর ভেতরে):

   ```bash
   python3 virt_probe.py --json > guest.json
   systemd-detect-virt          # তুলনার জন্য
   grep -c hypervisor /proc/cpuinfo
   ```

   `guest.json` host-এর `~/lab07a/`-এ আনুন (scp, shared folder, বা copy-paste)।

5. **Steal — idle অবস্থায়** (guest-এ): `python3 virt_probe.py steal 10`।

6. **Steal — load-এ** (guest-এ):

   ```bash
   for i in 1 2; do yes > /dev/null & done
   python3 virt_probe.py steal 10
   kill %1 %2
   ```

   Steal স্পষ্ট দেখতে চাইলে একই সময়ে host-কেও ব্যস্ত রাখুন (অন্য VM, বা host-এ build)। হালকা host-এ steal প্রায় ০ থাকতে পারে — সেটাও একটি পর্যবেক্ষণ।

7. **Overcommit:** host-এর logical CPU সংখ্যা (`host.json`-এর `logical CPUs`) ও RAM দিয়ে:

   ```bash
   python3 virt_probe.py overcommit --host-cores 12 --vcpus 2 --host-ram-gb 32 --vm-ram-gb 4
   ```

   (সংখ্যাগুলো নিজের machine-এর দিন। একাধিক VM চললে সবগুলোর vCPU ও RAM যোগ করুন।)

8. **`~/lab07a/observations.json`:**

   ```json
   {
     "vm_tool": "virt-manager",
     "host_cores": 12,
     "host_ram_gb": 32,
     "vms": [{"name": "lab07a", "vcpus": 2, "ram_gb": 4}],
     "vcpu_per_pcpu": 0.17,
     "memory_overcommit": 0.12,
     "steal_idle": {"user": 0.0, "nice": 0.0, "system": 0.0, "idle": 100.0, "iowait": 0.0, "irq": 0.0, "softirq": 0.0, "steal": 0.0},
     "steal_busy": {"…": "ধাপ ৬-এর output হুবহু"},
     "snapshot_taken": true
   }
   ```

   `steal_idle` ও `steal_busy`-তে ধাপ ৫ ও ৬-এর output হুবহু বসান। উপরের সংখ্যাগুলো শুধু format দেখানোর জন্য।

9. **Snapshot-এ ফেরা:** guest-এ একটি file বানিয়ে (`touch /home/$USER/after-snapshot`) `clean` snapshot-এ revert করুন। File কি আছে?

## Expected behavior

| পরিমাপ | যা দেখা উচিত |
|---|---|
| `host.json` | Physical হলে `"virtualized": false`। Windows-এ Hyper-V চালু থাকলে "root partition — host, not a guest" |
| `guest.json` | `"virtualized": true`, hypervisor `kvm`/`oracle`/`microsoft`/…, evidence-এ `logical CPUs: 2` |
| Steal idle | idle ≈ ১০০%, steal ≈ ০ |
| Steal busy | user ≈ ১০০%, idle ≈ ০; host ব্যস্ত থাকলে steal > ০ |
| Snapshot revert | `after-snapshot` file নেই |

## Verification

```bash
python3 labs/07-cloud-fundamentals/A-local-vm-observe/check_a.py ~/lab07a/host.json ~/lab07a/guest.json ~/lab07a/observations.json
# ALL CHECKS PASSED, exit 0
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| VM চালু হয় না: "VT-x is disabled" | BIOS/UEFI-তে virtualization বন্ধ |
| VirtualBox খুব ধীর (Windows) | Hyper-V/WSL2 চালু — VirtualBox তার ওপর চলছে; Hyper-V Manager ব্যবহার করুন |
| `guest is detected as a VM` FAIL | `guest.json` ভুলবশত host-এ বা container-এ বানানো |
| `guest sees N CPU(s)` FAIL | VM-এর vCPU সংখ্যা ও `vms[0].vcpus` আলাদা |
| `busy measurement` FAIL | `yes` চলার সময় মাপা হয়নি, বা idle/busy উল্টো বসানো |
| `error: /proc/stat not available` | `steal` host-এ (Windows/macOS) চালানো হয়েছে — guest-এ চালান |

## Cleanup / reset

- VM রাখতে পারেন (পরের module-এ কাজে লাগবে), বা মুছুন: VM বন্ধ করে tool থেকে "delete including disks"।
- Snapshot disk জায়গা নেয় — অপ্রয়োজনীয় snapshot মুছুন।
- `yes` process চলছে কিনা দেখুন: `pgrep yes`।

## Assessment

1. Guest কোন তিনটি সূত্র থেকে বোঝে যে সে VM? Cloud instance-এ এগুলো কী দেখাবে?
2. `vcpu_per_pcpu` ও `memory_overcommit`-এর মধ্যে কোনটি ১ ছাড়ালে বেশি বিপদ, কেন?
3. Steal কখন বাড়ে? Cloud-এ `%st` বেশি দেখলে কী করবেন?
4. Snapshot কি backup? কেন নয় (L05-12)?
5. VM ও container-এর পার্থক্য এই lab-এর পর্যবেক্ষণ দিয়ে ব্যাখ্যা করুন (Module 09-এর প্রস্তুতি)।
