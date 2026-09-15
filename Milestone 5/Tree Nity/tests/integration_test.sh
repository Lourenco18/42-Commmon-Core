#!/usr/bin/env bash
# integration_test.sh
#
# Black-box end-to-end test of the server/client pair, driven purely
# through the command-line interface described in the subject (chapter
# VIII), exactly the way an evaluator's test binaries would use it.
#
# Run via `make test` (which also runs the gtest unit tests first). Can
# also be run directly: ./tests/integration_test.sh
#
# Exit code 0 = every check passed, 1 = at least one failed.

set -u
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR_NAME="${BIN_DIR:-bin}"
SERVER="$ROOT_DIR/$BIN_DIR_NAME/server"
CLIENT="$ROOT_DIR/$BIN_DIR_NAME/client"
WORKDIR="$(mktemp -d /tmp/treenity_test.XXXXXX)"

PASS=0
FAIL=0
SERVER_PID=""

log()  { printf '  %s\n' "$*"; }
ok()   { PASS=$((PASS+1)); printf '  [PASS] %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  [FAIL] %s\n' "$*"; }

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -TERM "$SERVER_PID" 2>/dev/null
        for _ in $(seq 1 20); do
            kill -0 "$SERVER_PID" 2>/dev/null || break
            sleep 0.1
        done
        kill -9 "$SERVER_PID" 2>/dev/null
    fi
    jobs -p | xargs -r kill -9 2>/dev/null
    rm -rf "$WORKDIR"
    rm -f /tmp/operator.server.* 2>/dev/null
}
trap cleanup EXIT INT TERM

assert_eq() {
    # assert_eq <description> <expected> <actual>
    if [ "$2" = "$3" ]; then ok "$1"; else
        bad "$1 (expected [$2], got [$3])"
    fi
}

assert_exit() {
    # assert_exit <description> <expected_code> <actual_code>
    if [ "$2" = "$3" ]; then ok "$1"; else
        bad "$1 (expected exit $2, got $3)"
    fi
}

# --- build check -----------------------------------------------------------
if [ ! -x "$SERVER" ] || [ ! -x "$CLIENT" ]; then
    echo "integration_test: server/client not built, run 'make' first" >&2
    exit 1
fi

# --- start server ------------------------------------------------------------
echo "== starting server =="
"$SERVER" > "$WORKDIR/server.out" 2>"$WORKDIR/server.err" &
SERVER_PID=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/server.out" ] && break
    sleep 0.1
done
IPC=$(cat "$WORKDIR/server.out")
if [ -z "$IPC" ] || ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "integration_test: server failed to start" >&2
    cat "$WORKDIR/server.err" >&2
    exit 1
fi
log "server ipc identifier: $IPC"

# --- topic management --------------------------------------------------------
echo "== topic management =="
out=$("$CLIENT" "$IPC" create user_events); rc=$?
assert_eq "create prints confirmation" "topic created" "$out"
assert_exit "create exits 0" 0 "$rc"

"$CLIENT" "$IPC" create orders >/dev/null 2>&1

out=$("$CLIENT" "$IPC" create user_events 2>"$WORKDIR/e1"); rc=$?
assert_exit "duplicate create exits 2" 2 "$rc"

out=$("$CLIENT" "$IPC" list); rc=$?
if echo ",$out," | grep -q ",user_events," && echo ",$out," | grep -q ",orders,"; then
    ok "list contains both created topics"
else
    bad "list contains both created topics (got [$out])"
fi

out=$("$CLIENT" /tmp/nonexistent.ipc.path list 2>"$WORKDIR/e2"); rc=$?
assert_exit "bad ipc identifier exits 1" 1 "$rc"

out=$("$CLIENT" "$IPC" produce no_such_topic </dev/null 2>"$WORKDIR/e3"); rc=$?
assert_exit "produce to missing topic exits 2" 2 "$rc"

# --- produce / subscribe / prefix filtering (subject's worked example) -----
echo "== produce / subscribe / prefix filtering =="
"$CLIENT" "$IPC" subscribe user_events client0 --prefix user.create \
    > "$WORKDIR/sub.out" 2>"$WORKDIR/sub.err" &
SUB_PID=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/sub.out" ] && break
    sleep 0.1
done

printf 'user.create:{"user":"reach","age":25}\nuser.update:{"user":"norminet","age":42}\nuser.delete:{"user":"froz","age":24}\nuser.create:{"user":"moulinette","age":1337}\n' \
    | "$CLIENT" "$IPC" produce user_events
sleep 0.5

expected=$'subscribed to user_events\nuser.create:{"user":"reach","age":25}\nuser.create:{"user":"moulinette","age":1337}'
actual=$(cat "$WORKDIR/sub.out")
assert_eq "prefix filter delivers only matching messages, in order" "$expected" "$actual"

