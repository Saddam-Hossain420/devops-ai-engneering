# L07-01 — Virtualization ও hypervisor

| | |
|---|---|
| **Module** | 07 — Cloud Fundamentals |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L01-01 — Linux architecture](../01-linux-systems/L01-01-linux-architecture.md), [L01-16 — Namespace ও cgroup](../01-linux-systems/L01-16-namespaces-cgroups-capabilities.md), [L00-07 — Lab environment](../00-orientation/L00-07-lab-environment-setup.md) |
| **Label** | — |
| **Tested** | `virt_probe.py`: ৭টি test পাস (Python 3.14.5, Windows), নমুনা DMI tree দিয়ে। **এই machine-এ আসলে চালানো হয়েছে:** ফল একটি physical HP laptop, কিন্তু `HypervisorPresent=True` (Section 9.1)। Linux-এর `systemd-detect-virt` ও `/proc/stat`-এর steal অংশ **চালানো হয়নি**। কোনো VM বা cloud resource তৈরি করা হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Virtualization কী: এক physical machine-এ অনেক আলাদা OS।
- Hypervisor-এর ধরন: Type 1 (bare-metal: KVM, Xen, Hyper-V, ESXi, Nitro) ও Type 2 (hosted: VirtualBox, VMware Workstation)।
- CPU-র hardware সমর্থন (Intel VT-x / AMD-V), paravirtualization (virtio), এবং VM বনাম container।
- **Overcommit:** vCPU ও memory — কোনটায় কী ঝুঁকি।
- **CPU steal time** — cloud VM-এর একটি লুকানো performance সমস্যা।
- একটি machine VM কিনা, কোন প্রমাণে বোঝা যায় — এবং প্রমাণ কেন অনিশ্চিত।
- Cloud-এর "instance" আসলে কী।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Cloud provider-এর "instance" একটি VM: কারো data center-এর বিশাল physical server-এ hypervisor চলে, আর তার ওপর আপনার সহ অনেকের VM। এটা বুঝলে বহু বিভ্রান্তিকর আচরণের ব্যাখ্যা মেলে:

- "একই instance type, একই code, তবুও আজ ধীর" — পাশের VM-এর কারণে CPU steal বা noisy neighbor।
- "VM-এ ৪ vCPU, অথচ পুরো ৪ core-এর কাজ হচ্ছে না" — vCPU প্রায়ই একটি hyperthread, পুরো core নয়।
- "Burstable instance হঠাৎ ধীর হয়ে গেল" — CPU credit শেষ।
- "Laptop-এ Docker চালু করার পরে VirtualBox চলছে না" — দুটো hypervisor-এর সংঘাত।

আর Module 09-এর container বোঝার জন্য VM-এর সাথে পার্থক্যটা আগে পরিষ্কার হওয়া দরকার।

## 3. সহজ ভাষায় পরিচয়

| | Type 1 (bare-metal) | Type 2 (hosted) | Container |
|---|---|---|---|
| কোথায় চলে | সরাসরি hardware-এ | একটি OS-এর ওপর app হিসেবে | Host kernel ভাগ করে |
| উদাহরণ | KVM, Xen, Hyper-V, ESXi, AWS Nitro | VirtualBox, VMware Workstation | Docker, LXC (Module 09) |
| প্রতিটির kernel | নিজস্ব | নিজস্ব | Host-এর একটিই |
| আলাদাকরণ | শক্ত (hardware-সহায়তায়) | শক্ত | দুর্বলতর (namespace/cgroup — L01-16) |
| চালু হতে | সেকেন্ড থেকে মিনিট | মিনিট | মিলিসেকেন্ড |
| ব্যবহার | Cloud, data center | Laptop-এ lab | Application packaging |

KVM একটি মিশ্র ক্ষেত্র: Linux kernel-এর একটি module, যা Linux-কেই Type 1 hypervisor বানায়।

