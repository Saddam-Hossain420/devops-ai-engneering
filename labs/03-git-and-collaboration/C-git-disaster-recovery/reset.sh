#!/usr/bin/env bash
# Lab 03-C cleanup: break-it.sh-এর তৈরি directory মোছে — শুধু `.lab03c` চিহ্ন থাকলে।
# Usage: bash reset.sh ~/lab03c
set -euo pipefail

DEST=${1:?usage: bash reset.sh DIR}
[[ -f "$DEST/.lab03c" ]] || { echo "refusing: $DEST is not a Lab 03-C directory (no .lab03c marker)" >&2; exit 2; }
rm -rf -- "$DEST"
echo "removed $DEST"
