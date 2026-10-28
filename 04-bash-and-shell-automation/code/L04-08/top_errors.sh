#!/usr/bin/env bash
#
# top_errors.sh — access log-এ 5xx error সবচেয়ে বেশি এমন path-গুলো, JSON-এ।  (Bash + awk সংস্করণ)
#
# Usage: top_errors.sh LOGFILE [N]        (N default 5)
#
# সচেতন সরলীকরণ: awk field-ভিত্তিক ($7 = path, $9 = status), JSON হাতে printf দিয়ে —
# এটা দ্রুত ও ছোট, কিন্তু Section 9.2-এ দেখুন কোথায় ভাঙে।
#
set -Eeuo pipefail
[[ $# -ge 1 && -r $1 ]] || { echo "usage: top_errors.sh LOGFILE [N]" >&2; exit 2; }
N=${2:-5}
[[ $N =~ ^[0-9]+$ ]] || { echo "N must be an integer" >&2; exit 2; }

awk '$9 ~ /^5[0-9][0-9]$/ { count[$7]++ ; total++ }
     END { for (p in count) print count[p], p; print total + 0 > "/dev/stderr" }' "$1" 2>"${TMPDIR:-/tmp}/top_errors.total.$$" \
  | sort -k1,1nr -k2,2 | head -n "$N" \
  | { printf '{"top": ['; sep=""
      while read -r c p; do printf '%s{"path": "%s", "count": %d}' "$sep" "$p" "$c"; sep=", "; done
      printf '], "total_5xx": %d}\n' "$(cat "${TMPDIR:-/tmp}/top_errors.total.$$")"; }
rm -f -- "${TMPDIR:-/tmp}/top_errors.total.$$"
