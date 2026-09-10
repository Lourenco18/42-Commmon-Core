*This project has been created as part of the 42 curriculum by claude-ai.*

# TAP — The Answer Protocol

A shared-world retro text adventure: a TCP server implementing RFC 42TAP,
a command-line client, and a GTK3 graphical client.

## Description

TAP is a small multiplayer MUD (Multi-User Dungeon). Multiple players
connect over TCP to a single server, explore a persistent-feeling world of
interconnected rooms, chat with each other, fight monsters, and complete
quests given by NPCs. The goal of the project is to implement the full
RFC 42TAP protocol on the server side, and to provide two interchangeable
clients — a CLI and a GUI — that speak that protocol.

The world (`world/world.json`) contains:
- **10 rooms**: an 8-room loop (Village Square → Tavern → Market → Forest
  Edge → Forest Clearing → Cave Entrance → Old Bridge → Riverside → back
  to the Square) plus two optional dead-end branches (Cave Depths and
  Forgotten Ruins).
- **5 NPCs** covering all three required roles: a dialogue NPC (the
  Village Guard), two quest-givers (the Merchant and the Elder), and two
  enemies (a Goblin and a Cave Troll).
- **5 items**, three of which are obtainable in the world (Healing Herbs,
  a Rusty Sword, Frothy Ale) and two of which are quest rewards (a Gold
  Coin and a Goblin Tooth).
- **2 quests**: a fetch quest ("bring me healing herbs") and a defeat
  quest ("kill the goblin").

## Instructions

### Requirements
- Linux with `gcc`, GNU `make`, and `pkg-config`.
- GTK3 development headers for the GUI client (`libgtk-3-dev`).
- Nothing else — the server, world loader, and JSON handling are all
  written from scratch in plain C with no external libraries beyond the
  C standard library, POSIX sockets, and GTK3.

### Quick start
```sh
make deps        # installs libgtk-3-dev, pkg-config, cppcheck, netcat (Debian/Ubuntu)
make              # builds bin/tap-server, bin/tap-cli, bin/tap-gui
make test         # runs the full automated protocol test suite
make run-server   # terminal 1: starts the server on port 4242
make run-client   # terminal 2: starts the CLI client
make run-client-gui  # terminal 3: starts the GUI client
```
All binaries also accept `--help` for their command-line options
(`--port`, `--world`, `--log`, `--host`).

## Resources

- RFC 42TAP (`rfc/protocol-rfc.html`, provided with the assignment) — the
  normative protocol specification this project implements.
- Beej's Guide to Network Programming — general reference for POSIX
  sockets and the `select()` reactor pattern used by the server.
- GTK3 API documentation (docs.gtk.org) — reference for `GtkTextView`,
  `GtkNotebook`, `GIOChannel`/`g_io_add_watch` used by the GUI client.
- json.org — general reference for JSON grammar, used when writing the
  minimal hand-rolled JSON writer/parser in `common/jsonmin.c`.

