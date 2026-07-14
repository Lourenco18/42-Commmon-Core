*This project has been created as part of the 42 curriculum by dasantos.*

# Codexion

## Description

Codexion is a multithreaded simulation in C inspired by the classic **Dining Philosophers** problem, reimagined as coders sitting around a circular co-working table sharing **USB dongles** to compile their quantum code.

N coders sit in a circle. Between each adjacent pair lies a shared dongle. To compile, a coder must acquire **both neighbouring dongles simultaneously**, hold them for the duration of the compile, then release them. If any coder goes too long without starting a compile, they **burn out** and the simulation ends immediately.

A dedicated **monitor thread** checks burnout deadlines and completion in real time. The simulation ends cleanly when every coder has reached the required number of compiles, or abruptly if any coder burns out.

**Key features beyond classic Dining Philosophers:**
- Configurable **dongle cooldown**: each dongle must rest for a set time after being released before it can be taken again.
- Two **scheduling policies**: `fifo` (arrival order) and `edf` (earliest deadline first).
- A custom **min-heap priority queue** per dongle to enforce fair arbitration.
- A separate **monitor thread** for precise burnout detection (≤ 10 ms latency).

---

## Instructions

### Compilation

```bash
make
```

Produces the `codexion` binary. Object files land in `obj/`.

```bash
make clean    # remove object files
make fclean   # remove object files and binary
make re       # full rebuild
```

Compiled with: `-Wall -Wextra -Werror -pthread`

### Execution

```
./codexion number_of_coders time_to_burnout time_to_compile time_to_debug \
            time_to_refactor number_of_compiles_required dongle_cooldown scheduler
```

All time values are in **milliseconds**. `scheduler` must be exactly `fifo` or `edf`.

| Argument                      | Description                                                              |
|-------------------------------|--------------------------------------------------------------------------|
| `number_of_coders`            | Number of coder threads and dongles (1–200)                              |
| `time_to_burnout`             | Max ms a coder may go without **starting** a new compile (1–100000)     |
| `time_to_compile`             | ms spent compiling while holding both dongles (must be < time_to_burnout)|
| `time_to_debug`               | ms spent debugging after each compile (1–100000)                         |
| `time_to_refactor`            | ms spent refactoring after debugging (1–100000)                          |
| `number_of_compiles_required` | Compiles each coder must finish for a clean exit (1–10000)               |
| `dongle_cooldown`             | ms a dongle must rest after being released before reuse (0–100000)       |
| `scheduler`                   | `fifo` (arrival order) or `edf` (earliest deadline first)                |

### Example runs

```bash
# 5 coders, FIFO — standard test, no burnout expected
./codexion 5 1400 200 100 100 3 100 fifo

# 4 coders, EDF scheduling
./codexion 4 1000 150 100 50 5 80 edf

# Single coder edge case (uses 1 dongle only)
./codexion 1 800 200 100 100 2 50 fifo

# Burnout test (time_to_burnout < debug+refactor cycle → burnout)
./codexion 3 200 100 500 500 5 100 fifo
```

### Expected log format

```
0 1 has taken a dongle
2 1 has taken a dongle
2 1 is compiling
202 1 is debugging
402 1 is refactoring
405 2 has taken a dongle
406 2 has taken a dongle
406 2 is compiling
```

Each line: `<elapsed_ms> <coder_id> <state_message>`

Simulation statistics (result, total time, per-coder compile counts) are printed to **stderr** after the simulation ends.

### Memory checking

```bash
# Linux — Valgrind
make memcheck

# macOS — AddressSanitizer + UBSan
make test-mac

# Cross-platform — Valgrind inside Docker
make docker-test
```

---

## Resources

### Documentation & references

