#!/usr/bin/env bash
#
# coco-watchdog.sh — ping 192.168.0.11/.12/.13 once per pass. A unit is only
# powercycled after FAIL_THRESHOLD consecutive failed passes; counters persist
# on disk, so cron-driven single passes accumulate just like --loop does.
#
# Usage:
#   ./coco-watchdog.sh              # single pass over all units
#   ./coco-watchdog.sh --loop       # keep monitoring forever
#   ./coco-watchdog.sh --loop --interval 300
#   ./coco-watchdog.sh --threshold 5              # 5 bad passes before reboot
#   ./coco-watchdog.sh --reset                    # clear failure counters
#   ./coco-watchdog.sh --lib /path/to/powercycle-func.sh   # powercycle is a function
#   UNITS="192.168.0.11 192.168.0.14" ./coco-watchdog.sh
#
set -uo pipefail

# Associative arrays (the PC_TARGET map below) need bash 4+.
if (( BASH_VERSINFO[0] < 4 )); then
    echo "This script needs bash 4 or newer (found ${BASH_VERSION})." >&2
    exit 1
fi

# ---------------------------- configuration ---------------------------------
read -r -a UNITS <<< "${UNITS:-192.168.0.11 192.168.0.12 192.168.0.13}"

# What to hand to the powercycle command for each IP. If your powercycle
# utility takes the IP directly, delete this block (unmapped IPs fall back to
# the IP itself). Values could equally be PDU outlet numbers, e.g. [.11]=3.
declare -A PC_TARGET=(
    [192.168.0.11]=coco1
    [192.168.0.12]=coco2
    [192.168.0.13]=coco3
)

PING_COUNT="${PING_COUNT:-3}"                 # echo requests per test
PING_TIMEOUT="${PING_TIMEOUT:-2}"             # seconds to wait per request
FAIL_THRESHOLD="${FAIL_THRESHOLD:-3}"         # consecutive failed PASSES before powercycling
RECOVERY_WAIT="${RECOVERY_WAIT:-120}"         # grace period after powercycle, seconds
MAX_ATTEMPTS="${MAX_ATTEMPTS:-3}"             # powercycles before giving up
LOOP_INTERVAL="${LOOP_INTERVAL:-60}"          # seconds between passes in --loop
# Failure counts live here so they survive between passes AND between runs
# (so cron-driven single passes accumulate correctly). Wipe with --reset.
STATE_DIR="${STATE_DIR:-/tmp/coco-watchdog.state}"
POWERCYCLE_CMD="${POWERCYCLE_CMD:-powercycle}"
# If powercycle is a shell *function* rather than an executable, point this at
# the file that defines it — it gets sourced so the function is in scope here.
# e.g. POWERCYCLE_LIB=/usr/local/lib/pdu-functions.sh
POWERCYCLE_LIB="${POWERCYCLE_LIB:-}"
LOG_FILE="${LOG_FILE:-/tmp/coco-watchdog.log}"
LOOP=0
RESET=0
# ----------------------------------------------------------------------------

while (( $# )); do
    case "$1" in
        --loop)      LOOP=1 ;;
        --once)      LOOP=0 ;;
        --interval)  LOOP_INTERVAL="$2"; shift ;;
        --units)     read -r -a UNITS <<< "$2"; shift ;;
        --lib)       POWERCYCLE_LIB="$2"; shift ;;
        --threshold) FAIL_THRESHOLD="$2"; shift ;;
        --reset)     RESET=1 ;;
        -h|--help)   sed -n '2,12p' "$0"; exit 0 ;;
        *)           echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

log() {
    printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "${*:2}" \
        | tee -a "$LOG_FILE"
}

# Returns 0 if the host answers, 1 otherwise.
is_pingable() {
    ping -c "$PING_COUNT" -W "$PING_TIMEOUT" -q "$1" >/dev/null 2>&1
}

# ---- persistent per-unit state: "fails cycles skip_until" -------------------
# fails      = consecutive failed passes since the last success/powercycle
# cycles     = powercycles issued since the unit was last seen up
# skip_until = epoch seconds; unit is left alone until then (post-reboot boot time)
state_file() {
    printf '%s/%s' "$STATE_DIR" "${1//[^A-Za-z0-9._-]/_}"
}

# Loads into the globals: fails, cycles, skip_until
read_state() {
    local f v
    f="$(state_file "$1")"
    fails=0; cycles=0; skip_until=0
    if [[ -r "$f" ]]; then
        read -r fails cycles skip_until < "$f" || true
    fi
    for v in fails cycles skip_until; do
        [[ "${!v}" =~ ^[0-9]+$ ]] || printf -v "$v" '%s' 0
    done
}