out=$("$CLIENT" "$IPC" info client0); rc=$?
assert_eq "info reports offset past the last topic message" \
    '{"client":"client0","topic":"user_events","offset":4,"prefix":"user.create","ipc":"'"$IPC"'.client0"}' "$out"

kill -TERM "$SUB_PID" 2>/dev/null
wait "$SUB_PID" 2>/dev/null

# --- duplicate consumer name -------------------------------------------------
echo "== duplicate consumer rejection =="
"$CLIENT" "$IPC" subscribe user_events dupclient > "$WORKDIR/dup1.out" 2>&1 &
DUP_PID=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/dup1.out" ] && break
    sleep 0.1
done
out=$("$CLIENT" "$IPC" subscribe user_events dupclient --prefix x 2>"$WORKDIR/dup2.err"); rc=$?
assert_exit "second subscribe with same name exits 2" 2 "$rc"
kill -TERM "$DUP_PID" 2>/dev/null
wait "$DUP_PID" 2>/dev/null

# --- resume from committed offset -------------------------------------------
echo "== resume from committed offset =="
"$CLIENT" "$IPC" create resume_topic >/dev/null
printf 'a:1\nb:2\nc:3\n' | "$CLIENT" "$IPC" produce resume_topic
"$CLIENT" "$IPC" subscribe resume_topic rc0 > "$WORKDIR/rc0.out" 2>&1 &
RC0=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/rc0.out" ] && [ "$(wc -l < "$WORKDIR/rc0.out")" -ge 4 ] && break
    sleep 0.1
done
kill -TERM "$RC0" 2>/dev/null
wait "$RC0" 2>/dev/null
sleep 0.2
printf 'd:4\ne:5\n' | "$CLIENT" "$IPC" produce resume_topic
"$CLIENT" "$IPC" subscribe resume_topic rc0 > "$WORKDIR/rc0b.out" 2>&1 &
RC0B=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/rc0b.out" ] && [ "$(wc -l < "$WORKDIR/rc0b.out")" -ge 3 ] && break
    sleep 0.1
done
kill -TERM "$RC0B" 2>/dev/null
wait "$RC0B" 2>/dev/null
expected=$'subscribed to resume_topic\nd:4\ne:5'
actual=$(cat "$WORKDIR/rc0b.out")
assert_eq "a returning consumer resumes after its last committed offset" "$expected" "$actual"

# --- raw binary mode ----------------------------------------------------------
echo "== raw binary mode =="
"$CLIENT" "$IPC" create raw_topic >/dev/null
"$CLIENT" "$IPC" subscribe raw_topic rawc --raw > "$WORKDIR/raw.out" 2>&1 &
RAW_PID=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/raw.out" ] && break
    sleep 0.1
done
python3 "$ROOT_DIR/tests/raw_helpers.py" produce "$CLIENT" "$IPC" raw_topic \
    alpha:one beta:two "alpha.sub:three"
sleep 0.4
kill -TERM "$RAW_PID" 2>/dev/null
wait "$RAW_PID" 2>/dev/null
if python3 "$ROOT_DIR/tests/raw_helpers.py" check "$WORKDIR/raw.out" \
    "0:alpha:one" "1:beta:two" "2:alpha.sub:three"; then
    ok "raw mode round-trips offset/key/value correctly"
else
    bad "raw mode round-trips offset/key/value correctly"
fi

# --- graceful shutdown wakes a blocked consumer -----------------------------
echo "== graceful shutdown wakes blocked consumers =="
"$CLIENT" "$IPC" create idle_topic >/dev/null
"$CLIENT" "$IPC" subscribe idle_topic idlec > "$WORKDIR/idle.out" 2>&1 &
IDLE_PID=$!
for _ in $(seq 1 50); do
    [ -s "$WORKDIR/idle.out" ] && break
    sleep 0.1
done
kill -TERM "$SERVER_PID"
consumer_exited=1
for _ in $(seq 1 50); do
    if ! kill -0 "$IDLE_PID" 2>/dev/null; then consumer_exited=0; break; fi
    sleep 0.1
done
if [ "$consumer_exited" = 0 ]; then
    ok "blocked subscriber exits once the server shuts down"
else
    bad "blocked subscriber exits once the server shuts down (still running after 5s)"
    kill -9 "$IDLE_PID" 2>/dev/null
fi
server_exited=1
for _ in $(seq 1 60); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then server_exited=0; break; fi
    sleep 0.1
done
if [ "$server_exited" = 0 ]; then
    ok "server exits after SIGTERM"
else
    bad "server exits after SIGTERM"
fi
SERVER_PID=""

echo
echo "================================================================"
echo "  integration tests: $PASS passed, $FAIL failed"
echo "================================================================"
[ "$FAIL" -eq 0 ]
