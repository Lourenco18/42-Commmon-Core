# Codexion

A multithreaded simulation in C inspired by the classic **Dining Philosophers** problem — reimagined as coders sitting around a table, sharing **dongles** (USB licence keys) to compile their code.

Each coder needs two dongles (one on each side) to compile. If a coder goes too long without compiling, they **burn out** and the simulation ends.

---

## Concept

N coders sit around a circular table. Between each adjacent pair lies a shared dongle. To compile, a coder must acquire both neighbouring dongles, use them for the duration of the compile, then release them. After compiling, each coder debugs and refactors before trying again.

A monitor thread watches every coder's deadline in real time. If any coder fails to start a compile before their deadline, they burn out and the simulation stops immediately.

---

## Features

- **Deadlock-free** by always acquiring the lower-indexed dongle first (Coffman ordering).
- **Two scheduling policies** for dongle access:
  - `fifo` — coders are served in arrival order.
  - `edf` — Earliest Deadline First; the coder closest to burning out gets priority.
- **Dongle cooldown** — a configurable delay between a dongle being released and it being available again, preventing starvation.
- **Priority queue (min-heap)** per dongle to manage waiting coders efficiently.
- **Precise timing** using `gettimeofday` with millisecond resolution.
- Clean resource management: all threads are joined and all memory freed on exit.

---

## Requirements

- C compiler with POSIX thread support (`-pthread`)
- `make`
- Linux or macOS

Optional for leak checking: `valgrind` (Linux) or AddressSanitizer (macOS).

---

## Build

```bash
make
```

This produces the `codexion` executable. Object files are placed in `obj/`.

```bash
make clean     # remove object files
make fclean    # remove object files and binary
make re        # full rebuild
```

---

## Usage

```
./codexion n_coders time_to_burnout time_to_compile time_to_debug \
           time_to_refactor n_compiles_required dongle_cooldown scheduler
```

All time values are in **milliseconds**.

| Argument             | Description                                                    |
|----------------------|----------------------------------------------------------------|
| `n_coders`           | Number of coders (≥ 1)                                        |
| `time_to_burnout`    | Max time a coder can go without compiling before burning out  |
| `time_to_compile`    | Time spent compiling (while holding both dongles)             |
| `time_to_debug`      | Time spent debugging after a compile                          |
| `time_to_refactor`   | Time spent refactoring after debugging                        |
| `n_compiles_required`| How many compiles each coder must complete for success        |
| `dongle_cooldown`    | Cooldown period after a dongle is released before reuse       |
| `scheduler`          | Scheduling policy: `fifo` or `edf`                            |

### Examples

```bash
# 5 coders, 800ms burnout threshold, FIFO scheduling
./codexion 5 800 200 100 50 3 100 fifo

# 4 coders, 600ms burnout threshold, EDF scheduling
./codexion 4 600 150 100 50 5 80 edf

# Edge case: single coder
./codexion 1 1000 200 100 50 3 0 fifo
```

---

## Output

Each log line is printed to stdout in the format:

```
<timestamp_ms> <coder_id> <event>
```

Events: `is compiling`, `is debugging`, `is refactoring`, `has taken a dongle`, `burned out`.

Example:
```
0 3 has taken a dongle
1 3 has taken a dongle
1 3 is compiling
201 3 is debugging
301 3 is refactoring
351 1 has taken a dongle
...
```

---

## Testing & Sanitizers

**AddressSanitizer + UBSan (macOS / Clang):**
```bash
make test-mac
```

**Valgrind (Linux):**
```bash
make memcheck
```

**Docker (cross-platform, runs Valgrind inside Ubuntu):**
```bash
make docker-test
```

Install build dependencies automatically:
```bash
make install
```

---

## File Structure

```
Codexion/
├── codexion.h       # All structs, constants, and function prototypes
├── main.c           # Entry point
├── args.c           # Argument parsing and validation
├── sim.c            # Simulation init, run loop, and cleanup
├── coder.c          # Coder thread logic (wait → compile → debug → refactor)
├── dongle.c         # Dongle acquire/release with priority queue and cooldown
├── monitor.c        # Monitor thread: checks burnout and completion
├── pqueue.c         # Min-heap priority queue implementation
├── log.c            # Thread-safe timestamped logging
├── time_utils.c     # get_time_ms() and sleep_ms() helpers
└── Makefile
```

---

## How It Works

1. **Startup** — `sim_init` allocates N coders and N dongles, initialises mutexes and condition variables, and sets each coder's initial deadline.
2. **Threads** — One thread per coder plus one monitor thread are launched.
3. **Compiling** — A coder acquires its two dongles (lower index first), sleeps for `time_to_compile`, then releases both.
4. **Dongle scheduling** — Each dongle holds a min-heap of waiting coders. In `fifo` mode the key is arrival time; in `edf` mode it is the coder's deadline. The coder at the top of the heap is granted access first.
5. **Cooldown** — After release, a dongle enters a cooldown period to prevent the same coder from immediately reacquiring it.
6. **Monitor** — Every 0.5 ms the monitor checks whether all coders have hit `n_compiles_required` (clean exit) or whether any coder has missed their deadline (burnout).