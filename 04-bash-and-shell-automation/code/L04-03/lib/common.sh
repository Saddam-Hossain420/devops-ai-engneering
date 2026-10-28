# shellcheck shell=bash
# lib/common.sh — script-গুলোর সাধারণ function। চালানো নয়, source করা হয়:
#     source "$(dirname -- "${BASH_SOURCE[0]}")/lib/common.sh"
# নিয়ম: প্রতিটি function-এর variable `local`; ফল stdout-এ, বার্তা stderr-এ; সফলতা/ব্যর্থতা return code-এ।

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  echo "lib/common.sh is a library: source it, do not run it" >&2
  exit 2
fi
[[ -n ${_COMMON_SH_LOADED:-} ]] && return 0      # দুবার source হলে আবার define নয়
readonly _COMMON_SH_LOADED=1

# ---- logging ---------------------------------------------------------------
# LOG_LEVEL: debug < info < warn < error (default info)
_log_rank() {
  case $1 in debug) echo 0 ;; info) echo 1 ;; warn) echo 2 ;; error) echo 3 ;; *) echo 1 ;; esac
}

_log() {
  local level=$1; shift
  (( $(_log_rank "$level") >= $(_log_rank "${LOG_LEVEL:-info}") )) || return 0
  local IFS=' '
  printf '%s %-5s %s: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${level^^}" "${SCRIPT_NAME:-${0##*/}}" "$*" >&2
}
log_debug() { _log debug "$@"; }
log_info()  { _log info "$@"; }
log_warn()  { _log warn "$@"; }
log_error() { _log error "$@"; }

die() {  # die <message> [exit code, default 1]
  log_error "$1"
  exit "${2:-1}"
}

# ---- checks ----------------------------------------------------------------
require_cmd() {  # require_cmd cmd... — সবগুলো একবারে পরীক্ষা, অনুপস্থিত সবগুলোর নাম বলে
  local missing=() c
  for c in "$@"; do
    command -v -- "$c" >/dev/null 2>&1 || missing+=("$c")
  done
  if (( ${#missing[@]} )); then
    log_error "missing required command(s): ${missing[*]}"
    return 1
  fi
}

is_true() {  # is_true <value> — 1/true/yes/on (case-insensitive)
  case ${1,,} in 1|true|yes|on) return 0 ;; *) return 1 ;; esac
}

# ---- helpers ---------------------------------------------------------------
join_by() {  # join_by <separator> items... → stdout
  local sep=$1; shift
  local first=${1-}; shift || true
  printf '%s' "$first" "${@/#/$sep}"
  printf '\n'
}

to_bytes() {  # to_bytes 512 | 10K | 1.5M | 2G | 1T → stdout (integer bytes); অবৈধ হলে return 1
  local v=${1^^} num unit
  [[ $v =~ ^([0-9]+(\.[0-9]+)?)([KMGT]?)I?B?$ ]] || return 1
  num=${BASH_REMATCH[1]} unit=${BASH_REMATCH[3]}
  local mult
  case $unit in                     # associative array-এ খালি key ("") অবৈধ — তাই case
    K) mult=1024 ;; M) mult=1048576 ;; G) mult=1073741824 ;; T) mult=1099511627776 ;; *) mult=1 ;;
  esac
  awk -v n="$num" -v m="$mult" 'BEGIN { printf "%d\n", n * m }'   # দশমিক গুণ — Bash শুধু integer জানে
}

retry() {  # retry <attempts> <initial delay seconds> command... — exponential backoff, শেষ exit code ফেরত
  local attempts=$1 delay=$2 n=1 rc
  shift 2
  while true; do
    "$@" && return 0
    rc=$?
    if (( n >= attempts )); then
      log_warn "giving up after $n attempt(s): $* (exit $rc)"
      return "$rc"
    fi
    log_warn "attempt $n/$attempts failed (exit $rc); retrying in ${delay}s: $*"
    sleep "$delay"
    n=$((n + 1))
    delay=$((delay * 2))
  done
}
