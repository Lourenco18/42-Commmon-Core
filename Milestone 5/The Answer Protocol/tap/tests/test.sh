#!/usr/bin/env bash
# tests/test.sh - Automated, dependency-free test suite for the TAP server.
#
# Uses only bash built-ins (the /dev/tcp pseudo-device) to act as a raw
# TCP client, so `make test` needs nothing beyond the server binary
# itself. Each test opens a connection, sends one or more protocol lines,
# and checks the response against an expected pattern.
#
# Exit code: 0 if every test passed, 1 otherwise. Prints a PASS/FAIL line
# per test and a summary at the end.

set -u
cd "$(dirname "$0")/.."

SERVER_BIN="bin/tap-server"
WORLD_FILE="world/world.json"
PORT=4999
LOG_FILE="logs/test-server.log"

PASS_COUNT=0
FAIL_COUNT=0

# ---------- helpers ----------

log_result() {
    local status="$1" name="$2" detail="${3:-}"
    if [ "$status" = "PASS" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        printf "  \033[32mPASS\033[0m  %s\n" "$name"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        printf "  \033[31mFAIL\033[0m  %s\n" "$name"
        [ -n "$detail" ] && printf "        %s\n" "$detail"
    fi
}

assert_contains() {
    # assert_contains "test name" "haystack" "needle"
    local name="$1" haystack="$2" needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        log_result PASS "$name"
    else
        log_result FAIL "$name" "expected to find: $needle
        got: $(echo "$haystack" | tr '\n' '|')"
    fi
}

# Opens a TCP connection and assigns its fd to the variable named by $1.
open_conn() {
    local __varname="$1"
    local fd
    exec {fd}<>"/dev/tcp/127.0.0.1/$PORT"
    printf -v "$__varname" '%s' "$fd"
}

close_conn() {
    local fd="$1"
    exec {fd}<&-
    exec {fd}>&-
}

send_line() {
    local fd="$1" line="$2"
    printf '%s\n' "$line" >&"$fd"
}

# Reads every line currently available on fd, waiting up to ~0.4s total.
read_all() {
    local fd="$1" out="" line
    while IFS= read -r -t 0.4 -u "$fd" line; do
        out+="$line"$'\n'
    done
    printf '%s' "$out"
}

# ---------- setup ----------

echo "== TAP automated test suite =="

if [ ! -x "$SERVER_BIN" ]; then
    echo "error: $SERVER_BIN not found. Run 'make' first." >&2
    exit 1
fi

mkdir -p logs
: > "$LOG_FILE"

echo "Starting test server on port $PORT ..."
"$SERVER_BIN" --port "$PORT" --world "$WORLD_FILE" --log "$LOG_FILE" >/tmp/tap_test_server_stdout.log 2>&1 &
SERVER_PID=$!

cleanup() {
    kill "$SERVER_PID" >/dev/null 2>&1
    wait "$SERVER_PID" 2>/dev/null
}
trap cleanup EXIT

# wait for the server to be ready (bounded retry loop instead of a fixed sleep)
ready=0
for _ in $(seq 1 30); do
    if (exec 9<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
        exec 9<&- 9>&-
        ready=1
        break
    fi
    sleep 0.2
done
if [ "$ready" -ne 1 ]; then
    echo "error: server did not start listening on port $PORT" >&2
    cat /tmp/tap_test_server_stdout.log >&2
    exit 1
fi
echo "Server is up (pid $SERVER_PID)."
echo

# ---------- test 1: greeting + connect ----------
echo "-- Connection lifecycle --"
open_conn C1
out=$(read_all "$C1")
assert_contains "server sends greeting on connect" "$out" "OK hello proto=1"

send_line "$C1" "CONNECT alice"
out=$(read_all "$C1")
assert_contains "CONNECT succeeds" "$out" "OK connected"

open_conn C_DUP
read_all "$C_DUP" >/dev/null
send_line "$C_DUP" "CONNECT alice"
out=$(read_all "$C_DUP")
assert_contains "duplicate username rejected" "$out" "ERR 201"
close_conn "$C_DUP"

send_line "$C1" "FOOBARBAZ"
out=$(read_all "$C1")
assert_contains "unknown command rejected" "$out" "ERR 902"

echo
echo "-- Not-authenticated guard --"
open_conn C_NOAUTH
read_all "$C_NOAUTH" >/dev/null
send_line "$C_NOAUTH" "LOOK"
out=$(read_all "$C_NOAUTH")
assert_contains "command before CONNECT is rejected" "$out" "ERR 904"
close_conn "$C_NOAUTH"

# ---------- test 2: world exploration ----------
echo
echo "-- World exploration --"
send_line "$C1" "LOOK"
out=$(read_all "$C1")
assert_contains "LOOK returns starting room" "$out" "loc.square"
assert_contains "LOOK lists the village guard" "$out" "npc.guard"

send_line "$C1" "MOVE north"
out=$(read_all "$C1")
assert_contains "MOVE to a valid exit succeeds" "$out" "OK room=loc.tavern"

send_line "$C1" "MOVE up"
out=$(read_all "$C1")
assert_contains "MOVE to a non-existent exit fails" "$out" "ERR 301"

send_line "$C1" "TALK elder"
out=$(read_all "$C1")
assert_contains "TALK to an NPC returns dialogue, not an error" "$out" "OK"

# ---------- test 3: items ----------
echo
echo "-- Item management --"
send_line "$C1" "MOVE south"; read_all "$C1" >/dev/null   # -> square
send_line "$C1" "MOVE north"; read_all "$C1" >/dev/null   # -> tavern
send_line "$C1" "MOVE east"; read_all "$C1" >/dev/null    # -> market
send_line "$C1" "MOVE north"; read_all "$C1" >/dev/null   # -> forest_edge
send_line "$C1" "MOVE east"; read_all "$C1" >/dev/null    # -> forest_clearing

send_line "$C1" "LOOK"
out=$(read_all "$C1")
assert_contains "herbs are present in the forest clearing" "$out" "item.herbs"

send_line "$C1" "TAKE Herbs"
out=$(read_all "$C1")
assert_contains "TAKE by partial display name succeeds" "$out" "OK taken=item.herbs"

send_line "$C1" "LOOK"
out=$(read_all "$C1")
if [[ "$out" != *"item.herbs"* ]]; then
    log_result PASS "item removed from room after TAKE (no duplication)"
else
    log_result FAIL "item removed from room after TAKE (no duplication)" "still present: $out"
fi

send_line "$C1" "INVENTORY"
out=$(read_all "$C1")
assert_contains "INVENTORY lists the taken item" "$out" "item.herbs"

send_line "$C1" "DROP item.herbs"
out=$(read_all "$C1")
assert_contains "DROP succeeds" "$out" "OK dropped=item.herbs"

send_line "$C1" "TAKE item.herbs"
read_all "$C1" >/dev/null  # pick back up for the quest test below

# ---------- test 4: combat ----------
echo
echo "-- Combat system --"
send_line "$C1" "ATTACK goblin"
out=$(read_all "$C1")
assert_contains "ATTACK on a valid enemy returns combat data" "$out" "\"damage\""

# finish the goblin off (fresh HP 30, ~8-15 dmg/hit, so a handful of hits is enough)
victory=0
for _ in $(seq 1 8); do
    send_line "$C1" "ATTACK goblin"
    out=$(read_all "$C1")
    if [[ "$out" == *"\"status\":\"victory\""* ]]; then
        victory=1
        break
    fi
    if [[ "$out" == *"ERR 404"* ]]; then
        # goblin already dead from a previous loop iteration
        victory=1
        break
    fi
done
if [ "$victory" -eq 1 ]; then
    log_result PASS "repeated ATTACK eventually defeats the goblin"
else
    log_result FAIL "repeated ATTACK eventually defeats the goblin" "no victory after 8 attacks: $out"
fi

send_line "$C1" "STATUS"
out=$(read_all "$C1")
assert_contains "STATUS reports hp/max_hp/status fields" "$out" "\"hp\""

send_line "$C1" "ATTACK guard"
out=$(read_all "$C1")
assert_contains "attacking a non-hostile NPC is rejected" "$out" "ERR"

# ---------- test 5: quests ----------
echo
echo "-- Quest system --"
send_line "$C1" "MOVE west"; read_all "$C1" >/dev/null   # -> forest_edge
send_line "$C1" "MOVE south"; read_all "$C1" >/dev/null  # -> market

send_line "$C1" "QUEST merchant"
out=$(read_all "$C1")
assert_contains "requesting a quest assigns it" "$out" "\"status\":\"available\""

send_line "$C1" "QUEST merchant"
out=$(read_all "$C1")
assert_contains "turning in a fetch quest with the item completes it" "$out" "\"status\":\"completed\""

send_line "$C1" "QUESTS"
out=$(read_all "$C1")
assert_contains "QUESTS lists the completed quest" "$out" "fetch_herbs"

send_line "$C1" "QUEST merchant"
out=$(read_all "$C1")
assert_contains "re-requesting a completed quest is rejected" "$out" "ERR 406"

send_line "$C1" "INVENTORY"
out=$(read_all "$C1")
assert_contains "quest reward is granted to inventory" "$out" "item.gold_coin"

# ---------- test 6: chat + groups (two players) ----------
echo
echo "-- Chat and groups (two players) --"
open_conn C2
read_all "$C2" >/dev/null
send_line "$C2" "CONNECT bob"
read_all "$C2" >/dev/null

send_line "$C1" "CHAT GLOBAL hello from alice"
read_all "$C1" >/dev/null
out=$(read_all "$C2")
assert_contains "global chat is broadcast to other players" "$out" "hello from alice"

send_line "$C1" "GROUP CREATE"
out=$(read_all "$C1")
assert_contains "GROUP CREATE succeeds" "$out" "OK group="
GROUP_ID=$(echo "$out" | grep -o 'group\.[0-9]*' | head -1)

send_line "$C1" "GROUP INVITE bob"
read_all "$C1" >/dev/null
out=$(read_all "$C2")
assert_contains "group invite is delivered to the target" "$out" "EVT GROUP INVITE alice"

send_line "$C2" "GROUP JOIN $GROUP_ID"
out=$(read_all "$C2")
assert_contains "GROUP JOIN succeeds with a valid id" "$out" "OK group=$GROUP_ID"

send_line "$C1" "CHAT GROUP secret plan"
read_all "$C1" >/dev/null
out=$(read_all "$C2")
assert_contains "group chat reaches group members only" "$out" "secret plan"

send_line "$C1" "WHO"
out=$(read_all "$C1")
assert_contains "WHO reports player counts" "$out" "\"server\":2"

send_line "$C2" "QUIT"
read_all "$C2" >/dev/null
close_conn "$C2"

send_line "$C1" "QUIT"
out=$(read_all "$C1")
assert_contains "QUIT closes cleanly" "$out" "OK bye"
close_conn "$C1"

# ---------- summary ----------
echo
echo "== Summary: $PASS_COUNT passed, $FAIL_COUNT failed =="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "All tests passed."
    exit 0
else
    echo "Some tests failed. See logs/test-server.log for the server-side trace."
    exit 1
fi
