# Project Backlog

## Open Tasks
*(Waiting for PM/human to add upcoming bugs)*

## Completed Tasks
- **TASK-004 (Bug 4):** Tick Collision - Added a `_is_ticking` guard to the scheduled jobs in `main.py` to prevent overlapping ticks.
- **TASK-002 (Bug 2):** Session Setup Count - Fixed bug where `setup_count` was always 0 in the session-end alert by extracting it directly from the ModeController pipelines.
- **TASK-001 (Bug 1):** CLI Parsing (broken `--15` style args) - Fixed and replaced with proper `argparse` arguments (`--id` and `--mode`).
