# Claude session protocol

নতুন session শুরু হলে এই file অনুসরণ করুন।

## Session শুরুতে

1. [PROGRESS.md](../PROGRESS.md) পড়ুন — পরের lesson ও session log।
2. সংশ্লিষ্ট module-এর `README.md` ও `PROGRESS.md` পড়ুন।
3. আগের lesson file ও code দেখুন — সম্পন্ন কাজ আবার তৈরি করবেন না।
4. `python3 scripts/progress.py status` চালান।

## Command

| Command | কাজ |
|---|---|
| `next` | Curriculum ক্রমে পরের incomplete lesson **ঠিক একটি** সম্পন্ন করা |
| `next N` | ঠিক N টি lesson, প্রতিটি পুরোপুরি শেষ করে পরেরটি |
| `status` | সম্পন্ন lesson, বর্তমান অগ্রগতি, পরের lesson |
| `explain <topic>` | বাংলায় ব্যাখ্যা, lesson counter বাড়বে না |
| `review <path>` | file/lesson review ও অনুরোধ অনুযায়ী উন্নতি |
| `practice` | সম্পন্ন lesson থেকে practical exercise |
| `quiz` | সম্পন্ন lesson থেকে বোঝাপড়া যাচাই |
| `repeat` | সর্বশেষ lesson আরো ব্যাখ্যা ও exercise সহ |
| `fix` | নির্দিষ্ট সমস্যা তদন্ত ও সমাধান |

`next`-কে কখনো একাধিক lesson তৈরির অনুমতি হিসেবে ধরা হবে না।

## একটি lesson সম্পন্ন করার ধাপ

1. [templates/lesson-template.md](../templates/lesson-template.md) অনুযায়ী `<module>/LMM-NN-<slug>.md` লিখুন — শিক্ষণ ক্রম: সহজ পরিচয় → analogy ও তার সীমা → engineering scenario → internals → practical → troubleshooting ও assessment।
2. Code: `<module>/code/LMM-NN/` — Python-first যেখানে উপযুক্ত; native config (YAML, HCL, Dockerfile, nginx.conf) যেখানে দরকার। Test।
3. Ubuntu command; Fedora আলাদা হলে `> **Fedora-তে:**`।
4. যাচাই: `python3 scripts/check_links.py`, code চালানো/test, syntax check। যা যাচাই হয়নি তা স্পষ্ট লিখুন।
5. আপডেট: module `README.md` (lesson link ও status), module `PROGRESS.md`, root `PROGRESS.md`, `CHANGELOG.md`, `GLOSSARY.md` (নতুন term)।
6. Module-এর শেষ lesson হলে: Level A/B/C lab, module quiz।
7. Report: কোন lesson সম্পন্ন, কী যাচাই হলো, পরের lesson।

## সততা

- File থাকলেই `COMPLETED` নয়।
- Budget না থাকলে শেষ সম্পূর্ণ lesson-এ থামুন; অসম্পূর্ণটিকে `IN_PROGRESS` করে কী বাকি তা লিখুন।
- Terminal output বানাবেন না; উদাহরণ output চিহ্নিত করুন।
- Destructive বা costly কাজ কখনো স্বয়ংক্রিয়ভাবে চালাবেন না।
