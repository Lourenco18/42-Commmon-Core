# Acceptance Test Plan and Verification Log

## 1. Functional & Non-Functional Test Matrix

Every item below was executed prior to submission and maps directly to the 42 evaluation scale:

| ID | Category | Test Case | Steps / Input | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T01** | **CLI Usage** | Missing or extra CLI arguments | Run `python3 pac-man.py` or pass 2 arguments | Prints usage message and exits cleanly (no traceback) | PASS |
| **T02** | **CLI Usage** | Non-existent or invalid JSON file | Run `python3 pac-man.py missing.json` or corrupt JSON | Prints clear error message to `stderr` and exits cleanly | PASS |
| **T03** | **Config** | Comments & unknown keys | Add `#`, `//` comments and `"extra_key": 123` to `config.json` | Comments stripped, unknown keys ignored, game runs normally | PASS |
| **T04** | **Config** | Out-of-range / invalid values | Set `"lives": -5`, `"pacgum": "abc"`, `< 10` levels | Values clamped to `INT_CLAMPS`, warnings logged, 10 levels ensured | PASS |
| **T05** | **Maze Gen** | Deterministic Level 1 vs. random Level 2+ | Start two new games with `seed: 42`, skip to Level 2 | Level 1 layout is identical; Level 2 layout differs | PASS |
| **T06** | **Maze Gen** | Package re-installation check | Reinstall `mazegenerator-2.1.0-py3-none-any.whl` via `pip` | Game runs identically without any modification to the wheel | PASS |
| **T07** | **Player** | 4-directional movement & wall blocking | Move with Arrow keys and WASD against maze walls | Smooth corridor movement; player never crosses walls | PASS |
| **T08** | **Items** | Pacgum and Super-Pacgum collection | Eat regular dots and corner power pellets | Score increases by configured points; ghosts turn blue/edible | PASS |
| **T09** | **Ghosts** | Chase, flee, eaten, and respawn cycle | Observe normal chase, eat super-pacgum, eat blue ghost | Ghosts flee when edible; eyes return to corner and revive | PASS |
| **T10** | **Lives** | Life loss, respawn immunity, Game Over | Collide with chasing ghost until lives reach `0` | Player respawns at start with brief immunity; Game Over at `0` | PASS |
| **T11** | **Progression** | Multi-level carryover & timer expiry | Complete a level; also test letting timer reach `0` | Score and lives persist across levels; timer `0` triggers loss | PASS |
| **T12** | **Highscores** | Persistence across restarts | Clear `data/highscores.json`, finish game, enter name, quit, relaunch | Top-10 list persists on disk and displays in Main Menu | PASS |
| **T13** | **Highscores** | Name sanitization & Top-10 cap | Enter symbols/long names (`> 10` chars) and add 11+ scores | Invalid names default to `"Player"`; only Top 10 retained | PASS |
| **T14** | **UI Screens** | All menus, HUD, Pause, Win/Loss screens | Navigate Main Menu, Highscores, Instructions, Pause (`P`/`ESC`) | All required UI elements and controls work as specified | PASS |
| **T15** | **Cheat Mode** | Evaluation cheats (`Shift+C`) | Toggle `Shift+C`, then test `I`, `F`, `L`, `R`, `+`, `-`, `T`, `B`, `X` | Each cheat activates/deactivates accurately; `Shift+C` resets all | PASS |
| **T16** | **Code Quality** | Static analysis & style rules | Run `make lint` and `make lint-strict` | `flake8` and `mypy` pass with zero errors or warnings | PASS |
| **T17** | **Packaging** | Standalone build & Itch.io distribution | Run `make package`, extract ZIP, launch `./pacman config.json` | Packaged binary runs with sprites and matches Itch.io build | PASS |

---

## 2. QA Bug Log Summary

- **Bug #1 (Fixed):** `GAME_OVER` and `VICTORY` screens forced a full 3-second wait before transitioning to `NAME_ENTRY`. *Fix:* Enabled `ENTER` and `SPACE` keys to skip immediately to name entry.
- **Bug #2 (Fixed):** `Makefile` `lint` target initially checked only `src/`, omitting `pac-man.py`. *Fix:* Updated `lint` and `lint-strict` targets to run on `.` with `.flake8` excluding `.venv`, `build`, and `dist`.
- **Bug #3 (Fixed):** `Makefile` `package` target copied `config.json` without `README.md`. *Fix:* Updated `package` to copy both `config.json` and `README.md` into `dist/` prior to archiving.