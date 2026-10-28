# Lab 04-C — Broken script: debug ও repair

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৪৫–৬০ মিনিট |
| **Environment** | Bash ৪.৪+, coreutils — Ubuntu, Fedora বা Windows-এর Git Bash |
| **Label** | — (শুধু নিজের তৈরি directory-তে; system বা global config বদলায় না) |
| **Tested** | `break-it.sh` → `check.sh` (ভাঙা অবস্থায় ৫টি FAIL) → একটি সংশোধিত `report.sh` → `check.sh`: `ALL CHECKS PASSED` (Windows/Git Bash, Bash 5.3, ২০২৬-১০-২৭)। |

## Objective

একটি ছোট report script দেখতে ঠিক, কিন্তু **চারটি ফাঁদ** আছে — প্রতিটি এই module-এর একটি lesson-এর বিষয়। Debugging tool (`bash -x`, ERR trap, `shlint_mini`) দিয়ে খুঁজে script-টি ঠিক করুন, যাতে চারটি পরিস্থিতিতেই সঠিক আচরণ করে।

## Prerequisites

- Lesson: [L04-01](../../../04-bash-and-shell-automation/L04-01-script-structure-strict-mode.md), [L04-02](../../../04-bash-and-shell-automation/L04-02-variables-arrays-expansion.md), [L04-04](../../../04-bash-and-shell-automation/L04-04-error-handling-trap.md), [L04-06](../../../04-bash-and-shell-automation/L04-06-safe-idempotent-scripts.md), [L04-07](../../../04-bash-and-shell-automation/L04-07-shellcheck-bats-testing.md)

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/04-bash-and-shell-automation/C-broken-script
bash break-it.sh ~/lab04c
cat ~/lab04c/report.sh            # এবার script পড়ুন — এটা debugging-এর lab
ls -la ~/lab04c/input
```

Files: [`break-it.sh`](break-it.sh), [`check.sh`](check.sh), [`reset.sh`](reset.sh)।

## Steps

1. Timer চালু করুন।
2. **Symptom:**

   ```bash
   cd ~/lab04c
   TMPDIR=$PWD/tmp bash report.sh input out.tsv; echo "exit=$?"
   cat out.tsv; ls tmp/
   ```

   কী দেখছেন? কোনো error message আছে কি?
3. **Tool দিয়ে খোঁজা:**
   - `TMPDIR=$PWD/tmp bash -x report.sh input out.tsv` — কোন লাইনের পরে থামে?
   - `python3 ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-07/shlint_mini.py report.sh`
   - (Ubuntu) `shellcheck report.sh`
4. **একটি একটি করে ঠিক করুন।** প্রতিবার `bash check.sh ~/lab04c` চালিয়ে দেখুন কোন check সবুজ হলো।
5. শেষে `bash check.sh ~/lab04c` → `ALL CHECKS PASSED`।
6. Notebook-এ প্রতিটি ফাঁদের জন্য লিখুন: লক্ষণ, কোন tool ধরল, কোন lesson, এবং fix।

## Expected behavior

ঠিক করা script:

- `input`-এর চারটি file (একটির নামে space, একটি খালি) সঠিকভাবে গোনে; exit ০।
- stdout-এ কিছু লেখে না (log stderr-এ)।
- Relative output path caller-এর directory-তে লেখে।
- অস্তিত্বহীন input-এ exit ২, কোনো output file বা temp file রাখে না।

## Verification

```bash
bash check.sh ~/lab04c; echo "exit=$?"     # ALL CHECKS PASSED, 0
cat ~/lab04c/out.tsv
```

## Troubleshooting (সূত্র — একটি একটি করে খুলুন)

<details><summary>সূত্র ১ — script প্রথম file-এর পরেই নিঃশব্দে থামে</summary>

`count` শূন্য থেকে শুরু। `((count++))`-এর মান কত, এবং `set -e`-এ `(( 0 ))`-এর exit code কী? (L04-01, case ১১)
</details>

<details><summary>সূত্র ২ — "worker 2.log" দুই টুকরো</summary>

`for f in $(ls *.log)` ও `wc -l < $f` — L04-02। Glob সরাসরি ব্যবহার করুন, এবং variable quote করুন।
</details>

<details><summary>সূত্র ৩ — output file-এ "starting report…" লেখা, বা stdout দূষিত</summary>

Diagnostic কোথায় যাওয়া উচিত? (L04-01: stdout = ফল, stderr = log)
</details>

<details><summary>সূত্র ৪ — relative output ভুল জায়গায়</summary>

Script `cd` করার পরে `out.tsv` কোন directory-র সাপেক্ষে? `cd` কি আদৌ দরকার? দরকার হলে আগে output path absolute করুন (`realpath -m`, L04-05)।
</details>

<details><summary>সূত্র ৫ — ব্যর্থতার পরে temp file থেকে যায়</summary>

Temp file তৈরির পরে কোনো ধাপ ব্যর্থ হলে কে মুছবে? (L04-04: `trap … EXIT`)। Input যাচাই temp তৈরির **আগেই** করলে আরো ভালো। Output-ও temp-এ লিখে শেষে `mv` (L04-06)।
</details>

## Cleanup / reset

```bash
bash reset.sh ~/lab04c       # শুধু .lab04c চিহ্নযুক্ত directory
```

## Assessment

1. চারটি ফাঁদের প্রতিটির লক্ষণ, ধরার পদ্ধতি ও fix।
2. প্রথম ফাঁদে script কোনো error message দেয়নি — L04-04-এর কোন কৌশল থাকলে সঙ্গে সঙ্গে কারণ জানা যেত?
3. আপনার fix-এ কোনো ধাপ ব্যর্থ হলে output-এর কী হয়? Atomic কিনা ব্যাখ্যা করুন।
4. এই script কি Python-এ লেখা উচিত ছিল? L04-08-এর checklist প্রয়োগ করুন।
