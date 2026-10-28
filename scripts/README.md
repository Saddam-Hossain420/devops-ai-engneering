# Scripts — repository tooling

শুধু Python standard library; Python 3.10+ (Ubuntu 24.04-এ default 3.12)। কোনো install লাগে না।

| Script | কাজ |
|---|---|
| [progress.py](progress.py) | Module `PROGRESS.md` পড়ে অগ্রগতি, পরের lesson ও consistency দেখায় (read-only) |
| [check_links.py](check_links.py) | সব Markdown-এর internal link-এর target আছে কিনা যাচাই |
| [tests/test_scripts.py](tests/test_scripts.py) | উপরের দুটির test |

## ব্যবহার (repository root থেকে)

```bash
python3 scripts/progress.py status        # কতটি lesson সম্পন্ন, পরের lesson
python3 scripts/progress.py next 3        # পরের ৩টি lesson ও file path
python3 scripts/progress.py validate      # ID, ক্রম ও status বৈধ কিনা
python3 scripts/check_links.py            # ভাঙা internal link
python3 -m unittest discover -s scripts/tests -v
```

Exit code: `0` = ঠিক আছে, `1` = সমস্যা পাওয়া গেছে — তাই CI-তে সরাসরি ব্যবহারযোগ্য ([.github/workflows/validate.yml](../.github/workflows/validate.yml))।

## Project-specific script

Project বা lesson-এর নিজস্ব script সেই project/lesson-এর folder-এ থাকে (`projects/PNN-*/`, `<module>/code/LMM-NN/`), এখানে নয়।
