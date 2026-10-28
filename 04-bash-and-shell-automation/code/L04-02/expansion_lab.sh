#!/usr/bin/env bash
# expansion_lab.sh — parameter expansion ও array: প্রতিটি রূপ ও তার আসল ফল।
# কোনো external command ছাড়াই (sed/awk/basename নয়) string কাটা-ছাঁটা — দ্রুত ও process-মুক্ত।
# Usage: bash expansion_lab.sh
set -Eeuo pipefail
# shellcheck disable=SC2016  # '${...}' লেখাগুলো ইচ্ছাকৃতভাবে literal label — expand হওয়ার কথা নয়

show() {  # show <expression-এর লেখা> <ফল>
  printf '%-34s → [%s]\n' "$1" "$2"
}

path=/var/log/nginx/access.log.2.gz
echo "== string: path=$path"
show '${#path}'               "${#path}"
show '${path##*/}   (basename)' "${path##*/}"
show '${path%/*}    (dirname)'  "${path%/*}"
show '${path#*.}    (shortest)' "${path#*.}"
show '${path##*.}   (last ext)' "${path##*.}"
show '${path%.*}    (drop ext)' "${path%.*}"
show '${path%%.*}   (drop all)' "${path%%.*}"
show '${path/log/LOG}  (first)' "${path/log/LOG}"
show '${path//log/LOG} (all)'   "${path//log/LOG}"
show '${path:0:4}'            "${path:0:4}"
show '${path: -5}  (space!)'  "${path: -5}"

name=ubuntu-Server
echo "== case: name=$name"
show '${name^^}'              "${name^^}"
show '${name,,}'              "${name,,}"
show '${name^}'               "${name^}"

echo "== unset vs empty: unset UNSET; EMPTY=''"
unset UNSET
EMPTY=''
show '${UNSET:-default}'      "${UNSET:-default}"
show '${EMPTY:-default}'      "${EMPTY:-default}"
show '${EMPTY-default}  (no :)' "${EMPTY-default}"
show '${EMPTY:+alt}'          "${EMPTY:+alt}"
SET=x
show '${SET:+alt}'            "${SET:+alt}"
: "${ASSIGNED:=from-default}"
show '${ASSIGNED:=...} then $ASSIGNED' "$ASSIGNED"
if ( : "${UNSET:?is required}" ) 2>/dev/null; then r=ok; else r="error, exit $?"; fi
show '${UNSET:?is required}'  "$r"

ref=name
show '${!ref}  (indirect)'    "${!ref}"

echo "== arrays"
files=("my report.txt" "a b c.log" "plain")
show '${#files[@]}'           "${#files[@]}"
show 'for f in "${files[@]}" (count)' "$(c=0; for f in "${files[@]}"; do c=$((c + 1)); done; echo $c)"
# shellcheck disable=SC2068  # unquoted array ইচ্ছাকৃত — ভুলটাই দেখানো হচ্ছে
show 'for f in ${files[@]}  (count)'  "$(c=0; for f in ${files[@]}; do c=$((c + 1)); done; echo $c)"
show '"${files[*]}"'          "${files[*]}"
show '${files[@]:1:1}'        "${files[@]:1:1}"
files+=("added")
unset 'files[1]'
show 'after += and unset [1]: ${!files[*]}' "${!files[*]}"
show '${#files[@]}'           "${#files[@]}"

declare -A port=([ssh]=22 [https]=443 [postgres]=5432)
show '${port[https]}'         "${port[https]}"
show 'keys, sorted'           "$(printf '%s\n' "${!port[@]}" | sort | tr '\n' ' ')"
show '${port[missing]:-none}' "${port[missing]:-none}"

echo "== splitting safely"
IFS=, read -r -a fields <<< "web-1,10.0.1.5,running"
show 'IFS=, read -r -a fields'  "${fields[1]}"
mapfile -t lines < <(printf 'one\ntwo words\nthree\n')
show 'mapfile -t lines ; ${lines[1]}' "${lines[1]}"
printf -v quoted '%q' "it's a \$test"
show "printf %q \"it's a \$test\"" "$quoted"
