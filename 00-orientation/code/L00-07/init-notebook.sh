#!/usr/bin/env bash
# Engineering notebook directory তৈরি করে। আবার চালানো নিরাপদ (idempotent):
# বিদ্যমান file কখনো overwrite করে না।
#
# Usage:
#   bash init-notebook.sh              # ~/devops-notebook
#   bash init-notebook.sh /path/to/dir
#   bash init-notebook.sh --dry-run    # কী করবে শুধু দেখায়

set -euo pipefail

DRY_RUN=0
TARGET="${HOME}/devops-notebook"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    -*) echo "error: unknown option: $arg" >&2; exit 2 ;;
    *) TARGET="$arg" ;;
  esac
done

run() {
  # dry-run-এ command শুধু দেখায়, চালায় না
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

write_if_missing() {
  local file="$1" content="$2"
  if [[ -e "$file" ]]; then
    echo "skip   $file (already exists)"
  elif [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] create $file"
  else
    printf '%s\n' "$content" > "$file"
    echo "create $file"
  fi
}

run mkdir -p "$TARGET/experiments" "$TARGET/incidents" "$TARGET/labs"

write_if_missing "$TARGET/README.md" "# Engineering notebook

প্রতিটি lesson, lab ও experiment-এর নোট এখানে।

- experiments/  — hypothesis, prediction, আসল output, সিদ্ধান্ত
- incidents/    — নিজের তৈরি বা দেখা failure-এর timeline ও শিক্ষা
- labs/         — lab-এর ধাপ ও যাচাইয়ের ফল

নিয়ম: output বানাবেন না, কপি করুন; environment লিখুন; prediction আগে লিখুন।"

write_if_missing "$TARGET/experiments/TEMPLATE.md" "## Experiment: <শিরোনাম> — <তারিখ>

- Environment:
- Observation:
- Hypothesis:
- Prediction (data দেখার আগে):
- Method:
- Commands:
- Results (আসল output):
- Conclusion:
- Next question:"

if [[ "$DRY_RUN" -eq 0 ]]; then
  echo "notebook ready: $TARGET"
fi