write_state() {
    printf '%s %s %s\n' "$2" "$3" "$4" > "$(state_file "$1")"
}

# One pass over a single unit: test once, update its counters, and powercycle
# only once FAIL_THRESHOLD passes in a row have failed.
check_unit() {
    local unit="$1" target now
    target="${PC_TARGET[$unit]:-$unit}"
    read_state "$unit"
    now="$(date +%s)"

    # Still booting after a powercycle — don't test, don't count.
    if (( now < skip_until )); then
        log SKIP "$unit in post-powercycle grace period ($((skip_until - now))s left)"
        return 0
    fi

    if is_pingable "$unit"; then
        if (( fails > 0 || cycles > 0 )); then
            log RECOVERED "$unit is back (after $fails failed pass(es), $cycles powercycle(s))"
        else
            log OK "$unit is reachable"
        fi
        write_state "$unit" 0 0 0          # any success clears the counters
        return 0
    fi

    (( fails++ ))

    # Not enough consecutive failures yet — just record it and move on.
    if (( fails < FAIL_THRESHOLD )); then
        log FAIL "$unit failed pass $fails/$FAIL_THRESHOLD — not powercycling yet"
        write_state "$unit" "$fails" "$cycles" 0
        return 1
    fi

    # Threshold met, but we have already cycled this unit MAX_ATTEMPTS times.
    if (( cycles >= MAX_ATTEMPTS )); then
        log ALERT "$unit still down after $MAX_ATTEMPTS powercycle(s) — manual intervention needed"
        write_state "$unit" "$fails" "$cycles" 0
        return 1
    fi

    (( cycles++ ))
    log DOWN "$unit failed $FAIL_THRESHOLD consecutive passes — powercycling ($cycles/$MAX_ATTEMPTS)"
    log ACTION "running: $POWERCYCLE_CMD $target"

    if ! "$POWERCYCLE_CMD" "$target" >>"$LOG_FILE" 2>&1; then
        log ERROR "$POWERCYCLE_CMD $target exited non-zero"
    fi

    # Reset the fail count so it needs another full FAIL_THRESHOLD passes
    # before we would cycle again, and hold off testing while it boots.
    write_state "$unit" 0 "$cycles" "$(( now + RECOVERY_WAIT ))"
    log WAIT "$unit left alone for ${RECOVERY_WAIT}s while it boots"
    return 1
}

run_pass() {
    local failed=0
    for unit in "${UNITS[@]}"; do
        check_unit "$unit" || (( failed++ ))
    done
    return "$failed"
}

# --- sanity checks ----------------------------------------------------------
command -v ping >/dev/null 2>&1 || { echo "ping not found" >&2; exit 1; }

# Pull in the powercycle function, if it lives in a separate file. Sourced with
# -u relaxed so a lib written without `set -u` in mind doesn't abort the script.
if [[ -n "$POWERCYCLE_LIB" ]]; then
    if [[ ! -r "$POWERCYCLE_LIB" ]]; then
        echo "cannot read POWERCYCLE_LIB: $POWERCYCLE_LIB" >&2
        exit 1
    fi
    set +u
    # shellcheck source=/dev/null
    . "$POWERCYCLE_LIB"
    set -u
fi

# command -v resolves shell functions as well as executables, so this covers
# both cases. A function only counts if it was defined or sourced above.
if ! command -v "$POWERCYCLE_CMD" >/dev/null 2>&1; then
    echo "error: '$POWERCYCLE_CMD' is not an executable, builtin, or defined function." >&2
    echo "       If it's a shell function, source its file with --lib FILE" >&2
    echo "       or export it from the parent shell with: export -f $POWERCYCLE_CMD" >&2
    exit 1
fi
touch "$LOG_FILE" 2>/dev/null || { echo "cannot write $LOG_FILE" >&2; exit 1; }

mkdir -p "$STATE_DIR" 2>/dev/null || { echo "cannot create $STATE_DIR" >&2; exit 1; }
if (( RESET )); then
    rm -f "$STATE_DIR"/* 2>/dev/null
    log INFO "failure counters reset"
fi

trap 'log INFO "watchdog stopped"; exit 0' INT TERM

log INFO "watchdog started — units: ${UNITS[*]}"

if (( LOOP )); then
    while :; do
        run_pass
        sleep "$LOOP_INTERVAL"
    done
else
    run_pass
    exit $?
fi
