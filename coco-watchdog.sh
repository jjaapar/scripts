#!/usr/bin/env bash
#
# coco-watchdog.sh — ping 192.168.0.11/.12/.13; powercycle anything that's
# down, wait, then re-test.
#
# Usage:
#   ./coco-watchdog.sh              # single pass over all units
#   ./coco-watchdog.sh --loop       # keep monitoring forever
#   ./coco-watchdog.sh --loop --interval 300
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

declare -A PC_TARGET=(
    [192.168.0.11]=coco1
    [192.168.0.12]=coco2
    [192.168.0.13]=coco3
)

PING_COUNT="${PING_COUNT:-3}"                 # echo requests per test
PING_TIMEOUT="${PING_TIMEOUT:-2}"             # seconds to wait per request
RECOVERY_WAIT="${RECOVERY_WAIT:-120}"         # seconds to wait after powercycle
MAX_ATTEMPTS="${MAX_ATTEMPTS:-3}"             # powercycles before giving up
LOOP_INTERVAL="${LOOP_INTERVAL:-30}"          # seconds between passes in --loop
POWERCYCLE_CMD="${POWERCYCLE_CMD:-powercycle}"
# If powercycle is a shell *function* rather than an executable, point this at
# the file that defines it — it gets sourced so the function is in scope here.
# e.g. POWERCYCLE_LIB=/usr/local/lib/pdu-functions.sh
POWERCYCLE_LIB="${POWERCYCLE_LIB:-/opt/hitl-tools/.managefunctions}"
LOG_FILE="${LOG_FILE:-/tmp/coco-watchdog.log}"
LOOP=0
# ----------------------------------------------------------------------------

while (( $# )); do
    case "$1" in
        --loop)      LOOP=1 ;;
        --once)      LOOP=0 ;;
        --interval)  LOOP_INTERVAL="$2"; shift ;;
        --units)     read -r -a UNITS <<< "$2"; shift ;;
        --lib)       POWERCYCLE_LIB="$2"; shift ;;
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

# Ping a unit; on failure powercycle, wait, and retest up to MAX_ATTEMPTS.
check_unit() {
    local unit="$1" attempt=1 target
    target="${PC_TARGET[$unit]:-$unit}"

    while (( attempt <= MAX_ATTEMPTS + 1 )); do
        if is_pingable "$unit"; then
            if (( attempt == 1 )); then
                log OK "$unit is reachable"
            else
                log RECOVERED "$unit came back after $((attempt - 1)) powercycle(s)"
            fi
            return 0
        fi

        if (( attempt > MAX_ATTEMPTS )); then
            break
        fi

        log DOWN "$unit unreachable (attempt $attempt/$MAX_ATTEMPTS)"
        log ACTION "running: $POWERCYCLE_CMD $target"

        if ! "$POWERCYCLE_CMD" "$target" >>"$LOG_FILE" 2>&1; then
            log ERROR "$POWERCYCLE_CMD $target exited non-zero"
        fi

        log WAIT "sleeping ${RECOVERY_WAIT}s before retesting $unit"
        sleep "$RECOVERY_WAIT"
        (( attempt++ ))
    done

    log ALERT "$unit still down after $MAX_ATTEMPTS powercycle(s) — manual intervention needed"
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
