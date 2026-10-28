# Implementation plan

## 1. Environment report (2026-10-26)

Repository লেখার machine (practice machine নয়):

| বিষয় | পাওয়া গেছে |
|---|---|
| OS | Windows 11 Pro |
| CPU | 12 logical core |
| RAM | ~15 GB |
| GPU | NVIDIA GPU পাওয়া যায়নি (`nvidia-smi` নেই) |
| Disk (D:) | ~32 GB free |
| Python | 3.14 |
| Git | 2.54 |
| Docker | Docker Desktop 29.7 (engine তখন চালু ছিল না) |
| kubectl | 1.36 (client) |
| WSL2 | আছে, শুধু `docker-desktop` distro |
| terraform, ansible, kind, helm, aws CLI | নেই |

**Practice environment:** learner পরে **Ubuntu Linux**-এ practice করবেন, কিছু অংশ Fedora-তে। তাই সব lesson Ubuntu-র জন্য লেখা, Fedora পার্থক্য inline। এই Windows machine-এ শুধু repository-র Python script (link checker, progress) যাচাই করা হয়।

## 2. Repository architecture

plan.txt-এর structure হুবহু (বিস্তারিত: [ADR-0001](../architecture/adr/0001-repository-structure-and-primary-os.md))।

| Progress-এর জায়গা | কী |
|---|---|
| `CURRICULUM-MAP.md` | 356 lesson-এর ID, title, level, label, module dependency graph |
| `PROGRESS.md` | মোট অগ্রগতি, পরের lesson, milestone, session log |
| `<module>/PROGRESS.md` | প্রতিটি lesson: content status, learner status, file, validation, prerequisite, next |
| `<module>/README.md` | Module scope, prerequisite, outcome, lesson table, lab, completion criteria |

## 3. Batch পরিকল্পনা (priority অনুযায়ী)

| Batch | কাজ | অবস্থা |
|---|---|---|
| 0 | Foundation: root file, 33 module index ও progress, templates, assessments, reference, docs, projects spec, scripts, .github | এই session |
| 1 | Module 00 (L00-01 … L00-07) | L00-01 এই session; বাকি `next` দিয়ে |
| 2 | Module 01 Linux (18 lesson) + labs + P01 শুরু | `next` |
| 3 | Module 02 Networking (17) + labs | `next` |
| 4 | Module 03–05 (27) + continuous project v0.1–v0.2 | `next` |
| 5 | Module 06–08 (27) + P02 শুরু | `next` |
| 6 | Module 09–10 (21) + P02 সম্পূর্ণ | `next` |
| 7 | Module 11 (14) + P03 | `next` |
| 8 | Module 12–13 (21) + P04, P05 | `next` |
| 9 | Module 14–16 (39) + P06, P07 | `next` |
| 10 | Module 17–19 (37) + P08, P09 | `next` |
| 11 | Module 20–22 (24) | `next` |
| 12 | Module 23–27 (63) + P10, P11, P12 | `next` |
| 13 | Module 28–32 (48) + P13 | `next` |

প্রতিটি `next`-এ ঠিক একটি lesson (বা `next N`-এ N টি), সাথে সেই lesson-এর code, exercise ও validation। Module-এর শেষ lesson-এর সাথে তার Level A/B/C lab ও module quiz।

## 4. প্রতিটি batch-এর ধাপ

1. File তৈরি → 2. সম্পূর্ণ content → 3. exercise ও script → 4. validation (link, syntax, test) → 5. শুধু নিরাপদ check চালানো → 6. progress আপডেট → 7. কী হলো ও কী বাকি তার সারাংশ।

## 5. Assumption

- Learner Ubuntu 24.04 LTS (বা নতুন LTS) ব্যবহার করবেন; command সেই অনুযায়ী।
- Python 3.11+ (Ubuntu 24.04-এ 3.12)।
- Paid cloud account বাধ্যতামূলক নয়; AWS lesson-এ free tier ও cost সতর্কতা।
- GPU নেই ধরে নেওয়া; GPU lesson-এ CPU বিকল্প।

## 6. ঝুঁকি ও প্রতিরোধ

| ঝুঁকি | প্রতিরোধ |
|---|---|
| Version-sensitive command পুরোনো হয়ে যাওয়া | Lesson-এ "Tested on" version; [keeping-current.md](keeping-current.md) |
| এই machine-এ Linux command চালিয়ে যাচাই করা যায় না | Lesson-এ স্পষ্টভাবে লেখা হবে কী যাচাই হয়েছে ও কী হয়নি; Linux-এ verification procedure |
| Cloud lab-এ অপ্রত্যাশিত বিল | 💰 label, budget alert প্রথমে, cleanup checklist বাধ্যতামূলক |
| অনেক lesson-এ shallow content | Lesson count-এর চেয়ে quality; `next N` বাজেট না থাকলে শেষ সম্পূর্ণ lesson-এ থামা |
| Session বিচ্ছিন্ন হওয়া | PROGRESS.md session log ও module PROGRESS.md থেকে resume |
