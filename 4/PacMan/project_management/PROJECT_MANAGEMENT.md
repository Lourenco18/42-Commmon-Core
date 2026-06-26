# Project Management — Pac-Man

## Timeline & Gantt Overview

| Phase | Tasks | Duration |
|-------|-------|----------|
| Analysis | Read subject, decompose requirements, design architecture | Day 1 |
| Core engine | Config loader, maze integration, entities | Days 1–2 |
| Game logic | Level manager, collision, scoring, cheat mode | Days 2–3 |
| UI & Rendering | Pygame renderer, menus, HUD, screens | Days 3–4 |
| Highscores | Persistent system, name entry, top-10 | Day 4 |
| Testing | Unit tests, edge cases, integration smoke tests | Day 5 |
| Packaging | Makefile, requirements, README, itch.io build | Day 6 |

## Actual Progress Tracking

- [x] Subject analysis and architecture design
- [x] Config loader with validation and clamping
- [x] Maze integration using A-Maze-ing package
- [x] Player, Ghost, Pacgum, SuperPacgum entities
- [x] Level state machine (init, update, win/loss)
- [x] Ghost AI (chase + flee with distance heuristic)
- [x] Scoring system
- [x] Cheat mode (I/F/L/B/X keys)
- [x] Pygame renderer (maze, entities, animations)
- [x] All menus (main, pause, highscores, instructions)
- [x] Highscore system (persistent JSON, top 10, name entry)
- [x] Makefile with all required rules
- [x] README with all required sections
- [x] .gitignore, requirements.txt

## Project Analysis & Technical Choices

### Language & Library
Python 3.10+ with **pygame** chosen for the graphical library.
- Pygame provides a familiar and well-documented 2D game loop with event handling, surface drawing, and clock management.
- It is cross-platform and easily installable via pip.

### Architecture choice
A layered architecture was chosen to separate concerns:
1. **Config layer** — reads and validates JSON config with safe defaults.
2. **Domain layer** — pure-Python maze, entities, level logic (no pygame dependency).
3. **Presentation layer** — pygame renderer consumes domain objects.
4. **Controller layer** — `Game` class ties everything together with a state machine.

This makes each component independently testable and replaceable.

### Maze generator
The assigned A-Maze-ing package (`mazegenerator`) is used as-is. `PERFECT=False` is passed to produce Pac-Man-compatible corridors with loops. The first level uses the configured seed; subsequent levels use `random.randint` for variety.

### Highscore storage
JSON was chosen for its simplicity and human-readability. The file is written on game end and loaded on startup. All I/O is wrapped in try/except to tolerate missing or corrupt files.

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| A-Maze-ing package API changes | Low | High | Wrapper in `maze.py` isolates the dependency |
| Maze too large for screen | Medium | Medium | Cell size auto-scales; min window size enforced |
| Config file malformed | High | Low | All values clamped to safe defaults, no crash |
| Highscore file corruption | Medium | Low | Graceful reset to empty list on error |

## Team Organization

Solo project — one developer responsible for all components.
Decisions documented inline in code comments and this file.

## Acceptance Test Plan

| Feature | Test | Expected Result |
|---------|------|-----------------|
| Config loading | Pass valid config | All values parsed correctly |
| Config loading | Pass config with missing keys | Defaults used, no crash |
| Config loading | Pass non-JSON file | Clean error message, exit |
| Maze generation | Generate level 1 | Returns Maze with correct dimensions |
| Player movement | Press arrow keys | Player moves in correct direction |
| Pacgum eating | Player walks onto dot | Dot disappears, score increases |
| Super-pacgum | Player eats power pellet | Ghosts turn blue/edible |
| Ghost eaten | Player eats edible ghost | Ghost enters respawn state, score increases |
| Life loss | Ghost touches player | Life decremented, player respawns |
| Game over | Lives reach 0 | Game-over screen shown |
| Level win | All dots eaten | Next level loads |
| Time out | Timer reaches 0 | Level fails |
| Highscore | Enter name after game | Name + score saved to JSON |
| Cheat: I | Press I | Player becomes invincible |
| Cheat: F | Press F | Ghosts stop moving |
| Cheat: X | Press X | Level immediately won |
| Pause | Press P | Game pauses, resume works |

## Blocking Points & Notes

- The maze bitmask encoding (N/E/S/W passage bits) required careful inspection of the generator's output to determine row/column ordering.
- Pygame must be run in headless mode for CI; display init may require `DISPLAY` env var on Linux.
