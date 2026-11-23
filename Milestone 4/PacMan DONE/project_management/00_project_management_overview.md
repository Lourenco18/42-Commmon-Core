# Project Management — Pac-Man

This directory contains the project management artifacts produced by **dasantos** and **fjose-hi** to plan, structure, track, and validate the **Pac-Man** project for the 42 curriculum.

## Methodology Overview

We adopted an **iterative, milestone-driven Kanban workflow** organized across a 6-day development cycle:

1. **Upfront Decomposition & Architecture:** Separating pure-Python game logic from Pygame rendering and isolating the external `A-Maze-ing` dependency behind an adapter layer.
2. **Incremental Vertical Slices:** Delivering a playable core loop early, then layering ghost personalities, UI screens, persistent highscores, cheat mode, and standalone packaging.
3. **Continuous Quality Gates:** Enforcing `flake8`, `mypy`, PEP 257 docstrings, and zero-traceback error handling before merging any feature.

---

## Directory Contents

| Document | Purpose |
| :--- | :--- |
| [`01_timeline_and_progress.md`](01_timeline_and_progress.md) | Visual Gantt timeline, Kanban snapshot, and planned vs. actual progress comparison |
| [`02_architecture_and_choices.md`](02_architecture_and_choices.md) | System decomposition, layered and OOP architecture, ghost AI, and technical trade-offs |
| [`03_risk_analysis.md`](03_risk_analysis.md) | Risk register with likelihood, impact, preventive controls, and runtime mitigations |
| [`04_team_organization.md`](04_team_organization.md) | Task ownership between `dasantos` and `fjose-hi`, Git workflow, and blocking points resolved |
| [`05_acceptance_test_plan.md`](05_acceptance_test_plan.md) | End-to-end acceptance test matrix mapped to the evaluation scale and QA bug log |

---

## 1-Minute Defense Tour Guide

During peer evaluation, the team can walk through the documents in the following sequence:

1. **Planning & Execution (`01_timeline_and_progress.md`):** Show the 6-day Gantt schedule and how actual delivery tracked against planned milestones.
2. **Technical Design (`02_architecture_and_choices.md`):** Highlight the 4-layer separation (`Config`, `Domain`, `Presentation`, `Controller`), OOP inheritance (`Entity` and `Collectible`), and the `mazegenerator` adapter.
3. **Risk & Robustness (`03_risk_analysis.md`):** Explain how faulty configs, unreachable maze cells, central `"42"` wall blocks, and corrupt highscore files are mitigated without crashes.
4. **Collaboration & Challenges (`04_team_organization.md`):** Present the division of work between `dasantos` and `fjose-hi`, code review practices, and key bugs resolved.
5. **Verification (`05_acceptance_test_plan.md`):** Review the acceptance criteria covering CLI safety, gameplay mechanics, persistence, cheat mode, linting, and packaging.