```bash
systemd-detect-virt          # kvm / microsoft / oracle / none
grep -c -E 'vmx|svm' /proc/cpuinfo    # host-এ hardware virtualization সমর্থন
python3 virt_probe.py        # এই lesson-এর tool
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### Apartment building

- **Physical server** = একটি বড় ভবন।
- **Hypervisor** = ভবন ব্যবস্থাপনা: কে কোন flat, কতটা পানি-বিদ্যুৎ।
- **VM** = আলাদা flat — নিজের তালা, রান্নাঘর, বাথরুম (নিজের kernel)।
- **Container** = একটি flat-এর ভেতরে আলাদা ঘর — রান্নাঘর ভাগ করে (একটিই kernel)।
- **Overcommit** = ভবনে ১০০টি flat, কিন্তু পানির pump ৬০টির সমান — সবাই একসাথে না চাইলে চলে।

### Analogy কোথায় মেলে না

- **Flat-এর বাসিন্দা জানেন তিনি apartment-এ থাকেন।** VM-এর OS প্রায়ই "জানে" না — তার কাছে hardware দেখতে আসল। প্রমাণ (DMI vendor, CPU-র `hypervisor` flag) পরোক্ষ ও বদলানো যায়। Nested virtualization-এ স্তর মিশে যায় — এই machine-এ Windows নিজেই Hyper-V-এর ওপর চলছে, অথচ machine-টি physical laptop (Section 9.1)।
- **পানির ঘাটতি সবাই একভাবে টের পান।** CPU overcommit-এ VM শুধু **অপেক্ষা** করে (steal time) — ধীর হয়, কিন্তু চলে। Memory overcommit-এ host ballooning বা swap করে — তখন **সব** VM হঠাৎ ভীষণ ধীর হয়। দুটো ঝুঁকি একরকম নয়।
- **পাশের flat-এর শব্দ দেয়াল দিয়ে আসে।** VM-এর মধ্যে শব্দ আসে shared cache, memory bandwidth ও disk/network queue দিয়ে — কোনো log-এ লেখা থাকে না। শুধু steal time (`%st`) ও latency-র অস্থিরতায় বোঝা যায়।

## 5. Real-world engineering scenario — "রাত ৮টায় API ধীর, অথচ CPU ৪০%"

**পরিস্থিতি:** TaskFlow একটি ছোট cloud VM-এ চলে। প্রতি সন্ধ্যায় ৮–১০টায় p99 latency তিন গুণ। `top`-এ CPU ব্যবহার মাত্র ৪০%, memory ঠিক, application log-এ কিছু নেই।

**তদন্ত:**

1. `top`-এর `%st` কলাম (steal) ঐ সময়ে ২৫–৩০%। অর্থাৎ hypervisor সেই সময়টুকু অন্য VM-কে CPU দিয়েছে, আর আমাদের VM-এর process "চলার জন্য প্রস্তুত" অবস্থায় অপেক্ষা করেছে।
2. Instance type ছিল burstable (CPU credit-ভিত্তিক)। সন্ধ্যার traffic-এ credit শেষ হয়ে baseline-এ নেমে যায় — provider-এর metric-এ credit balance শূন্য।
3. VM-এর ভেতরের "CPU ৪০%" ছিল তার নিজের ভাগের ৪০% — host-এর বাস্তবতা নয়।

**সমাধানের বিকল্প:**

- Non-burstable বা উপযুক্ত instance type (খরচ বাড়ে — L07-06)।
- Monitoring-এ steal time ও credit balance (Module 17)।
- Load-কে একাধিক ছোট instance-এ ভাগ করা।

**শিক্ষা:** VM-এর ভেতরের metric একটি সীমিত দৃশ্য। Steal time হলো hypervisor-এর দিকের জানালা — এটা monitor না করলে "রহস্যময় ধীরতা" ব্যাখ্যা করা যায় না।

## 6. Diagram

```text
 Type 1 (cloud):                                Type 2 (laptop lab):
 ┌───────── VM A ────────┐ ┌──── VM B ────┐      ┌── VM ──┐ ┌── VM ──┐
 │ app │ guest kernel     │ │ guest kernel │      │ guest  │ │ guest  │
 │ virtio-net/blk drivers │ │              │      └────┬───┘ └───┬────┘
 └───────────┬────────────┘ └──────┬───────┘      VirtualBox / VMware (app)
       vCPU = host thread-এর সময়ের ভাগ             ─────────────────────────
 ┌─────────── hypervisor (KVM / Nitro / Xen) ───┐  host OS (Windows/macOS/Linux)
 │ CPU scheduling · memory (EPT/NPT) · I/O       │  ─────────────────────────
 └──────────────────────────────────────────────┘  hardware (VT-x/AMD-V)
 hardware: CPU (VT-x/AMD-V), RAM, NIC, disk

 guest-এর /proc/stat:  user  system  idle  iowait … steal ← hypervisor অন্যকে CPU দিয়েছে
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Hypervisor / VMM | VM তৈরি ও চালানোর software |
| Guest / host | VM-এর ভেতরের OS / নিচের machine |
| vCPU | VM-কে দেওয়া virtual CPU — সাধারণত একটি host thread-এর সময় |
| VT-x / AMD-V | CPU-র hardware virtualization সমর্থন |
| EPT / NPT | Hardware-সহায়তায় guest memory-র address অনুবাদ |
| Paravirtualization / virtio | Guest জানে সে VM-এ, তাই দ্রুত I/O driver ব্যবহার করে |
| Overcommit | Host-এর চেয়ে বেশি vCPU/memory VM-দের দেওয়া |
| Steal time (`%st`) | Guest প্রস্তুত ছিল, কিন্তু hypervisor CPU অন্যকে দিয়েছে |
| Ballooning | Host guest-এর ভেতর থেকে memory ফেরত নেয় |
| Noisy neighbor | একই host-এর অন্য VM-এর কারণে performance হ্রাস |
| Burstable instance | CPU credit-ভিত্তিক; credit শেষে baseline-এ নামে |
| Nested virtualization | VM-এর ভেতরে আরেকটি hypervisor |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 CPU

