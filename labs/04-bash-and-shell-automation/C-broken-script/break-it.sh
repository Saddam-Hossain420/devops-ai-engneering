#!/usr/bin/env bash
# Lab 04-C: একটি ভাঙা report script ও তার input তৈরি করে — নিজের directory-তে, system-এ কিছু বদলায় না।
# Usage: bash break-it.sh ~/lab04c
set -euo pipefail

DEST=${1:?usage: bash break-it.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists (reset.sh দিয়ে মুছুন)" >&2; exit 2; }
mkdir -p "$DEST/input" "$DEST/tmp"
touch "$DEST/.lab04c"

printf 'a\nb\nc\n' > "$DEST/input/app.log"
printf 'x\n' > "$DEST/input/worker 2.log"            # নামে space
printf 'one\ntwo\n' > "$DEST/input/db.log"
: > "$DEST/input/empty.log"                          # ০ লাইন

cat > "$DEST/report.sh" <<'SCRIPT'
#!/usr/bin/env bash
# report.sh — INPUT_DIR-এর প্রতিটি *.log file-এর লাইন সংখ্যা, নাম অনুযায়ী সাজানো, OUTPUT_FILE-এ:
#     <name><TAB><lines>
#     TOTAL<TAB><sum>
# Usage: report.sh INPUT_DIR OUTPUT_FILE        exit 0 OK, 2 usage/input error
set -euo pipefail

IN=$1
OUT=$2
TMP=$(mktemp "${TMPDIR:-/tmp}/report.XXXXXX")

echo "starting report for $IN"
cd $IN

count=0
total=0
for f in $(ls *.log); do
  lines=$(wc -l < $f)
  printf '%s\t%d\n' "$f" "$lines" >> "$TMP"
  total=$((total + lines))
  ((count++))
done

sort "$TMP" > "$OUT"
printf 'TOTAL\t%d\n' "$total" >> "$OUT"
echo "processed $count files"
rm -f "$TMP"
SCRIPT

echo "Lab 04-C ready in $DEST"
echo "Broken script: $DEST/report.sh   (input: $DEST/input, use TMPDIR=$DEST/tmp)"
