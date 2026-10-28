#!/usr/bin/env bash
# Lab 04-C cleanup — শুধু `.lab04c` চিহ্নযুক্ত directory মোছে।   Usage: bash reset.sh ~/lab04c
set -euo pipefail
DEST=${1:?usage: bash reset.sh DIR}
[[ -f "$DEST/.lab04c" ]] || { echo "refusing: $DEST is not a Lab 04-C directory" >&2; exit 2; }
rm -rf -- "$DEST"
echo "removed $DEST"
