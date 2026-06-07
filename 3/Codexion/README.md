*This project has been created as part of the 42 curriculum by dasantos.*

# Codexion

## Description

Codexion is a multithreaded simulation in C inspired by the classic **Dining Philosophers** problem, reimagined as coders sitting around a circular table sharing **dongles** (USB licence keys) to compile their code.

N coders sit around a table. Between each adjacent pair lies a shared dongle. To compile, a coder must acquire **both neighbouring dongles**, hold them for the duration of the compile, then release them. If any coder goes too long without starting a compile, they **burn out** and the simulation ends immediately.

A dedicated **monitor thread** checks burnout deadlines and completion in real time. The simulation ends cleanly when every coder has reached the required number of compiles, or abruptly if any coder burns out.

---

## Instructions

### Compilation

```bash
make
```

This produces the `codexion` binary. Object files land in `obj/`.

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

All time values are in **milliseconds**. `scheduler` must be either `fifo` or `edf`.

| Argument                      | Description                                                   |
|-------------------------------|---------------------------------------------------------------|
| `number_of_coders`            | Number of coder threads (≥ 1)                                 |
| `time_to_burnout`             | Max ms a coder may go without starting a compile              |
| `time_to_compile`             | ms spent compiling (holding both dongles)                     |
| `time_to_debug`               | ms spent debugging after each compile                         |
| `time_to_refactor`            | ms spent refactoring after debugging                          |
| `number_of_compiles_required` | Compiles each coder must finish for a clean exit              |
| `dongle_cooldown`             | ms a dongle must rest after being released before reuse       |
| `scheduler`                   | `fifo` (arrival order) or `edf` (earliest deadline first)     |

### Example runs

```bash
# 5 coders, FIFO scheduling — easy test
./codexion 5 1400 200 100 100 3 100 fifo
5      → 5 coders (threads) sentados à mesa
1400   → burns out se passar 1400ms sem começar a compilar
200    → cada compile demora 200ms (segura os dois dongles)
100    → depois de compilar, debuga 100ms
100    → depois de debugar, refactora 100ms
3      → cada coder precisa de 3 compiles para sair com sucesso
100    → após largar um dongle, este precisa de 100ms de cooldown
fifo   → fila por ordem de chegada

# 4 coders, EDF scheduling
./codexion 4 1000 150 100 50 5 80 edf


# Burnout test (burnout must NOT happen here)
./codexion 3 2000 300 100 100 2 50 fifo
```

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

- [POSIX Threads Programming – LLNL](https://hpc-tutorials.llnl.gov/posix/)
- [The Dining Philosophers Problem – Wikipedia](https://en.wikipedia.org/wiki/Dining_philosophers_problem)
- [Earliest Deadline First scheduling – Wikipedia](https://en.wikipedia.org/wiki/Earliest_deadline_first_scheduling)
- [pthread_cond_timedwait(3) man page](https://man7.org/linux/man-pages/man3/pthread_cond_timedwait.3p.html)
- [Valgrind documentation](https://valgrind.org/docs/manual/manual.html)

### AI usage

AI (Claude) was used as a learning and debugging aid throughout this project:

- **Architecture design** – discussing the priority-queue-per-dongle approach and Coffman ordering for deadlock prevention.
- **Concurrency edge cases** – reasoning through race conditions around `stopped` flag propagation and dongle cooldown expiry.
- **Norminette compliance** – reviewing function length and formatting.
- **README writing** – structuring this document.

All code was written and understood by the student; AI was not used to generate production code directly.

---

## Blocking cases handled

| Concurrency issue | Solution |
|---|---|
| **Deadlock** | All coders always acquire the lower-indexed dongle first (Coffman resource ordering). This prevents the circular-wait condition. |
| **Starvation** | A per-dongle priority queue ensures every waiting coder is eventually served. FIFO mode uses arrival timestamps; EDF mode uses burnout deadlines. |
| **Dongle duplication / double-acquire** | Each dongle carries an `in_use` flag checked atomically under its mutex. A coder only proceeds after `pq_peek` confirms it is first in the queue **and** `in_use == 0`. |
| **Burnout race** | The monitor reads deadlines that are only updated inside `do_compile` before the compile sleep. The `stop_mutex` gate ensures the stopped signal propagates atomically to all waiting coders. |
| **Cooldown bypass** | `in_cooldown` is cleared only when `get_time_ms() >= release_time + dongle_cooldown`, checked every time the coder re-evaluates its wait condition. |
| **Log interleaving** | All output goes through `log_state`, which holds `log_mutex` for the entire `printf` call, guaranteeing each log line is atomic. |
| **Graceful shutdown** | When `stopped` is set, `pthread_cond_broadcast` is issued on every dongle, waking all blocked coders so they can observe the flag and exit cleanly. |

---

## Thread synchronization mechanisms

| Primitive | Where used | Purpose |
|---|---|---|
| `pthread_mutex_t` (per dongle) | `dongle.c` | Protects `in_use`, `in_cooldown`, `release_time`, and the waiter priority queue. |
| `pthread_cond_t` (per dongle) | `dongle.c` | Allows waiting coders to sleep until a dongle is released, avoiding busy-waiting. Uses `pthread_cond_timedwait` with a 1 ms timeout to re-check the `stopped` flag. |
| `stop_mutex` | `sim.c`, `monitor.c`, `coder.c` | Single mutex guarding the global `stopped` flag and `burnout_coder_id`; ensures only one thread writes the stop signal. |
| `log_mutex` | `log.c` | Serialises all `printf` calls so log lines never interleave on stdout. |
| `pthread_create` / `pthread_join` | `sim.c` | One thread per coder + one monitor thread. All are joined before `sim_cleanup` frees memory, preventing use-after-free. |
