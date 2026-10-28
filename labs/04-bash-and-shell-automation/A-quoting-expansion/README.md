# Lab 04-A — Quoting, expansion ও strict mode পরীক্ষা

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৪৫–৬০ মিনিট |
| **Environment** | Bash ৪.৪+ (Ubuntu, Fedora বা Git Bash) |
| **Label** | — (শুধু temporary directory-তে; কিছু বদলায় না) |

## Objective

প্রতিটি প্রশ্নের উত্তর **আগে অনুমান করে লিখুন, তারপর চালিয়ে যাচাই করুন।** অনুমান আর বাস্তবের পার্থক্যই এই lab-এর শিক্ষা।

## Prerequisites

- Lesson: [L04-01](../../../04-bash-and-shell-automation/L04-01-script-structure-strict-mode.md), [L04-02](../../../04-bash-and-shell-automation/L04-02-variables-arrays-expansion.md)

## Environment setup

```bash
C=~/devops-ai-engineering/04-bash-and-shell-automation/code
T=$(mktemp -d) && cd "$T"
touch -- "a b.txt" "-n.txt" "*.txt" plain.txt     # `--` ছাড়া touch "-n.txt"-কে option ভাবে (lab লেখার সময় আসলে ঘটেছিল)
mkdir -p ~/devops-notebook/labs/04-A
```

## Steps

1. **Word splitting ও glob:** অনুমান লিখুন, তারপর চালান:

   ```bash
   f="a b.txt"; ls $f; ls "$f"
   for x in *.txt; do echo "[$x]"; done
   for x in $(ls); do echo "[$x]"; done
   ```

   শেষ দুটির পার্থক্য কী এবং কেন?
2. **`-` দিয়ে শুরু নাম:** `cat -n.txt` বনাম `cat -- -n.txt` — কী ঘটে?
3. **নামের ভেতরে literal `*`:** `rm "*.txt"` বনাম `rm *.txt` — কোনটি কী মুছবে? **শুধু অনুমান লিখুন, `rm` চালাবেন না।** তারপর `echo rm *.txt` দিয়ে যাচাই করুন।
4. **Strict mode:** `bash $C/L04-01/strict_mode_demo.sh` চালানোর আগে ১৮টি case-এর প্রতিটির ফল (continued বা STOPPED) অনুমান করে লিখুন। কয়টি মিলল?
5. **Parameter expansion:** `path=/srv/app/releases/2026-10-27_1530/app.tar.gz` থেকে **external command ছাড়া** বের করুন:
   - file name;
   - directory;
   - `.tar.gz` ছাড়া নাম;
   - release-এর তারিখ (`2026-10-27`)।
6. **Unset বনাম খালি:**

   ```bash
   unset U; E=""
   echo "[${U:-d}] [${U-d}] [${E:-d}] [${E-d}]"
   ```

   অনুমান লিখে তারপর যাচাই করুন।
7. **Array:**
   - `files=("a b.txt" "-n.txt")` দিয়ে `"${files[@]}"`, `${files[@]}` ও `"${files[*]}"` — প্রতিটির word সংখ্যা।
   - `printf '[%s]\n'` দিয়ে দেখান।
8. **`"$*"` ও IFS:**

   ```bash
   set -- one two three
   IFS=,; echo "$*"; IFS=$' \t\n'
   ```

   L04-01-এর template-এর bug-এর সাথে সম্পর্ক কী?

## Expected behavior

- Step 1: glob loop-এ ৪টি নাম, প্রতিটি অক্ষত। `$(ls)` loop-এ (Windows/Git Bash-এ আসলে চালানো) ৮টি iteration:
  `[*.txt][-n.txt][a b.txt][plain.txt][-n.txt][a][b.txt][plain.txt]` — `a b.txt` দুই টুকরো, এবং `*.txt`
  নামের file-এর নাম **আবার glob হয়ে** সব `.txt` file দ্বিতীয়বার ঢুকিয়েছে।
- Step 4: বেশিরভাগ মানুষ case ৬, ৭, ১১ ও ১৭-এ ভুল অনুমান করেন।
- Step 6: `[d] [d] [d] []`।

## Verification

```bash
test -s ~/devops-notebook/labs/04-A/answers.md && echo "answers written"
grep -c "অনুমান" ~/devops-notebook/labs/04-A/answers.md      # প্রতিটি step-এ অনুমান লেখা আছে
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `declare -A` বা `${x^^}` error | Bash ৩ (পুরোনো macOS) | Bash ৪.৪+ |
| `strict_mode_demo.sh`-এ case ১৩-এর exit code ভিন্ন | Bash version-ভেদে | স্বাভাবিক; থেমেছে কিনা সেটাই মূল |

## Cleanup / reset

```bash
rm -rf -- "$T"
```

## Assessment

1. কোন তিনটি অনুমান ভুল হয়েছিল, এবং কেন?
2. Step ৩-এর বিপদ কোন বাস্তব পরিস্থিতিতে ঘটতে পারে?
3. এই lab-এর একটি পর্যবেক্ষণ দিয়ে L04-02-এর rename script-এর একটি নকশা-সিদ্ধান্ত ব্যাখ্যা করুন।
