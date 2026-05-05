*This project has been created as part of the 42 curriculum by dasantos.*

# Fly-in — Drone Routing Simulation

## Description

**Fly-in** is a drone fleet routing simulator. Given a network of connected zones and a fleet of drones, the system finds the most efficient paths to move all drones from a single start zone to a single end zone in the fewest possible simulation turns.

The problem is modelled as a weighted graph where zones have types (`normal`, `restricted`, `priority`, `blocked`), capacities, and connections have link-capacity constraints. The simulator runs a turn-by-turn discrete simulation enforcing all movement, occupancy, and capacity rules.

---

## Instructions

### Requirements

- Python 3.10 or later
- `flake8` and `mypy` (installed via `make install`)

### Installation

```bash
make install
```

### Running

```bash
make run MAP=maps/easy/01_linear_path.txt

python main.py maps/easy/01_linear_path.txt

python main.py maps/easy/01_linear_path.txt --no-color
```

### Debug mode

```bash
make debug MAP=maps/easy/01_linear_path.txt
```

### Lint

```bash
make lint       
make lint-strict
```

### Clean

```bash
make clean
```

---

## Algorithm Choices and Implementation Strategy

### Graph Representation

The graph is implemented from scratch without any external graph library (networkx, graphlib, etc. are forbidden). It consists of:

- `Zone` — a node with type, coordinates, color, capacity (`max_drones`), and runtime occupancy counter.
- `Connection` — a bidirectional edge with a link capacity (`max_link_capacity`) and runtime usage counter.
- `Graph` — holds all zones and connections, exposes `neighbors()`, `get_connection()`, and `reset_capacities()`.

### Pathfinding — A\* with Yen's K-Shortest Paths

The `Pathfinder` class implements two algorithms:

**1. A\* (`find_path`)**  
Standard A* with Euclidean distance as the heuristic. Movement costs follow zone types: `normal` = 1, `restricted` = 2, `priority` = 1, `blocked` = ∞ (skipped). This finds the single cheapest path.

**2. Yen's K-Shortest Paths (`find_k_shortest_paths`)**  
Built on top of A\*, this enumerates up to `k` distinct loopless paths by iteratively applying spur-node exploration with connection and node blocking. Paths are ranked by total cost and deduplicated. This enables drones to spread across multiple routes and avoid congestion.

**Complexity**: A\* runs in O((V + E) log V). Yen's algorithm runs k iterations of A\*, so O(kV(V + E) log V) in the worst case.

### Simulation Engine

`Simulator` runs a turn-based loop:

1. **Path assignment** — each drone is assigned a path from the k-shortest list in round-robin order, spreading traffic across available routes.
2. **Turn execution** in 4 phases:
   - **Intention** — each drone computes its desired next move based on its remaining path.
   - **Conflict detection** — count incoming drones per zone and per connection.
   - **Greedy approval** — approve moves in drone-ID order, respecting zone capacity (`max_drones`) and link capacity (`max_link_capacity`). Drones that cannot move wait in place.
   - **State update** — apply approved moves, update occupancy counters, mark delivered drones.
3. **Restricted zones** — moving into a `restricted` zone takes 2 turns. On the first turn the drone "enters the connection" (logged as `D<id>-<conn_name>`); on the second turn it arrives. A drone committed to a restricted-zone transit **must** complete it and cannot wait on the connection.
4. The simulation ends when all drones are delivered.

**Caching**: Paths are computed once at startup and reused throughout the simulation. No re-planning per turn.

**Deadlock avoidance**: The greedy approval phase prevents capacity violations. Because paths are pre-computed and drones wait when blocked rather than reversing, the risk of cyclic deadlock is low; the 10 000-turn safety limit is a backstop.

### Complexity Summary

| Component | Complexity |
|-----------|-----------|
| Parsing | O(L) — L lines in input |
| A\* pathfinding | O((V + E) log V) |
| Yen's k-paths | O(k · V · (V + E) log V) |
| Simulation loop | O(T · D) — T turns, D drones |

Memory usage is O(V + E + k · P) where P is average path length.

---

## Visual Representation

The `Display` class provides colored terminal output using ANSI escape codes (disabled with `--no-color`).

**Header** — on startup, a banner shows the number of drones, start/end zone names, zone and link counts, and a zone-type color legend:
- `[normal]` — white
- `[restricted]` — red
- `[priority]` — green
- `[blocked]` — gray

**Per-turn output** — each turn is printed with a cyan turn number prefix `T  N |`. Each drone movement token is colored:
- Drone ID (e.g., `D1`) — cyan
- Destination zone — colored by zone type or by the zone's own `color` attribute from the map file
- Connection names (in-transit toward restricted) — orange

**Mandatory output** — after the colored simulation, the plain `D<ID>-<zone>` format is printed verbatim (the format the subject requires for evaluation).

**Statistics** — at the end: total turns, drones routed, and average drones moved per turn.

---

## Resources

### Algorithm References

- Hart, P.E., Nilsson, N.J., Raphael, B. (1968). *A Formal Basis for the Heuristic Determination of Minimum Cost Paths.* — foundational A\* paper.
- Yen, J.Y. (1971). *Finding the K Shortest Loopless Paths in a Network.* Management Science, 17(11). — basis for the k-shortest paths implementation.
- Python `heapq` documentation: https://docs.python.org/3/library/heapq.html

### Tools & Standards

- flake8: https://flake8.pycqa.org/
- mypy: https://mypy.readthedocs.io/
- PEP 257 (docstrings): https://peps.python.org/pep-0257/
- PEP 484 (type hints): https://peps.python.org/pep-0484/

### AI Usage

AI (Claude) was used in this project for the following tasks:

- **Initial structure brainstorming** — discussing which classes to create and how to organise the OOP hierarchy before writing any code.
- **Yen's algorithm review** — validating that the spur-node logic correctly blocks previously used edges and nodes.
- **ANSI color mapping** — suggesting the color-code table in `display.py`.
- **Docstring and type-hint completeness checks** — verifying that all public methods had proper signatures.

All generated suggestions were reviewed, tested, and adapted by the author. No code was copied without understanding. The final implementation is the result of iterative peer review and manual testing against all provided map files.