#!/usr/bin/env bats
# L04-02-এর rename_ext.sh-এর bats test।  চালানো (Ubuntu):  bats tests/rename_ext.bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../../L04-02/rename_ext.sh"
  D="$BATS_TEST_TMPDIR/files"
  mkdir -p "$D"
  touch "$D/my photo.jpeg" "$D/-dash.jpeg" "$D/plain.jpeg" "$D/keep.png"
}

@test "renames names with spaces and a leading dash" {
  run bash "$SCRIPT" "$D" jpeg jpg
  [ "$status" -eq 0 ]
  [ -e "$D/my photo.jpg" ]
  [ -e "$D/-dash.jpg" ]
  [ -e "$D/keep.png" ]
}

@test "never overwrites an existing target and exits 1" {
  echo original > "$D/plain.jpg"
  run bash "$SCRIPT" "$D" jpeg jpg
  [ "$status" -eq 1 ]
  [ "$(cat "$D/plain.jpg")" = original ]
  [ -e "$D/plain.jpeg" ]
}

@test "dry-run changes nothing" {
  before=$(ls -A "$D" | sort)
  run bash "$SCRIPT" -n "$D" jpeg jpg
  [ "$status" -eq 0 ]
  [ "$(ls -A "$D" | sort)" = "$before" ]
}

@test "non-alphanumeric extension is rejected" {
  run bash "$SCRIPT" "$D" 'jp*g' jpg
  [ "$status" -eq 2 ]
}
