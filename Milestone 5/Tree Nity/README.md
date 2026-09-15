*This project has been created as part of the 42 curriculum by &lt;your_login&gt;.*

> Replace `<your_login>` above with your actual 42 login(s) (comma-separated
> if there are several) before submitting/evaluating.

# treenity

## Description

`treenity` is a lightweight, topic-based message queue system, built from
scratch in C++17 with no external message-broker libraries. It is made of
two programs:

- **`server`** — a long-running process that owns one or more *topics*
  (append-only message logs), accepts new topics, and routes every
  produced message to every consumer whose subscription prefix matches
  the message's key.
- **`client`** — a single CLI binary with five subcommands that talk to a
  running server: `create`, `list`, `produce`, `subscribe`, `info`.

The goal of the project is to explore inter-process communication,
concurrent server design (one worker per topic, safely sharing state with
a control thread and many producer/consumer sessions), and two small
"from scratch" data structures explicitly required by the subject: a
hand-rolled hashmap for client metadata, and a prefix trie for
routing messages to consumers by key prefix.

A worked example (topic creation, prefix-filtered subscription, message
production, and metadata lookup) is provided in the [Instructions](#instructions)
section below and reproduces the exact example from the subject.

## Instructions

### Requirements

- A Linux system with named-pipe (FIFO) support in `/tmp` (standard on
  any Linux distribution/container).
- `g++` with C++17 support (tested with GCC 13).
- `pthread`.
- For the test suite only: `libgtest` (dev headers + static libs) and
  `python3` (used by the raw-mode integration test to build/parse binary
  frames — the server and client themselves have no Python dependency).

On Debian/Ubuntu, everything needed to build and test can be installed
with:

```sh
sudo apt-get install build-essential libgtest-dev python3
```

### Build

```sh
make          # builds bin/server and bin/client
make re        # full rebuild from scratch
make clean     # remove intermediate build artifacts
make fclean    # remove build artifacts AND the final binaries
```

### Test

```sh
make test
```

This single command builds everything (including the test binaries) and
runs, in order:

1. The GoogleTest unit tests for the prefix trie and the client-metadata
   hashmap (`tests/test_trie.cpp`, `tests/test_hashmap.cpp`).
2. A black-box integration test (`tests/integration_test.sh`) that starts
   a real `bin/server`, drives it purely through `bin/client` exactly as
   an end user would, and checks topic management, produce/subscribe
   flows, prefix filtering, offset resume, `--raw` binary mode, error
   exit codes, and graceful shutdown.

`make test` exits non-zero if any check fails, so it is safe to use in CI.

### Run

Start the server (it prints its IPC identifier and keeps running until
`Ctrl+C` / `SIGTERM`):

```sh
$ ./bin/server
/tmp/operator.server.1337
```

In separate terminals, using the identifier printed above:

```sh
# create a topic
$ ./bin/client /tmp/operator.server.1337 create user_events
topic created

$ ./bin/client /tmp/operator.server.1337 list
user_events

# subscribe (blocks, printing matching messages as they arrive)
$ ./bin/client /tmp/operator.server.1337 subscribe user_events client0 --prefix user.create &
subscribed to user_events

# produce messages (reads "key:body" lines from stdin)
$ ./bin/client /tmp/operator.server.1337 produce user_events <<'EOF'
user.create:{"user":"reach","age":25}
user.update:{"user":"norminet","age":42}
user.delete:{"user":"froz","age":24}
user.create:{"user":"moulinette","age":1337}
EOF

# client0's subscribe process prints:
user.create:{"user":"reach","age":25}
user.create:{"user":"moulinette","age":1337}

# inspect committed offset / metadata
$ ./bin/client /tmp/operator.server.1337 info client0
{"client":"client0","topic":"user_events","offset":4,"prefix":"user.create","ipc":"/tmp/operator.server.1337.client0"}
```

Binary framing (`--raw`) is available on both `produce` and `subscribe`;
see the "Message Formats" behaviour mirrored in `src/client/client.cpp`
for the exact byte layout (4-byte little-endian length prefixes around
raw key/value bytes, plus a leading offset on the consumer side).

### `gitinette`

`gitinette` (at the repository root) is a small guideline checker,
independent of `treenity` itself: it verifies commit messages follow
Conventional Commits, branch names follow `<type>/<name>`, and that
`main`'s history shows a merge-based workflow. Run it with:

```sh
./gitinette --repo . --base-branch main
```

or, for a manual message/diff coherence sample:

```sh
./gitinette --repo . --base-branch main --evaluation --sample 3
```

## Architecture

### Process model

`server` is a single OS process. On startup it creates its main control
FIFO and prints its path (`/tmp/operator.server.<pid>`) to stdout — this
is the *IPC identifier* every `client` invocation needs.

### Threading / routine model

- **One control thread** (the process's `main()`) owns the main FIFO and
  is the only reader of control requests (`CREATE`, `LIST`, `INFO`,
  `SUBSCRIBE`, `PRODUCE`, `DISCONNECT`). It never blocks on client I/O
  for more than the length of one short line, so it stays responsive even
  while other topics are busy delivering backlog.
- **One dedicated worker thread per topic** (`src/server/topic.hpp`,
  `Topic::run()`), as required by the subject. This thread is the *only*
  writer to any consumer FIFO belonging to that topic, so message
  delivery never needs extra locking beyond the topic's own state.
  It wakes on a condition variable whenever a message is produced or a
  consumer (re)subscribes, walks every registered consumer, and — for
  each one — replays every log entry from the consumer's last committed
  offset up to the newest message, forwarding the ones whose key matches
  the consumer's prefix and advancing the offset past every entry
  (matching or not). This single loop transparently handles both "catch
  up a late/resuming consumer" and "push a brand-new live message" with
  no separate code path.
- **One short-lived background thread per producer session and per
  consumer handshake.** Opening a FIFO for writing blocks until a reader
  is present (and vice versa); rather than blocking the control thread
  or a topic's worker thread on that rendezvous, each `SUBSCRIBE`/
  `PRODUCE` request spawns a small detached thread that performs the
  blocking `open()` and then hands the resulting file descriptor to the
  relevant `Topic` (`attach_fd()` for consumers, direct reads for
  producers).
- **One watchdog thread**, started only when shutdown begins, that force
  -exits the process after the subject's 5-second grace period if normal
  shutdown hasn't already finished (see "Graceful shutdown" below).

### Synchronization strategy

- Each `Topic` has its own `std::mutex` guarding its message log
  (`std::vector<Message>`), its consumer map, and its prefix index. Only
  that topic's worker thread and the control thread (when
  registering/removing a consumer, or appending a produced message) ever
  touch it, so contention is limited to one topic at a time — topics are
  fully independent of one another.
- The persisted client-metadata table (`g_client_index`, see
  [Data Structures](#data-structures)) is a single process-wide instance
  of the hand-rolled `HashMap`, which is internally thread-safe (its own
  mutex), because it is written both by the control thread (on
  subscribe) and by every topic's worker thread (each time it advances a
  consumer's committed offset).
- The topics registry itself (`name -> Topic`) is protected by a small
  dedicated `std::mutex` (`g_topics_mu`), taken briefly for `CREATE`,
  `LIST`, and to look up a topic by name for `SUBSCRIBE`/`PRODUCE`.
- Producer and consumer *data* FIFOs are never shared between sessions,
  so there is no risk of interleaved writes there; the only genuinely
  shared channel (the main control FIFO) is written one line at a time,
  and every line is guaranteed by POSIX to be written atomically because
  it is always well under `PIPE_BUF` (4096 bytes on Linux) — see
  [IPC Choice](#ipc-choice).

### Graceful shutdown

On `SIGINT`/`SIGTERM`, the control loop stops accepting new requests and
calls `Topic::stop()` on every topic. Each topic's worker flushes any
remaining backlog to its still-connected consumers, then writes a small
sentinel record (`offset = 0xFFFFFFFF` in `--raw` mode, a single ASCII
`EOT` byte on its own line in text mode) to every connected consumer FIFO
and closes it — this is what makes a `subscribe` process that is blocked
in `read()` wake up and exit(0) instead of hanging forever. A background
watchdog thread guarantees the whole process exits within 5 seconds even
in a pathological case (subject requirement), independent of how long the
per-topic flush takes.

## IPC Choice

**Named pipes (FIFOs)** were chosen over POSIX/System V message queues.

Reasoning:

- Message queues (both POSIX `mq_*` and SysV `msgget`/`msgsnd`) impose a
  fixed maximum message size and a fixed maximum queue depth, both of
  which are typically small by default (POSIX `mq_msgsize` defaults to a
  few KB and usually requires root/`sysctl` changes to raise) and would
  need to be re-tuned per-environment for a message queue meant to carry
  arbitrarily many, variably-sized `--raw` records. FIFOs impose no such
  limit: they are a byte stream, so framing is entirely up to the
  application (see the wire formats in `src/common/protocol.hpp`), and a
  message can be any size the 1024-byte key+body cap allows without any
  kernel tuning.
- FIFOs let each conversation get its own private channel simply by
  picking a path in `/tmp` and calling `mkfifo()` — this maps very
  naturally onto the subject's model of "one dedicated IPC channel per
  subscribed client" and "producers register, then stream messages,"
  without needing to multiplex several logical streams over one
  queue/identifier the way SysV message queues (single integer key) or a
  single POSIX queue would require extra message-type tagging for.
- FIFOs are visible as ordinary filesystem paths, which makes debugging
  (`ls /tmp/operator.server.*`, attaching `strace`/`cat` to a channel)
  and cleanup (`unlink`) straightforward, and matches the example IPC
  identifier format shown in the subject (`/tmp/operator.server.1337`).

### Achieving bidirectional communication over one-way FIFOs

A FIFO is inherently one-directional. `treenity` achieves full
request/response and streaming communication using three kinds of
channel, all built on plain FIFOs:

1. **The main control FIFO** (`/tmp/operator.server.<pid>`) — one
   long-lived, many-writers FIFO. The server opens it `O_RDWR` once at
   startup (so it always has at least one writer — itself — and `read()`
   never returns EOF); every client opens it `O_WRONLY` just long enough
   to write one line and close. Since every field in the protocol is
   drawn from the subject's restricted identifier charset (no spaces),
   and every control line is far under `PIPE_BUF`, concurrent clients
   writing to this shared FIFO never see their requests interleaved.
2. **A private response FIFO**, created by the *client* before sending
   any request that needs an answer (`create`, `list`, `info`,
   `subscribe`, `produce`'s initial handshake). Its path is included as
   the last field of the request line. The server opens it `O_WRONLY`,
   writes exactly one reply line (`OK ...` / `ERR <code> <message>`),
   and closes it; the client's blocking `open(..., O_RDONLY)` naturally
   waits for that. This turns a one-way FIFO into a clean
   request/response round trip without ever needing the server to know
   about a client in advance.
3. **Per-session data FIFOs**, created once a request is approved: a
   producer creates its own `producer_fifo` (server reads from it,
   client writes to it) and a subscribing consumer's dedicated FIFO
   (`<ipc_id>.<client_id>`, matching the subject's example) is created by
   the *server* right before it replies `OK` to `SUBSCRIBE` (so the node
   is guaranteed to exist by the time the client tries to open it for
   reading) and is written to exclusively by that topic's worker thread.

## Data Structures

### Client metadata hashmap

`src/common/hashmap.hpp` implements `treenity::HashMap<Value>`, a
string-keyed hashmap built from scratch (no `std::unordered_map`/
`std::map`, per the subject's constraint on this specific piece of
state):

- **Hash function**: djb2 (`hash = hash*33 + c`), a simple, fast,
  well-distributed string hash that is more than adequate for the short
  (≤32 character) topic/client identifiers this project deals with.
- **Collision resolution**: separate chaining — each bucket is a
  `std::vector` of `{key, value}` entries; a collision simply appends to
  that bucket's vector instead of touching any other bucket.
- **Growth**: the table doubles and every entry is rehashed once the load
  factor exceeds 0.75, keeping average chain length short as more
  clients connect over the server's lifetime.
- **Thread safety**: a single internal `std::mutex` guards every
  operation, since this table is the one piece of state genuinely shared
  between the control thread (writing on `SUBSCRIBE`) and every topic's
  worker thread (writing every time it advances a consumer's committed
  offset).

It is used as `g_client_index` in `server.cpp` to answer `info` and to
resume a returning consumer from its last committed offset.

### Prefix-matching structure

`src/common/trie.hpp` implements a **prefix trie (`PrefixTrie`)** whose
nodes are keyed by character, plus a thin wrapper (`PrefixIndex`) that
also tracks empty-prefix ("wildcard") consumers as a flat list per the
subject's "Direct Addition" rule.

Why a trie rather than, say, a flat list of `(prefix, consumer)` pairs
checked with `starts_with` one by one: a trie turns "find every consumer
whose prefix is a prefix of this message's key" into a single walk over
the key's characters (`O(key length)`), collecting every consumer
registered at any node passed along the way — independent of how many
distinct prefixes are registered in total. A flat list, by contrast,
would need to check every registered consumer against every message
(`O(consumers)` per message), which scales poorly as the number of
consumers on a busy topic grows. The trie also naturally supports several
consumers sharing the same prefix, and prefixes that are themselves
prefixes of other prefixes (e.g. both `"user"` and `"user.create"`
registered at once — see the `NestedPrefixesAllMatchAlongThePath` test),
without any special-casing.

`Topic::run()` (see [Architecture](#architecture)) additionally reuses the
same underlying rule — `treenity::prefix_matches()` — for the
catch-up/replay scan of a single resuming consumer, so "what counts as a
match" is defined in exactly one place and is exercised by both the live
trie-based dispatch and the linear replay path.

## Testing

The prefix-matching structure is unit-tested with GoogleTest in
`tests/test_trie.cpp` (and the hashmap in `tests/test_hashmap.cpp`,
covering the other from-scratch data structure end to end).

- **Build**: `make test` (or, directly, `g++ -std=c++17 -pthread -o
  build/test_trie tests/test_trie.cpp -lgtest -lpthread`). GoogleTest is
  linked as a plain static library (`-lgtest`, plus its bundled `main()`
  substitute defined at the bottom of the test file) — no CMake or
  gtest_discover machinery is required.
- **Coverage**: the free function `prefix_matches()` (exact match, partial
  match, no match, empty-prefix wildcard, prefix-longer-than-key, case
  sensitivity); `PrefixTrie` (basic insert/match, several consumers
  sharing one prefix, nested/overlapping prefixes, removal, removing an
  unknown consumer being a no-op, an empty trie matching nothing, and a
  500-prefix scale test); and `PrefixIndex` (the empty-prefix fast path
  matching everything, removing a wildcard consumer, and a mix of
  wildcard + specific-prefix consumers on the same key).
- **Run**: `./build/test_trie` on its own, or as part of `make test`,
  which runs it (and `test_hashmap`) before the end-to-end integration
  test in `tests/integration_test.sh`, so a broken prefix-matching rule
  is caught immediately rather than surfacing later as a subtly wrong
  message delivery in the full server/client integration test.

## Resources

Classic references consulted while building this project:

- `man 7 fifo`, `man 2 mkfifo`, `man 2 open` — FIFO semantics, blocking
  open()/read()/write() behaviour, and `PIPE_BUF` atomicity guarantees.
- `man 7 pipe` — `PIPE_BUF` value and the atomic-write guarantee for
  writes up to that size, which underpins the "one control line per
  write is safe with concurrent writers" design in [IPC Choice](#ipc-choice).
- `man 2 sigaction`, `man 7 signal` — `SA_RESTART` semantics, used
  deliberately *without* the flag on the client's `subscribe` signal
  handlers so a blocking `read()` returns `EINTR` on `Ctrl+C` instead of
  silently resuming.
- *The Linux Programming Interface*, Michael Kerrisk — background reading
  on named pipes vs. message queues and POSIX threading/synchronization
  primitives.
- [GoogleTest primer](https://google.github.io/googletest/primer.html) —
  test fixture/assertion conventions used in `tests/test_trie.cpp` and
  `tests/test_hashmap.cpp`.
- [Conventional Commits](https://www.conventionalcommits.org/) — the
  commit-message format `gitinette` checks and that this repository's
  history follows.

### AI usage disclosure

An AI assistant (Anthropic's Claude) was used throughout this project as
a hands-on pair-programmer, specifically for:

- Drafting the initial architecture (FIFO-based request/response +
  per-session data channel design, per-topic worker threading model) from
  the subject's requirements, which was then implemented, compiled, and
  iteratively debugged against real runs.
- Writing the first draft of the C++ source in `src/`, the GoogleTest unit
  tests in `tests/`, the integration test script, the `Makefile`, and this
  README, all subsequently compiled and exercised end-to-end (including
  fixing a real bug found this way: blocking reads on the client's
  subscribe loop were silently retrying on `EINTR`, which prevented
  `Ctrl+C` from waking a blocked consumer, until interruptible read
  variants were added).
- Extracting and summarizing the two subject/guideline documents provided
  for this project.

No part of the implementation logic (the protocol, the data structures,
or the concurrency design) was taken from an external codebase; all
prompts, iteration, and final review were done against this project's own
subject and guideline documents.
