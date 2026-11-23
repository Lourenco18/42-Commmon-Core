# Timeline, Kanban, and Progress Tracking

## 1. Project Timeline (Gantt Chart)

The project was structured into seven sequential and overlapping work packages across six days:

```text
Work Package                  | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 | Day 6 |
------------------------------|-------|-------|-------|-------|-------|-------|
1. Subject & Architecture     | ████  |       |       |       |       |       |
2. Config & Maze Integration  | ████  | ████  |       |       |       |       |
3. Entities & OOP Hierarchy   |       | ████  | ████  |       |       |       |
4. Level Loop, AI & Cheats    |       |       | ████  | ████  |       |       |
5. Renderer, UI & Highscores  |       |       |       | ████  | ████  |       |
6. QA, Linting & Docstrings   |       |       |       |       | ████  | ████  |
7. Packaging & Itch.io Deploy |       |       |       |       |       | ████  |
```

---

## 2. Planned vs. Actual Progress Comparison

| Milestone | Planned Window | Actual Completion | Status | Variance & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **M1: Subject Analysis & Repo Setup** | Day 1 (AM) | Day 1 (AM) | Completed | On schedule; established folder layout, `Makefile`, and `.gitignore`. |
| **M2: Config Loader & CLI Guard** | Day 1 (PM) | Day 1 (PM) | Completed | On schedule; added `#` and `//` comment stripping and clamping ranges. |
| **M3: `A-Maze-ing` Adapter** | Day 2 (AM) | Day 2 (PM) | Completed | +0.5 day; extra inspection needed to verify wall bitmask polarity (`N/E/S/W`). |
| **M4: Entities & Level Mechanics** | Day 2–3 | Day 3 (PM) | Completed | On schedule; later refactored into `Entity` and `Collectible` base classes on Day 5. |
| **M5: Ghost AI & Scoring** | Day 3 (PM) | Day 4 (AM) | Completed | +0.5 day; implemented 4 distinct target behaviors (Blinky, Pinky, Inky, Clyde). |
| **M6: UI Screens & Highscores** | Day 4 | Day 4 (PM) | Completed | On schedule; implemented all required menus, HUD, sprites, and JSON persistence. |
| **M7: Cheat Mode & Edge-Case QA** | Day 5 | Day 5 (PM) | Completed | On schedule; added BFS spawn search for central `"42"` walls and `Shift+C` cheats. |
| **M8: Docstrings, Lint & Packaging** | Day 6 | Day 6 (PM) | Completed | On schedule; verified `flake8`, `mypy`, PyInstaller bundle, and Itch.io release. |

---

## 3. Final Kanban Board Snapshot

### Done
- [x] Decompose subject requirements and define 4-layer architecture
- [x] Implement CLI argument validation and top-level traceback suppression (`pac-man.py`)
- [x] Build JSON config parser with comment filtering, clamping, and safe defaults (`src/config.py`)
- [x] Integrate external `mazegenerator` wheel unmodified with `perfect=False` (`src/maze.py`)
- [x] Refactor shared movement and wall-collision rules into `Entity` and `Collectible` (`src/entities.py`)
- [x] Implement level progression (10+ levels), timers, collisions, and cheat controls (`src/level.py`)
- [x] Implement persistent Top-10 JSON highscore system with strict name/score validation (`src/highscore.py`)
- [x] Build Pygame renderer with sprite loading, fallback primitives, and all UI views (`src/renderer.py`, `src/game.py`)
- [x] Add PEP 257 docstrings and pass `flake8` and `mypy` checks
- [x] Package standalone build via `pacman.spec` / `make package` and publish to Itch.io

### In Progress
- [ ] Final live rehearsal of the 1-minute project management pitch prior to defense

### Backlog (Post-Evaluation Enhancements)
- [ ] Optional chiptune sound effects toggle
- [ ] Custom sprite themes selectable via configuration