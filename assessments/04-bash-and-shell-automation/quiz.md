# Module 04 Quiz — Bash and Shell Automation

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৬০ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে shell ছাড়া উত্তর দিন, পরে চালিয়ে যাচাই করুন।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. `set -euo pipefail`-এর প্রতিটি অংশ কী করে?
2. `set -e` কোন তিনটি জায়গায় কাজ করে না?
3. `local x=$(cmd)` কেন ব্যর্থতা লুকায়? সঠিক রূপ কী?
4. stdout ও stderr-এ কী লেখা উচিত, এবং কেন?
5. `"$@"` ও `"$*"`-এর পার্থক্য।
6. `${var:-x}` ও `${var-x}`-এর পার্থক্য।
7. `for f in $(ls)` কেন ভুল?
8. `rm -- "$f"`-এ `--` কী করে?
9. Bash function কীভাবে data ফেরত দেয়, কীভাবে সফলতা জানায়?
10. Library file সরাসরি চালানো হয়েছে কিনা কীভাবে বুঝবেন?
11. EXIT trap-এ exit code কীভাবে রক্ষা করবেন?
12. ERR trap function-এর ভেতরে কাজ না করলে সম্ভাব্য কারণ?
13. Script SIGTERM পেলে কোন exit code দেওয়া উচিত?
14. `getopts`-এর দুটি সীমাবদ্ধতা।
15. অজানা option চুপচাপ উপেক্ষা করা কেন বিপজ্জনক?
16. `flock` ও `mkdir`-ভিত্তিক lock-এর পার্থক্য।
17. Atomic publish কীভাবে করবেন, এবং কখন `mv` atomic নয়?
18. ভালো dry-run-এর মূল নিয়ম কী?
19. ShellCheck কী ধরে, কী ধরে না?
20. কোন তিনটি সংকেত দেখে Bash থেকে Python-এ যাবেন?

## Part B — Analysis (প্রতিটি ২ নম্বর)

21. `set -e` চালু। `count=0; ((count++)); echo done` — `done` ছাপবে কি? কেন? `count=1` হলে?
22. `path=/var/log/nginx/access.log.2.gz`। নিচের প্রতিটির ফল লিখুন:
    - `${path##*/}`
    - `${path%.*}`
    - `${path%%.*}`
    - `${path#*.}`
23. `files=("my report.txt" plain)`। `for f in ${files[@]}` loop কতবার চলবে? `for f in "${files[@]}"` হলে?
24. `IFS=$'\n\t'` সেট করা script-এ `log "x: $*"`, যেখানে `$@ = (mkdir -p dir)`। Output কেমন হবে? সমাধান কী?
25. `set -eo pipefail`। `n=$(printf 'a\n' | grep -c zzz); echo "n=$n"` — কী ঘটে? কীভাবে ঠিক করবেন?
26. EXIT trap: `cleanup() { rm -rf "$TMP"; }`। Script `exit 3` দিয়ে শেষ হলো। Caller কোন exit code দেখবে? কেন, এবং সঠিক রূপ কী?
27. `backup.sh --dest ./b -s .` চালানো হলো source directory-র ভেতর থেকে। "dest source-এর ভেতরে নয়" যাচাই string তুলনায় কেন ব্যর্থ হতে পারে? সমাধান কী?
28. তিনটি backup আছে, `--keep 2`, এবং এই run একটি নতুন backup তৈরি করবে। আসল run কয়টি মুছবে? একটি সরল dry-run (নতুনটি না গুনে) কয়টি মোছার কথা বলত?
29. awk `$9`-কে status ধরে। Log লাইন: `10.0.0.6 - - [27/Oct/2026:10:00:06 +0000] "GET /my file.txt HTTP/1.1" 502 10 "-" "curl"` — `$9` কী? ফল কী হবে?
30. `rm -rf "$INSTALL_ROOT/"*` — কোন ShellCheck code, কী ঝুঁকি, এবং সঠিক রূপ কী?

## Part C — Practical

31. (৫ নম্বর) [Lab 04-C](../../labs/04-bash-and-shell-automation/C-broken-script/README.md) সম্পূর্ণ করুন। `check.sh`-এর output, চারটি ফাঁদ ও প্রতিটির fix লিখুন।
32. (৫ নম্বর) [`strict_mode_demo.sh`](../../04-bash-and-shell-automation/code/L04-01/strict_mode_demo.sh) চালানোর আগে ১৮টি case অনুমান করুন, তারপর চালান। ভুল অনুমানগুলোর ব্যাখ্যা দিন।
33. (৫ নম্বর) [`safe_job.sh`](../../04-bash-and-shell-automation/code/L04-04/safe_job.sh)-কে SIGTERM পাঠান (`-s 30`)। Exit code ১৪৩, temp directory মোছা হয়েছে, এবং কোনো অনাথ child নেই — প্রমাণ দিন (`pgrep` বা `/proc`)।
34. (৫ নম্বর) Ubuntu-তে `shellcheck` ও `bats` install করে [`run_checks.sh --strict`](../../04-bash-and-shell-automation/code/L04-07/run_checks.sh) চালান। প্রতিটি finding ঠিক করুন, অথবা কারণসহ disable করুন।

---

<details>
<summary><strong>Answer key</strong></summary>

**Part A**