- [threading — Thread-based parallelism](https://docs.python.org/3/library/threading.html)
- [Valgrind documentation](https://valgrind.org/docs/manual/manual.html)
- [Binary Heap (min-heap) – Wikipedia](https://en.wikipedia.org/wiki/Binary_heap)

### AI usage

AI (Claude) was used as a learning and debugging aid throughout this project:

- **Architecture design** — discussing the priority-queue-per-dongle approach and Coffman ordering for deadlock prevention.
- **Concurrency edge cases** — reasoning through race conditions around `stopped` flag propagation, dongle cooldown expiry, and burnout detection timing.
- **Norminette compliance** — reviewing function length and formatting constraints.
- **Documentation** — structuring both this README and the full project explanation file.

All code was written and understood by the student. AI was used to clarify concepts and review logic, not to generate production code directly.

---

## Blocking cases handled

| Concurrency issue | How it is handled |
|---|---|
| **Deadlock (circular wait)** | Coffman resource ordering: every coder always acquires the lower-indexed dongle first (`get_dongle_order`). This eliminates the circular-wait Coffman condition. Coder N (whose right dongle has index 0) acquires index 0 before index N-1, matching all other coders' ordering. |
| **Starvation** | A per-dongle min-heap priority queue ensures every waiting coder is eventually served. In FIFO mode the key is the arrival timestamp; in EDF mode it is the burnout deadline. Both guarantees mean every coder in the queue will eventually reach the top. |
| **Dongle double-acquire / race** | The `in_use` flag is read and set atomically inside `d->mutex`. The check `is_my_turn() && !in_use → in_use=1` is a single critical section; no two threads can succeed simultaneously for the same dongle. |
| **Cooldown bypass** | `in_cooldown` is cleared only when `(release_time + dongle_cooldown) - get_time_ms() <= 0`, evaluated every time a coder re-tests `try_acquire` under the dongle mutex. |
| **Burnout timing (≤ 10 ms requirement)** | The monitor polls every 500 µs (`usleep(500)`). Worst-case detection latency is ~0.5 ms, well within the 10 ms requirement. |
| **Burnout false positive during compile** | The burnout check includes `state != STATE_COMPILING`. A coder that has already acquired both dongles and started compiling is not marked as burned out even if the deadline timestamp has passed. |
| **Log interleaving** | All output goes through `log_state`, which holds `log_mutex` for the entire `printf` call. No two log lines can interleave on stdout. |
| **Graceful shutdown** | When `stopped` is set to 1, `pthread_cond_broadcast` is called on every dongle's condition variable. This wakes all coders blocked in `acquire_loop`, which then observe `stopped=1` and exit cleanly. |
| **Thread lifecycle / use-after-free** | All coder threads are joined before `sim_cleanup` frees memory. The monitor thread is joined after the coders. Memory is never freed while any thread could still reference it. |

---

## Thread synchronization mechanisms

### Overview of primitives

| Primitive | Count | Where | Purpose |
|---|---|---|---|
| `pthread_mutex_t` (per dongle) | N | `dongle.c` | Protects `in_use`, `in_cooldown`, `release_time`, and the waiter priority queue of each dongle. |
| `pthread_cond_t` (per dongle) | N | `dongle.c` | Allows waiting coders to sleep until a dongle becomes available, without busy-waiting. Paired with `pthread_cond_timedwait` (1 ms timeout) so coders can periodically re-check `stopped`. |
| `stop_mutex` | 1 | `sim.c`, `monitor.c`, `coder.c` | Guards the global `stopped` flag and `burnout_coder_id`. Ensures only one thread writes the stop signal and all reads are consistent. |
| `log_mutex` | 1 | `log.c` | Serialises all `printf` calls so that stdout lines never interleave. |
| `dongle_order_mutex` | 1 | `coder.c` | Protects the read of `left_dongle` / `right_dongle` in `get_dongle_order`. Ensures the ordering decision is made atomically even if fields are theoretically immutable after init. |

### How race conditions are prevented

**Dongle acquisition race**: two coders could theoretically pass `is_my_turn()` and `!in_use` checks at the same time. This is impossible because both checks and the subsequent `in_use=1` assignment happen inside `d->mutex`. The mutex guarantees mutual exclusion for the entire `try_acquire` function.

**`stopped` flag race**: the monitor writes `stopped=1` while coders read it in `sim_is_stopped`. Both operations are protected by `stop_mutex`, so no torn reads or writes occur.

**Deadline update race**: `coder->deadline` is written only by the coder's own thread (in `do_compile`) and read by the monitor thread. Because each coder's deadline is written once per compile cycle and the monitor only needs an approximate value for detection, no mutex is needed here — the worst case is a 1-cycle stale read, which cannot cause false burnout given the 10 ms tolerance.

### Thread-safe communication between coders and monitor

The monitor does not communicate directly with coders. The shared communication channel is the `t_sim` state:

1. **Coder → Monitor**: coders update `coder->state`, `coder->last_compile_start`, and `coder->compile_count`. The monitor reads these to detect burnout and completion.
2. **Monitor → Coders**: the monitor writes `sim->stopped = 1` under `stop_mutex`, then calls `pthread_cond_broadcast` on every dongle. Coders blocked in `acquire_loop` wake up, read `stopped` under `stop_mutex`, and exit.

This one-way signalling through a shared flag + broadcast is the standard POSIX pattern for graceful thread shutdown. No direct inter-thread messaging or pipes are needed.

### `pthread_cond_timedwait` usage

```c
// dongle_utils.c — wait_one_ms()
gettimeofday(&tv, NULL);
ts.tv_sec  = tv.tv_sec;
ts.tv_nsec = tv.tv_usec * 1000LL + 1000000LL;  // +1 ms
if (ts.tv_nsec >= 1000000000LL) { ts.tv_sec++; ts.tv_nsec -= 1000000000LL; }
pthread_cond_timedwait(&d->cond, &d->mutex, &ts);
```

The 1 ms timeout means that even without a `broadcast`, a waiting coder will re-evaluate the dongle state at least every millisecond. This prevents permanent blocking after `stopped` is set and ensures cooldown expiry is noticed promptly.