**How AI was used:** An AI assistant (Claude) was used to draft the
initial implementation of every source file in this repository (server,
world loader, JSON library, CLI client, GUI client, Makefile, test
suite) from the RFC 42TAP specification and this assignment brief. The
AI also compiled and ran the code iteratively against a real server
instance during development, which caught and fixed a real protocol bug
(NPC/item lookups originally required an exact id/name match, which
rejected the RFC's own example commands like `TAKE Herbs` and `TALK
Baker` that use short/partial names — fixed by adding case-insensitive
substring matching against both the id and the display name). Per the
assignment's AI-instructions chapter, treat this generated code as a
**starting point**: read through `server/server.c` and `server/world.c`
in particular, run `make test`, and make sure you can explain every
design decision (documented below) before submitting or presenting it.

## Architecture

The server (`server/server.c`) is a **single-threaded, `select()`-based
reactor**, not a thread-per-client design. All shared state (the list of
connected players, the world's rooms/items/NPCs) lives in plain global
structs. Every command handler runs to completion before the next `select()`
call, so there is only ever one piece of code touching that state at a
time — no mutexes, no data races, no lock-ordering bugs.

This trade-off was chosen deliberately: TAP is a line-based text protocol
where every command handler is O(number of rooms/items/NPCs), i.e.
microseconds of work. A thread pool would add real complexity (locking
every shared structure, or message-passing between threads) to parallelize
work that isn't CPU-bound in the first place — the bottleneck for a text
MUD is network I/O and human typing speed, not computation. `select()`
lets the server handle up to `MAX_CLIENTS` (128) simultaneous connections
on a single core with no locking at all.

Command dispatch (`dispatch()` in `server.c`) is a simple **inline
if/else chain on the uppercased verb**, rather than a table-driven
dispatcher. With 15 top-level commands this reads linearly top-to-bottom
and is easy to follow; a dispatch table would mostly add indirection for
no real benefit at this scale.

Framing: each client connection has a per-player buffer
(`player_t.inbuf`). Incoming bytes are appended to it and every complete
`\n`-terminated line is extracted and dispatched; any partial trailing
line is kept for the next `recv()`. This correctly handles both TCP
fragmentation (a command split across two `recv()` calls) and coalescing
(multiple commands arriving in one `recv()` call).

## Protocol Implementation

The server implements every command, event, and error code from RFC
42TAP. Two clarifications/deviations were needed and are documented here
as required:

1. **`WHO` reply format.** RFC §5.2.2 specifies a bare `OK players=<n>`
   reply. However, the assignment's own example interactions (chapter
   V.5, "NPC interaction and inventory") show `WHO` returning
   `OK { "room": [...], "server": N }` — a richer JSON reply with both
   the room's player list and the server total. Since the GUI client is
   explicitly required to "show counters for players in the room and on
   the server" (chapter V.4), the richer JSON format is strictly more
   useful and is what this server implements. `WHO` therefore does *not*
   use the bare `players=<n>` form from §5.2.2.

2. **Resource name resolution.** RFC §8.3–8.4 says items/NPCs can be
   referenced "by ID or display name". The RFC's own examples go
   further, though: `TAKE Herbs` resolves an item whose id is
   `item.herbs` and whose display name is `Healing Herbs` — `"Herbs"` is
   neither the id nor the full display name, just a recognizable
   fragment of it. This server therefore resolves a query against, in
   order: (1) exact id, (2) exact display name, (3) the id's local part
   after the last `.` (e.g. `goblin` for `npc.goblin`), (4)
   case-insensitive substring match against the display name or that
   local part. This is implemented once in `server/world.c`
   (`resource_matches`) and shared by every command that accepts an item
   or NPC argument (TAKE, DROP, TALK, ATTACK, QUEST).

Two commands beyond the base protocol were added to make combat
non-trivial (see "Combat System" below): **`DEFEND`** and **`FLEE`**.
Both follow the same `OK {...}` / `ERR <code> <NAME>` shape as every
other command. Error codes `407 PLAYER_NOT_FOUND`, `902
UNKNOWN_COMMAND`, `903 BAD_ARGS`, `904 NOT_AUTHENTICATED`, `905
ALREADY_AUTHENTICATED`, and `908 RATE_LIMITED` are also extensions
beyond the RFC's base error table, needed to give meaningful errors for
cases the RFC's table doesn't cover (e.g. sending `LOOK` before
`CONNECT`, or a client flooding the server with commands — see "Server
Logging" below for the abuse-detection mechanism behind `908`).

## Combat System

Design choice, implemented in `cmd_attack`/`cmd_defend`/`cmd_flee` in
`server/server.c`:

- Players start at **100 HP**. Enemy NPCs have a fixed HP defined in
  `world.json` per NPC (Goblin: 30 HP, Cave Troll: 50 HP) — tougher
  enemies simply have a higher `hp` field in the world file.
- `ATTACK <npc>` is **immediately resolved, one round per command** (no
  separate "declare then resolve" step, to keep the protocol simple):
  the attacker deals `8–15` damage to the NPC. If the NPC survives, it
  immediately counter-attacks for `3–10` damage. This is effectively a
  fixed initiative order: **player always acts first**, since the player
  chose to attack.
- `DEFEND` (extension command) may be sent while `in_combat`; the next
  NPC counter-attack against that player is halved. This gives the
  player a way to reduce risk instead of always trading blows.
- `FLEE` (extension command) may be sent while `in_combat`: there is a
  50% chance of escaping unharmed, and a 50% chance the NPC gets one free
  hit (`5–10` damage) as the player disengages.
- If a player's HP reaches 0 (from a counter-attack or a failed flee),
  they **respawn at the world's starting room** (`loc.square`, the
  village square — the designated safe room) **with 50 HP**, per the
  "respawn at a safe location with reduced health" requirement.
- Every combat round, victory, defeat, and flee is logged via the
  structured logger (`combat_round`, `combat_victory`, `combat_defeat`,
  `combat_flee` events) and room-wide victories are also broadcast as a
  `EVT ROOM CHAT server ... has defeated ...` line so other players in
  the room see it happen.
- `STATUS` reports `hp`, `max_hp`, and a derived `status` string:
  `in_combat` (currently fighting), `critical` (<30% HP), `wounded`
  (<70% HP), `healthy`, or `defeated`.

## Quest System

Each quest-giver NPC in `world.json` has an embedded `quest` object with
either a `require_item`/`require_count` pair (fetch quest) or a
`require_kill`/`require_count` pair (defeat quest), plus a
`reward_item`.

The `QUEST <npc>` command doubles as both "ask for a quest" and "turn a
quest in", which keeps the protocol surface small (no separate
`COMPLETE_QUEST` command is needed):

1. **First call** to a given quest-giver: the quest is recorded against
   the player (per-player state, `player_t.quests[]`) and the reply has
   `"status":"available"` along with the quest's description and reward.
2. **Subsequent calls** while the quest is still active: the server
   checks completion —
   - fetch quests: is `require_count` copies of `require_item` in the
     player's inventory? (`inv_count_item`)
   - defeat quests: has the player killed `require_count` copies of
     `require_kill`? (a per-player kill counter, incremented in
     `cmd_attack` on every NPC kill)
   If not yet met, the reply reports `"status":"active"` with a
   `"progress":"have/need"` string. If met, the required items are
   consumed from the inventory (fetch quests only — kills aren't
   "consumed"), the reward item is granted, the quest is marked
   completed, and the reply is `"status":"completed"`.
3. **Further calls** to an already-completed quest return
   `ERR 406 NO_QUEST_AVAILABLE`, matching the RFC's error table.

`QUESTS` (plural) lists every quest the player has ever taken, with live
progress for active ones. Every assignment and completion is logged
(`quest_assigned`, `quest_completed` events).

## World Design

See `world/world.json`. Layout:

```
        Ruins (branch)
          |
Cave Depths (branch)      Square -- Riverside
    |                        |           |
Cave Entrance -- Forest Clearing        Old Bridge
                     |                     |
                Forest Edge -- Market -- Tavern -- Square
```

The **8-room loop** is: Square → Tavern → Market → Forest Edge → Forest
Clearing → Cave Entrance → Old Bridge → Riverside → back to Square,
satisfying "movement must allow a full circuit". **Cave Depths** (off
Cave Entrance) and **Forgotten Ruins** (off Old Bridge) are optional
dead-end branches.

NPC placement: the Village Guard (dialogue) and starting quest-givers
are placed near the village (Square, Market, Tavern) so new players meet
them immediately; the enemies (Goblin, Cave Troll) are placed further
out (Forest Clearing, Cave Depths) so combat is opt-in, not forced on
arrival. Items obtainable in the world are placed near the quest that
needs them (Healing Herbs in the Forest Clearing, next to the Goblin, so
a player naturally picks up both quest-relevant elements on the same
trip); quest-reward items (`obtainable: true` but `room: null`) only
enter the world when a quest is completed, so they can never be found or
duplicated by exploring.

## Server Logging

All logging goes through `common/log.c` (`log_line(level, event,
fields...)`), which writes one **structured JSON line per event** to
both stdout and `logs/server.log` (path configurable via `--log`),
e.g.:
```json
{"ts":"2026-09-03T02:06:16Z","level":"INFO","event":"command_received","player":"alice","ip":"127.0.0.1","line":"MOVE north"}
```
Fields captured include: `connect`/`disconnect` (with IP and timestamp),
`command_received` (every command, with player name and full line),
`response_sent` (every response and error code sent back),
`item_taken`/`item_dropped`, `combat_round`/`combat_victory`/
`combat_defeat`, `quest_assigned`/`quest_completed`, `move`, `respawn`,
and `world_loaded`/`server_started`/`server_stopping` for lifecycle
events. Levels used: `INFO` for normal traffic and state changes, `WARN`
for player defeats and abuse detection, `ERROR` for send failures.

**Abuse detection**: each player has a sliding 5-second command-count
window (`check_rate_limit` in `server.c`). If a player sends more than
30 commands in 5 seconds, an `abuse_detected` `WARN` event is logged
(with IP and command count) and further commands in that window are
rejected with `ERR 908`, giving basic protection against command
flooding without needing an external rate-limiting library.

To monitor a running server: `tail -f logs/server.log | jq .` (or
`grep '"level":"WARN"'` to watch only for defeats/abuse in real time).

## Group Contributions

This repository was produced as a solo/AI-assisted submission for
demonstration purposes; there is a single contributor (`claude-ai`)
responsible for the server, both clients, the world data, and this
documentation. **If you are adapting this project for an actual 2–3
person group submission**, replace this section with a real breakdown,
for example:
- *Learner A*: server (`server/`), protocol compliance, logging.
- *Learner B*: CLI client (`client-cli/`), world design
  (`world/world.json`), quest/combat balancing.
- *Learner C*: GUI client (`client-gui/`), test suite (`tests/`),
  README/documentation.

## Building and Running

Build system: **GNU Make** (see `Makefile` at the repository root).

| Command | What it does |
|---|---|
| `make` / `make all` | Builds `bin/tap-server`, `bin/tap-cli`, `bin/tap-gui` |
| `make deps` | Installs system dependencies via `apt-get` (Debian/Ubuntu) |
| `make run-server` | Runs the server on port 4242 with `world/world.json`, logging to `logs/server.log` |
| `make run-client` | Runs the CLI client, connecting to `127.0.0.1:4242` |
| `make run-client-gui` | Runs the GTK3 GUI client |
| `make lint` | Strict `gcc -Wall -Wextra -Werror` syntax check on every source file, plus `cppcheck` if installed |
| `make test` | Builds everything, then runs `tests/test.sh`, a full black-box protocol test suite |
| `make clean` | Removes build artifacts (`bin/`, stray `.o` files) |
| `make fclean` | `clean` + removes log files |
| `make re` | `fclean` + `all` (full rebuild) |

Running server and clients manually (equivalent to the `make run-*`
targets, useful for custom ports/worlds):
```sh
bin/tap-server --port 4242 --world world/world.json --log logs/server.log
bin/tap-cli --host 127.0.0.1 --port 4242
bin/tap-gui   # host/port/username are entered in the GUI's connection bar
```

## Testing

`make test` is the single entry point and requires nothing but the
compiled server binary — it uses bash's built-in `/dev/tcp` pseudo-device
as a raw TCP client, so there is no extra dependency to install just to
run the tests.

What it does:
1. Builds the project (`make test` depends on `make all`).
2. Starts a **dedicated server instance** on port 4999 (separate from
   whatever you might have running on 4242) using the bundled world, and
   waits (with a bounded retry loop, not a fixed sleep) until it accepts
   connections.
3. Runs 31 assertions across six areas, each printing a `PASS`/`FAIL`
   line: connection lifecycle (greeting, CONNECT, duplicate names,
   unknown commands, pre-auth guard), world exploration (LOOK, MOVE,
   TALK), item management (TAKE/DROP/INVENTORY and no-duplication),
   combat (ATTACK to victory, STATUS fields, attacking a non-hostile
   NPC), the full quest lifecycle (assign → progress → complete →
   reward → re-request rejected), and **two simultaneous connections**
   exercising global/group chat, group create/invite/join, and WHO's
   player counts.
4. Tears the test server down (via a `trap ... EXIT`) and exits 0 only
   if every assertion passed; exits 1 (with a pointer to
   `logs/test-server.log`) otherwise.

To test multiplayer behavior **interactively**: run `make run-server` in
one terminal, then `make run-client` (or `make run-client-gui`) in two
or more other terminals, `CONNECT` with different usernames, and use
`MOVE`/`CHAT ROOM ...` to verify presence/chat events appear live in the
other clients. To test combat/quests interactively: `CONNECT`, walk to
the Forest Clearing (`MOVE north` from the Square, `MOVE east`, `MOVE
north`, `MOVE east`), `TAKE Herbs`, `ATTACK goblin` repeatedly, then
walk back to the Market and `QUEST merchant` to see the fetch quest
complete and grant its reward.