Hardware virtualization-এ (VT-x/AMD-V) guest-এর বেশিরভাগ instruction সরাসরি CPU-তে চলে। শুধু বিশেষ instruction (hardware-এ প্রবেশ, privileged register) "VM exit" ঘটায়, এবং hypervisor সেগুলো সামলায়।

তাই compute-heavy কাজে VM প্রায় native গতিতে চলে। I/O-heavy কাজে exit বেশি হয় — virtio এবং cloud-এর hardware offload (যেমন AWS Nitro card) এই খরচ কমায়।

### 8.2 Memory

Guest ভাবে তার কাছে "physical" memory আছে। Hypervisor সেটাকে host-এর আসল memory-তে map করে, EPT/NPT hardware-এর সাহায্যে।

Overcommit-এ host ballooning (guest-এর ভেতরের driver memory "ধরে রেখে" ফেরত দেয়), KSM (একই page ভাগ), বা swap ব্যবহার করে — শেষটি ভয়ঙ্কর ধীর। Public cloud সাধারণত memory overcommit করে না। Private cloud-এ (VMware, OpenStack) এটা একটি নীতিগত সিদ্ধান্ত।

### 8.3 VM কিনা — প্রমাণ

| উৎস | কী দেখায় | দুর্বলতা |
|---|---|---|
| CPUID-এর hypervisor bit (`/proc/cpuinfo`-এর `hypervisor` flag) | কোনো hypervisor-এর ওপর চলছে | Nested বা root partition-এও set থাকতে পারে |
| DMI (`/sys/class/dmi/id/*`) | Vendor/product: "QEMU", "Amazon EC2" | Hypervisor ইচ্ছামতো বদলাতে পারে |
| `systemd-detect-virt` | উপরের সব মিলিয়ে, VM ও container আলাদা | Linux-এ |
| Windows CIM `HypervisorPresent` | Hypervisor আছে | Host-এ Hyper-V চালু থাকলেও True |

`virt_probe.py` সব প্রমাণ দেখায় এবং একটি সিদ্ধান্ত দেয়, কিন্তু প্রমাণগুলোও লিখে রাখে — কারণ সিদ্ধান্ত নিশ্চিত নয়।

### 8.4 Steal time

Guest kernel প্রতিটি tick-এ হিসাব রাখে, CPU কোথায় গেছে — user, system, idle, iowait, … এবং **steal**: hypervisor-এর কাছ থেকে জানা, কতক্ষণ guest চলতে চেয়েছিল কিন্তু CPU পায়নি।

`/proc/stat`-এর দুটি sample-এর পার্থক্য থেকে শতাংশ বের হয় (`virt_probe.py steal`)। নিয়মিত ৫–১০%-এর বেশি steal মানে host ব্যস্ত, অথবা burstable credit শেষ।

> **Fedora-তে:** KVM ও libvirt (`dnf install @virtualization`, `virt-manager`) Fedora-র প্রথম শ্রেণির সমর্থিত পথ। Ubuntu-তে `qemu-kvm libvirt-daemon-system` বা Multipass। `systemd-detect-virt` দুই distro-তেই একই।

## 9. Practical demonstration

Files: [`code/L07-01/virt_probe.py`](code/L07-01/virt_probe.py), [`test_l07_01.py`](code/L07-01/test_l07_01.py)।

### 9.1 এই machine — আসল output

```bash
cd ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-01
python3 virt_probe.py
```

```text
physical (no VM evidence) — hypervisor present (this OS is the Hyper-V root partition — host, not a guest)
  evidence: CIM: manufacturer='HP' model='HP EliteBook 845 14 inch G11 Notebook PC' HypervisorPresent=True
  evidence: python platform: Windows-11-10.0.26300-SP0; logical CPUs: 12
```

একটি সূক্ষ্ম ফল:

