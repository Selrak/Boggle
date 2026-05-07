# Agent Instructions - Boggle Project

## Critical Directives
1.  **READ FIRST:** Always read and follow the instructions in `General_specification.md`.
2.  **DOCUMENTATION:** Whenever making a general change (new feature, metric change, architecture shift), you **MUST** update `General_specification.md` to reflect the change in high-level terms (purpose and logic) without necessarily detailing implementation specifics.
3.  **DATABASE INTEGRITY (CRITICAL):** The file `boggle_stats.db` contains the user's entire gameplay history. **NEVER** delete, reset, or modify this file unless explicitly instructed by the user. If you are writing tests, use a temporary in-memory database or a separate `.db` file.
4.  **DEBUG MODE:** Whenever running the game for testing or development purposes from an agent environment, **ALWAYS** use the `--debug` flag (e.g., `python boggle_game.py --debug`). This redirects all gameplay data to `boggle_stats_debug.db` to keep the production history clean and enables verbose console logging.

## Core Mandates
- **Accuracy of Metrics:** Any changes to the game logic must ensure that the "Max Possible Score" and "Total Words" remain accurate, as these are the baseline for all progress tracking.
- **Visualization Performance:** The end-of-game stats window must load in under 1 second. Avoid adding heavy dependencies or complex queries that block the main UI thread.

## Development Guidelines
- **Testing:** Use `test_boggle.py` for logic verification. It uses a fixed grid to ensure deterministic results (Expected Score: 112).
- **Styling:** Maintain the "White/Minimalist" aesthetic. Use `draw_rounded_rect` for custom canvas elements.
- **Git Hooks:** Avoid re-introducing the tracker ID hook or any interactive hooks that might break automated environments.