1. `-e`: ব্যর্থ command-এ থামে; `-u`: অজানা variable-এ error; `pipefail`: pipeline-এর যেকোনো অংশ ব্যর্থ হলে pipeline ব্যর্থ।
2. `if`/`while`-এর শর্তে; `&&`/`||`-এর শেষ নয় এমন অংশে; ঐভাবে ডাকা function-এর পুরো ভেতরে। (এছাড়া `!`-এর পরে, `local x=$(...)`-এ, এবং `inherit_errexit` ছাড়া `$(...)`-এ।)
3. `local`-এর নিজের exit status (০) দেখা হয়। সঠিক রূপ: `local x; x=$(cmd)`।
4. stdout = ফল (অন্য program পড়বে); stderr = log/diagnostic — pipe ও `$(...)` পরিষ্কার থাকে।
5. `"$@"` = প্রতিটি argument আলাদা word; `"$*"` = সব মিলে একটি string, IFS-এর প্রথম অক্ষর দিয়ে জোড়া।
6. `:-` খালি ও unset দুটোতেই default দেয়; `-` শুধু unset-এ।
7. Output word splitting ও glob-এ ভাঙে — space বা `*`-যুক্ত নাম।
8. "এরপর আর option নয়" — `-` দিয়ে শুরু নামকে option ভাবা হয় না।
9. Data stdout-এ (`$(f)` দিয়ে ধরা); সফলতা return code (০–২৫৫) দিয়ে।
10. `[[ ${BASH_SOURCE[0]} == "$0" ]]` সত্য হলে সরাসরি চালানো হয়েছে।
11. প্রথম লাইনে `local rc=$?`, তারপর `trap - EXIT`, শেষে `exit "$rc"`।
12. `set -E` (errtrace) নেই; অথবা ব্যর্থতা `if`/`&&`/`||`-এর ভেতরে।
13. ১৪৩ (১২৮ + ১৫)।
14. Long option নেই; প্রথম non-option argument-এ থামে।
15. বানান ভুল option (যেমন `--dryrun`) উপেক্ষিত হয়ে উল্টো কাজ (আসল run) হয়ে যেতে পারে।
16. `flock` = kernel lock, process মরলে নিজে মুক্ত; `mkdir` = portable, কিন্তু stale lock থাকে এবং দখলে race।
17. একই filesystem-এ temp-এ লিখে যাচাই করে `mv`। ভিন্ন filesystem-এ `mv` = copy + delete, তাই atomic নয়।
18. আসল run-এর একই সিদ্ধান্তের পথ; শুধু শেষ ধাপে পরিবর্তনের বদলে ছাপানো; pending পরিবর্তনও হিসাবে ধরা।
19. Parser-ভিত্তিক পরিচিত ভুলের pattern ধরে (quoting, SC2155, SC2115…); logic-এর ভুল ধরে না।
20. Nested data, API/retry, ১০০+ লাইন, দশমিক বা তারিখের হিসাব, unit test-এর প্রয়োজন, নিঃশব্দ ভুলের উচ্চ ঝুঁকি (যেকোনো তিনটি)।

**Part B**

21. **না।** Post-increment পুরোনো মান ০ ফেরত দেয়, `((0))` exit ১, তাই script থামে। `count=1` হলে ছাপবে।
22. `access.log.2.gz`; `/var/log/nginx/access.log.2`; `/var/log/nginx/access`; `log.2.gz`।
23. Quote ছাড়া **৩**বার (`my`, `report.txt`, `plain`); quote সহ **২**বার।
24. প্রতিটি argument আলাদা লাইনে (`"$*"` newline দিয়ে জোড়া হয়)। সমাধান: `log()`-এ `local IFS=' '`, অথবা `printf '%q '`।
25. ০টি match → `grep` exit ১ → pipefail-এ assignment ব্যর্থ → `set -e`-এ script থামে, `n=` ছাপে না। ঠিক করা: `n=$(… | grep -c zzz || true)`।
26. **০** (`rm`-এর সফলতা) — ব্যর্থতা লুকিয়ে যায়। সঠিক রূপ: `cleanup() { local rc=$?; trap - EXIT; rm -rf -- "$TMP"; exit "$rc"; }`।
27. `./b` আর source-এর absolute path ভিন্ন string, তাই prefix-তুলনা মেলে না এবং যাচাই এড়িয়ে যায়। সমাধান: দুটোকেই `realpath` (dest-এ `-m`) দিয়ে normalize করে তুলনা।
28. আসল run: ৩ + ১ − ২ = **২**টি। সরল dry-run: ৩ − ২ = **১**টি (ভুলভাবে কম)।
29. `$9` = `HTTP/1.1"` — status নয়। 502-টি গণনা থেকে **নিঃশব্দে বাদ** পড়ে।
30. SC2115। `INSTALL_ROOT` খালি হলে command হয় `rm -rf /*`। সঠিক রূপ: `rm -rf -- "${INSTALL_ROOT:?}/"*`।

**Part C — গ্রহণযোগ্য উত্তরের বৈশিষ্ট্য:**

- আসল output থাকতে হবে।
- Lab C-তে চারটি fix:
  - `count=$((count + 1))`;
  - glob ও quote;
  - log stderr-এ;
  - trap + input-এর আগাম যাচাই + atomic output + absolute output path।
- Strict mode-এর ভুল অনুমানের lesson-ভিত্তিক ব্যাখ্যা।
- SIGTERM-এর প্রমাণ: exit ১৪৩ ও child-এর অনুপস্থিতি।
- ShellCheck-এর finding-এর প্রতিটির সিদ্ধান্ত, disable-এ কারণ লেখা।

</details>
