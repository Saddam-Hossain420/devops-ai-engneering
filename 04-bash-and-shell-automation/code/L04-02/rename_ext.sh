#!/usr/bin/env bash
#
# rename_ext.sh — একটি directory-তে (recursive নয়) FROM extension-এর file-গুলোকে TO extension-এ rename।
#
# Usage: rename_ext.sh [-n] DIR FROM TO        e.g.  rename_ext.sh -n ./photos jpeg jpg
#   -n   dry-run: কী করত দেখায়, কিছু বদলায় না
#
# নিরাপত্তা: space/newline/শুরুতে '-' যুক্ত নাম নিরাপদ; আগে থেকে থাকা target কখনো overwrite করে না।
# Exit codes: 0 সব ঠিক, 1 কিছু file skip হয়েছে (conflict), 2 usage error
#
set -Eeuo pipefail

usage() { sed -n '3,9s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; }

DRY_RUN=0
while getopts ':hn' opt; do
  case $opt in
    h) usage; exit 0 ;;
    n) DRY_RUN=1 ;;
    *) usage >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
(( $# == 3 )) || { usage >&2; exit 2; }
dir=$1 from=${2#.} to=${3#.}         # ".jpeg" বা "jpeg" দুটোই চলে
[[ -d $dir ]] || { echo "error: not a directory: $dir" >&2; exit 2; }
[[ $from =~ ^[A-Za-z0-9]+$ && $to =~ ^[A-Za-z0-9]+$ ]] || { echo "error: extensions must be alphanumeric" >&2; exit 2; }

renamed=0 skipped=0
# -print0 + read -d '': নামে newline থাকলেও সঠিক; `for f in $(ls)` কখনো নয়
while IFS= read -r -d '' src; do
  base=${src##*/}
  dst="${src%.*}.$to"
  if [[ -e $dst ]]; then
    printf 'skip (target exists): %q\n' "$base" >&2
    skipped=$((skipped + 1))
    continue
  fi
  if (( DRY_RUN )); then
    printf 'would rename: %q -> %q\n' "$base" "${dst##*/}"
  else
    mv -n -- "$src" "$dst"          # -- : '-' দিয়ে শুরু নামকে option ভাবা নয়; -n: race-এ overwrite নয়
    printf 'renamed: %q -> %q\n' "$base" "${dst##*/}"
  fi
  renamed=$((renamed + 1))
done < <(find "$dir" -maxdepth 1 -type f -name "*.$from" -print0 | sort -z)

printf '%d %s, %d skipped\n' "$renamed" "$( (( DRY_RUN )) && echo "would be renamed" || echo renamed)" "$skipped" >&2
(( skipped == 0 ))