- Machine-টি physical laptop।
- কিন্তু **hypervisor উপস্থিত** — Docker Desktop/WSL2-এর জন্য Hyper-V চালু, তাই Windows নিজেই Hyper-V-এর "root partition"-এ চলে।

একারণেই এমন machine-এ VirtualBox-এর পুরোনো version ধীর হয় বা চলে না — দুটি hypervisor একই hardware feature চায়। `HypervisorPresent` একা দেখে "এটা VM" বলা ভুল হতো।

### 9.2 Overcommit — আসল output

```bash
python3 virt_probe.py overcommit --host-cores 32 --vcpus 160 --host-ram-gb 256 --vm-ram-gb 300
```

```text
{
  "vcpu_per_pcpu": 5.0,
  "memory_overcommit": 1.17,
  "notes": [
    "vCPU:pCPU 5.0:1 — high; expect CPU steal (%st) when guests are busy together",
    "memory 117% of host — overcommitted RAM means ballooning/swap on the host: every guest slows down, unlike CPU overcommit which only shares time"
  ]
}
```

### 9.3 Ubuntu VM-এর ভেতরে (চালানো হয়নি)

```bash
python3 virt_probe.py                     # প্রত্যাশা: VIRTUAL MACHINE — kvm/oracle/microsoft …
systemd-detect-virt; cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
python3 virt_probe.py steal 5             # ৫ s-এর CPU ভাগ, steal সহ
# অন্য terminal-এ host-এ বা অন্য VM-এ CPU চাপ দিয়ে (stress-ng) steal বাড়ে কিনা দেখুন
top                                        # '%st' কলাম
```

### 9.4 Test

```bash
python3 -m unittest -v
```

৭টি test:

- Vendor/product signature — Microsoft-এর আসল hardware VM নয়; HP physical।
- নমুনা DMI-তে KVM।
- শুধু hypervisor flag।
- Physical।
- প্রমাণ না থাকলে "unknown"।
- Overcommit।
- Steal-এর হিসাব।
- CLI।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `SIGNATURES` | DMI লেখা → hypervisor | সবচেয়ে সাধারণ পরিচয় |
| Microsoft-এর ব্যতিক্রম | "Microsoft" + "virtual" না থাকলে VM নয় | Surface laptop physical |
| `systemd-detect-virt --vm/--container` | VM ও container আলাদা | Container VM নয় |
| `--root` | নমুনা tree থেকে পড়া | Test ও অন্য machine-এর copy |
| `virtualized: None` | প্রমাণ নেই | "জানি না" ≠ "physical" |
| `HypervisorPresent` + physical vendor | Root partition | Section 9.1 |
| `steal_percent` | `/proc/stat`-এর পার্থক্য | Kernel-এর নিজস্ব হিসাব |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| Laptop/physical | physical (Hyper-V চালু থাকলে "hypervisor present") |
| Ubuntu VM-এ | VIRTUAL MACHINE + hypervisor-এর নাম |
| `overcommit` ৫:১ ও ১১৭% | দুটি সতর্কতা |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| VirtualBox: "VT-x is not available" | BIOS-এ বন্ধ, বা Hyper-V দখল করে আছে | BIOS-এ চালু; Hyper-V-এর সাথে compatible version |
| VM-এ CPU কম, তবুও ধীর | Steal time / burst credit শেষ | `%st`; instance type |
| `sysbench` ফল দিনে দিনে ভিন্ন | Noisy neighbor | বহুবার মাপুন, median (L00-06) |
| VM-এর disk ধীর | Emulated driver | virtio-blk/scsi |
| Snapshot থেকে ফেরত গিয়ে সময় ভুল | Guest-এর ঘড়ি | NTP/chrony (L01) |
| Container-কে VM ভাবা | একই kernel | `systemd-detect-virt --container` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - VM-এর আলাদাকরণ container-এর চেয়ে শক্ত, কিন্তু অভেদ্য নয় — CPU-র side-channel দুর্বলতা (Spectre/L1TF-শ্রেণি) একই host-এর VM-দের মধ্যে ঝুঁকি তৈরি করেছিল।
  - সংবেদনশীল কাজে dedicated host।
  - Snapshot-এ memory ও disk-এর secret থাকে — snapshot-কে data হিসেবেই সুরক্ষিত রাখুন।
- **Performance:**
  - Compute-এ প্রায় native।
  - I/O-তে virtio ও hardware offload।
  - Steal time monitor করুন।
  - vCPU প্রায়ই hyperthread — ৪ vCPU ≠ ৪ physical core।
