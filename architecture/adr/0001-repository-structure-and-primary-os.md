# ADR-0001: Repository structure ও primary operating system

- **Status:** Accepted
- **তারিখ:** 2026-10-26

## Context

- Learner-এর মূল নির্দেশিকা `plan.txt`-এ একটি নির্দিষ্ট top-level structure দেওয়া আছে।
- plan.txt-এ Fedora উল্লেখ ছিল, কিন্তু learner জানিয়েছেন মূল practice **Ubuntu**-তে হবে, কিছু practice Fedora-তে।
- বর্তমানে repository লেখা হচ্ছে Windows machine-এ; practice পরে Linux-এ হবে।
- Repository-কে একাধিক Claude session জুড়ে lesson-by-lesson (`next`, `next N`) এগোতে হবে।

## বিবেচিত বিকল্প

1. **plan.txt-এর structure হুবহু** — learner-এর চাওয়া অনুযায়ী, পরিচিত ও পূর্বানুমেয়।
2. অতিরিক্ত `curriculum/`, `progress/` folder সহ machine-readable curriculum — automation সহজ, কিন্তু learner-এর নির্ধারিত structure-এর বাইরে।
3. Primary OS হিসেবে Fedora — plan.txt অনুযায়ী, কিন্তু learner-এর বাস্তব practice-এর সাথে মেলে না।

## Decision

- plan.txt-এর top-level structure হুবহু রাখা হলো। Curriculum ও progress tracking রাখা হলো plan-এ উল্লেখিত file-এ: `CURRICULUM-MAP.md`, `PROGRESS.md`, এবং প্রতিটি module folder-এর `PROGRESS.md` (stage-specific progress file)।
- **Primary OS: Ubuntu LTS (24.04 লক্ষ্য)।** Fedora-তে আলাদা হলে ঠিক সেই জায়গায় `> **Fedora-তে:**` note।
- Lesson file pattern: `<module>/LMM-NN-<slug>.md`; lesson code: `<module>/code/LMM-NN/`।
- Lab: `labs/<module>/{A,B,C}-<slug>/`; project: `projects/PNN-<slug>/`।

## Consequences

- ইতিবাচক: learner-এর কাছে structure পরিচিত; Ubuntu-কেন্দ্রিক command সরাসরি কাজে লাগবে; Fedora-র পার্থক্যও শেখা হবে।
- নেতিবাচক: Markdown table-এ progress রাখায় সম্পূর্ণ automated হিসাব সীমিত; `scripts/progress.py` Markdown table parse করে এই ঘাটতি পূরণ করে।
- Repository Windows-এ লেখা হলেও সব script LF line ending ও Linux-প্রথম ভাবে লেখা (`.editorconfig`)।

## কখন পুনর্বিবেচনা

- Learner অন্য distribution-এ (যেমন Debian, RHEL) মূল practice সরালে।
