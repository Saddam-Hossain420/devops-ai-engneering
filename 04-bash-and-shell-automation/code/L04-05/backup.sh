#!/usr/bin/env bash
#
# backup.sh — একটি directory-র timestamp-যুক্ত tar.gz backup।
#
# Usage: backup.sh [options] --source DIR --dest DIR
#   -s, --source DIR      যে directory-র backup                (env: BACKUP_SOURCE)
#   -d, --dest DIR        backup কোথায় রাখা হবে                 (env: BACKUP_DEST)
#   -x, --exclude PATTERN tar --exclude pattern; একাধিকবার দেওয়া যায়
#   -n, --dry-run         কী করত দেখায়, কিছু লেখে না
#   -v, --verbose         বেশি log (দুবার = debug)
#   -q, --quiet           শুধু warning ও error
#       --log-file FILE   log stderr-এর পাশাপাশি এই file-এও
#       --print-config    চূড়ান্ত configuration দেখিয়ে বের হওয়া
#   -h, --help            এই সাহায্য
#
# মানের অগ্রাধিকার: command-line > environment variable > default।
# Exit codes: 0 OK, 1 runtime error, 2 usage error
#
set -Eeuo pipefail
readonly SCRIPT_NAME=${0##*/}

usage() { sed -n '3,18s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; }

# ---- logging: level, stderr, ঐচ্ছিক file ------------------------------------
LOG_LEVEL=1                 # console: 0 debug, 1 info, 2 warn, 3 error
readonly FILE_LOG_LEVEL=1   # log file-এ সবসময় info ও তার উপরে — `-q` শুধু terminal শান্ত করে
LOG_FILE=""
log() {  # log <level-number> <LABEL> <message...>
  local level=$1 label=$2; shift 2
  local IFS=' ' line
  line=$(printf '%s %-5s %s[%d]: %s' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" "$SCRIPT_NAME" "$$" "$*")
  (( level < LOG_LEVEL )) || printf '%s\n' "$line" >&2
  [[ -z $LOG_FILE ]] || (( level < FILE_LOG_LEVEL )) || printf '%s\n' "$line" >> "$LOG_FILE"
}
debug() { log 0 DEBUG "$@"; }
info()  { log 1 INFO "$@"; }
warn()  { log 2 WARN "$@"; }
error() { log 3 ERROR "$@"; }
usage_error() { error "$1"; echo "Try '$SCRIPT_NAME --help'." >&2; exit 2; }

# ---- argument parsing: short ও long, "--opt VALUE" ও "--opt=VALUE" -------------
parse_args() {
  SOURCE=${BACKUP_SOURCE:-} DEST=${BACKUP_DEST:-}
  DRY_RUN=0 PRINT_CONFIG=0
  EXCLUDES=()
  local verbosity=0 quiet=0
  need_value() { [[ $# -ge 2 && -n $2 && $2 != -* ]] || usage_error "option $1 needs a value"; }
  while (( $# )); do
    case $1 in
      -s|--source)    need_value "$@"; SOURCE=$2; shift ;;
      --source=*)     SOURCE=${1#*=} ;;
      -d|--dest)      need_value "$@"; DEST=$2; shift ;;
      --dest=*)       DEST=${1#*=} ;;
      -x|--exclude)   need_value "$@"; EXCLUDES+=("$2"); shift ;;
      --exclude=*)    EXCLUDES+=("${1#*=}") ;;
      -n|--dry-run)   DRY_RUN=1 ;;
      -v|--verbose)   verbosity=$((verbosity + 1)) ;;
      -vv)            verbosity=$((verbosity + 2)) ;;
      -q|--quiet)     quiet=1 ;;
      --log-file)     need_value "$@"; LOG_FILE=$2; shift ;;
      --log-file=*)   LOG_FILE=${1#*=} ;;
      --print-config) PRINT_CONFIG=1 ;;
      -h|--help)      usage; exit 0 ;;
      --)             shift; break ;;
      -*)             usage_error "unknown option: $1" ;;
      *)              usage_error "unexpected argument: $1 (use --source/--dest)" ;;
    esac
    shift
  done
  (( $# == 0 )) || usage_error "unexpected argument(s) after --: $*"
  if (( quiet )); then LOG_LEVEL=2; elif (( verbosity >= 1 )); then LOG_LEVEL=0; fi
}

validate() {
  [[ -n $SOURCE ]] || usage_error "--source is required (or set BACKUP_SOURCE)"
  [[ -n $DEST ]]   || usage_error "--dest is required (or set BACKUP_DEST)"
  [[ -d $SOURCE ]] || usage_error "source is not a directory: $SOURCE"
  # দুটোই absolute ও normalized — নইলে relative dest (বা "a/../a/b") দিয়ে নিচের পরীক্ষা এড়ানো যেত
  SOURCE=$(realpath -- "$SOURCE")
  DEST=$(realpath -m -- "$DEST")                   # -m: dest এখনো না থাকলেও
  [[ $DEST != "$SOURCE" && $DEST != "$SOURCE"/* ]] || usage_error "dest must not be inside source"
}

print_config() {
  printf 'source=%s\ndest=%s\ndry_run=%d\nlog_level=%d\nlog_file=%s\n' \
    "$SOURCE" "$DEST" "$DRY_RUN" "$LOG_LEVEL" "${LOG_FILE:--}"
  printf 'exclude=%s\n' "${EXCLUDES[@]+"${EXCLUDES[@]}"}"
}

main() {
  parse_args "$@"
  validate
  if (( PRINT_CONFIG )); then print_config; exit 0; fi

  local name archive tar_args=()
  name="$(basename -- "$SOURCE")-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
  archive="$DEST/$name"
  local x
  for x in "${EXCLUDES[@]+"${EXCLUDES[@]}"}"; do tar_args+=(--exclude="$x"); done
  # --force-local: নামে ':' থাকলে GNU tar সেটাকে "host:path" (remote) ভাবে — test-এ "C:/..."-এ আসলে ঘটেছিল
  tar_args+=(--force-local -czf "$archive" -C "$(dirname -- "$SOURCE")" "$(basename -- "$SOURCE")")
  debug "tar ${tar_args[*]}"

  if (( DRY_RUN )); then
    info "dry-run: would create $archive"
    printf '%s\n' "$archive"                       # stdout: ফল (পরের ধাপের script ব্যবহার করতে পারে)
    return 0
  fi
  mkdir -p -- "$DEST"
  tar "${tar_args[@]}"
  info "created $archive ($(du -h -- "$archive" | cut -f1))"
  printf '%s\n' "$archive"
}

main "$@"
