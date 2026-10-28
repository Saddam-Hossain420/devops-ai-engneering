#!/usr/bin/env bash
# হাতে তৈরি উদাহরণ — ইচ্ছাকৃত ভুলে ভরা script। চালাবেন না; শুধু lint-এর জন্য।
# (set -e নেই — ইচ্ছাকৃত)

BACKUP_DIR=$1
cleanup() {
  local count=$(ls "$BACKUP_DIR" | wc -l)
  echo "removing $count files"
  rm -rf "$BACKUP_DIR/"*
}

cd /var/app
for f in $(ls *.log); do
  cp $f /tmp/
done

while read line; do
  echo "$line"
done < list.txt

rm -rf $TMPDIR/build    # TMPDIR খালি হলে?
cleanup
