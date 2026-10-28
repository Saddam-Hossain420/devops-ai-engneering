#!/usr/bin/env bats
# L04-06-এর backup_safe.sh-এর bats test।  চালানো (Ubuntu):  sudo apt install bats && bats tests/
# প্রতিটি @test আলাদা process-এ চলে; BATS_TEST_TMPDIR প্রতি test-এ নতুন, শেষে মুছে যায় (bats ১.৪+)।

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../../L04-06/backup_safe.sh"
  SRC="$BATS_TEST_TMPDIR/app"
  DEST="$BATS_TEST_TMPDIR/bk"
  mkdir -p "$SRC"
  echo v1 > "$SRC/a.txt"
}

archive_count() {
  find "$DEST" -maxdepth 1 -name 'app-*.tar.gz' | wc -l
}

@test "first run creates one verified archive and prints its path" {
  run bash "$SCRIPT" -q -s "$SRC" -d "$DEST"
  [ "$status" -eq 0 ]
  [[ "$output" == "$DEST"/app-*.tar.gz ]]
  tar -tzf "$output" | grep -q 'app/a.txt'
}

@test "second run with unchanged source creates nothing (idempotent)" {
  bash "$SCRIPT" -q -s "$SRC" -d "$DEST"
  run bash "$SCRIPT" -s "$SRC" -d "$DEST"
  [ "$status" -eq 0 ]
  [[ "$output" == *"unchanged"* ]]
  [ "$(archive_count)" -eq 1 ]
}

@test "a concurrent run exits 75 and names the holder" {
  bash "$SCRIPT" -f -q -H 3 -s "$SRC" -d "$DEST" &
  holder=$!
  sleep 1
  run bash "$SCRIPT" -f -s "$SRC" -d "$DEST"
  wait "$holder"
  [ "$status" -eq 75 ]
  [[ "$output" == *"another backup"* ]]
}

@test "dry-run touches nothing" {
  run bash "$SCRIPT" -n -s "$SRC" -d "$DEST"
  [ "$status" -eq 0 ]
  [ ! -e "$DEST" ]
}

@test "usage errors exit 2" {
  run bash "$SCRIPT" -s /does/not/exist -d "$DEST"
  [ "$status" -eq 2 ]
  run bash "$SCRIPT" -s "$SRC" -d "$SRC/inside"
  [ "$status" -eq 2 ]
  run bash "$SCRIPT" -k notanumber -s "$SRC" -d "$DEST"
  [ "$status" -eq 2 ]
}