- **Cost:**
  - Cloud-এ VM-এর আকার = বিল। Overcommit-এর সুবিধা provider পায়, আপনি পান দাম।
  - Burstable instance সস্তা, কিন্তু স্থির load-এ credit শেষ হয়ে ধীর (বা unlimited mode-এ বাড়তি বিল)।
  - Right-sizing (L07-06, Module 29)।

## 14. Hands-on exercise

1. Ubuntu VM-এর ভেতরে `virt_probe.py` চালান। কোন প্রমাণে hypervisor চেনা গেল? `--json` দিয়ে সংরক্ষণ করুন।
2. VM-এ `virt_probe.py steal 10` চালানোর সময় host-এ বা পাশের VM-এ CPU চাপ দিন। Steal কতটা বাড়ে?
3. একই VM-এ ১ বনাম ৪ vCPU দিয়ে একটি CPU benchmark (Python-এর prime গণনা, `multiprocessing`) চালান। Scaling রৈখিক কি?
4. `virt_probe.py`-তে container শনাক্তকরণ যোগ করুন (`/.dockerenv`, `/proc/1/cgroup`)। Docker container-এর ভেতরে চালিয়ে দেখুন (Module 09-এর আগে প্রস্তুতি)।
5. আপনার laptop-এ Hyper-V/WSL2 চালু আছে কিনা দেখুন। VirtualBox ও Hyper-V একসাথে চালালে কী হয়, তা নোট করুন।

## 15. Mini-project — Host capacity planner

`capacity_plan.py hosts.json vms.json`:

- Host-গুলোর core/RAM ও VM-গুলোর vCPU/RAM।
- First-fit/best-fit-এ VM বসানো, overcommit সীমাসহ (vCPU ৪:১, RAM ১:১)।
- কোন VM বসানো গেল না, এবং প্রতিটি host-এর অনুপাত।
- Anti-affinity: একই app-এর দুটি VM একই host-এ নয় (L07-03-এর fault domain)।

## 16. Interview প্রশ্ন

1. Type 1 ও Type 2 hypervisor-এর পার্থক্য কী? উদাহরণ দিন।
2. VM ও container-এর মৌলিক পার্থক্য কী?
3. CPU steal time কী? কখন দেখবেন?
4. CPU ও memory overcommit-এর ঝুঁকি কীভাবে আলাদা?
5. Burstable instance কীভাবে কাজ করে?
6. একটি machine VM কিনা কীভাবে বুঝবেন?

## 17. Self-assessment প্রশ্ন

1. Apartment analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ CPU ৪০% হওয়া সত্ত্বেও ধীরতার দুটি কারণ কী?
3. এই laptop-এ `HypervisorPresent=True` কেন, এবং এটা VM নয় কেন?
4. VM-কে "virtualized: None" বলা কেন "physical" বলার চেয়ে ভালো?
5. Memory overcommit-এ "সবাই ধীর" কেন?

## 18. সংক্ষিপ্ত সারাংশ

- Cloud instance = hypervisor-এর ওপর VM; Type 1 (KVM, Nitro, Hyper-V) data center-এ।
- VM-এর নিজস্ব kernel; container host kernel ভাগ করে।
- CPU overcommit → steal time; memory overcommit → ballooning/swap, সবাই ধীর।
- `%st` ও burst credit monitor করুন।
- VM শনাক্তকরণ প্রমাণ-ভিত্তিক ও অনিশ্চিত — প্রমাণ দেখান, শুধু সিদ্ধান্ত নয়।

## 19. Completion checklist

- [ ] নিজের laptop ও একটি VM-এ `virt_probe.py` চালিয়ে পার্থক্য ব্যাখ্যা করতে পারি
- [ ] (VM) steal time মেপেছি
- [ ] Overcommit-এর দুই ধরনের ঝুঁকি বলতে পারি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Linux kernel — KVM documentation: https://docs.kernel.org/virt/kvm/index.html
- systemd — `systemd-detect-virt`: https://www.freedesktop.org/software/systemd/man/latest/systemd-detect-virt.html
- Linux man page — `proc_stat(5)` (steal): https://man7.org/linux/man-pages/man5/proc_stat.5.html
- Microsoft Learn — Hyper-V architecture: https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/reference/hyper-v-architecture
- AWS — The Nitro System: https://aws.amazon.com/ec2/nitro/
- AWS — Burstable performance instances: https://docs.aws.amazon.com/ec2/latest/instancetypes/burstable-performance-instances.html
- virtio specification (OASIS): https://docs.oasis-open.org/virtio/virtio/

---

**পরের lesson:** L07-02 — IaaS, PaaS, SaaS ও shared responsibility model
