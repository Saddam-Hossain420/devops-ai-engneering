#!/usr/bin/env bash
# Lab 04-C verification: DIR/report.sh-কে চারটি পরিস্থিতিতে চালায় (DIR-এর ভেতরেই, TMPDIR=DIR/tmp)।
# Usage: bash check.sh ~/lab04c        exit 0 = ALL CHECKS PASSED
set -uo pipefail

DEST=${1:?usage: bash check.sh DIR}
[[ -f "$DEST/.lab04c" ]] || { echo "not a Lab 04-C directory: $DEST" >&2; exit 2; }
S="$DEST/report.sh"
export TMPDIR="$DEST/tmp"
fail=0
pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }
leftovers() { find "$TMPDIR" -mindepth 1 | wc -l; }

expected=$'app.log\t3\ndb.log\t2\nempty.log\t0\nworker 2.log\t1\nTOTAL\t6'

# ১. সঠিক ফল (space-যুক্ত নাম ও ০-লাইনের file সহ), exit 0
rm -f "$DEST/out.tsv"
bash "$S" "$DEST/input" "$DEST/out.tsv" >"$DEST/run.stdout" 2>"$DEST/run.stderr"; rc=$?
if [[ $rc -eq 0 && -f $DEST/out.tsv && "$(cat "$DEST/out.tsv")" == "$expected" ]]; then
  pass "correct report for all 4 files (exit 0)"
else
  bad "report wrong or missing (exit $rc) — expected:"$'\n'"$expected"
fi

# ২. stdout পরিষ্কার: log/diagnostic stderr-এ
[[ ! -s $DEST/run.stdout ]] && pass "nothing on stdout (logs go to stderr)" || bad "stdout is not empty: $(head -c 80 "$DEST/run.stdout")"

# ৩. relative OUTPUT path কাজ করে (script-এর cd কারণে ভুল জায়গায় লেখা নয়)
( cd "$DEST" && rm -f rel.tsv && bash "$S" "$DEST/input" rel.tsv >/dev/null 2>&1 )
[[ -f $DEST/rel.tsv ]] && pass "relative OUTPUT_FILE is written where the caller expects" \
                       || bad "relative OUTPUT_FILE was not created in the caller's directory"

# ৪. ব্যর্থতায় পরিচ্ছন্নতা: অস্তিত্বহীন input → exit 2, output নেই, temp নেই
rm -f "$DEST/bad.tsv"; before=$(leftovers)
bash "$S" "$DEST/no-such-dir" "$DEST/bad.tsv" >/dev/null 2>&1; rc=$?
[[ $rc -eq 2 ]] && pass "missing input dir → exit 2" || bad "missing input dir → exit $rc (expected 2)"
[[ ! -e $DEST/bad.tsv ]] && pass "no output file left after failure" || bad "partial output left: bad.tsv"
[[ $(leftovers) -eq $before ]] && pass "no temp files left in TMPDIR" || bad "temp files left in $TMPDIR"

(( fail == 0 )) && echo "ALL CHECKS PASSED" || echo "some checks failed"
exit "$fail"
