# Boggle Project - General Specifications

## Project Purpose
A Python-based Boggle game (Tkinter) designed to track and visualize player progress over time through rigorous statistical analysis of gameplay data.

## Core Gameplay Mechanics
- **Grid:** 4x4 grid of letters derived from a standard Boggle dice set.
- **Timer:** Default 180 seconds (3 minutes) per round.
- **Word Validation:** Words must be at least 3 letters long, exist in the official dictionary (`mots_boggle.txt`), and be findable on the grid via adjacent cells (horizontal, vertical, or diagonal).
- **Scoring:** Standard Boggle scoring (3-4 letters: 1pt, 5L: 2pts, 6L: 3pts, 7L: 5pts, 8L+: 11pts).

## Progress Tracking & Metrics
The system analyzes performance relative to the "Grid Potential" (all possible words in a specific layout).
- **Grid Richness (Bins):**
    - **Aride (Poor):** Max score < 50
    - **Fertile (Average):** 50 <= Max score < 150
    - **Luxuriante (Rich):** Max score >= 150
- **Primary Ratios:**
    - **Score Ratio:** Percentage of total available points achieved.
    - **Words Ratio:** Percentage of total available words found.
- **Top-Tier Catch Rate:** Focuses on the longest words possible in a grid (Range: [Max_Length - 2, Max_Length]).
- **Effective Playing Time:** Precise tracking of seconds played, excluding pauses. Only full 3-minute games are included in primary progress charts.

## Pause & Integrity Features
- **Anti-Cheat Pause:** Spacebar or losing window focus hides the board and stops the timer.
- **Unfinished Games:** Games interrupted by closing or resetting are saved as "unfinished" to preserve raw data for time-based ratio analysis.
- **Database:** SQLite (`boggle_stats.db`) stores every game session. Integrity is critical.
- **Update Checker:** On startup, the app checks the GitHub repository for a newer revision on the `master` branch. To optimize performance, this check occurs **once every 24 hours**. If an update is found, it prompts the user to perform a `git pull` and auto-restart.
- **Gist-Sync (Cloud Persistence):** The app implements a "dual-layer" storage architecture:
    - **Local SQLite:** Serves as a high-speed cache for instant UI response and offline play.
    - **GitHub Gist:** Acts as the single source of truth (master archive).
    - **Mechanism:** On startup, the app pulls missing games from a Secret Gist (identified by unique GUIDs). At the end of every game, it pushes the updated history back to the cloud. This allows seamless sequential play across multiple machines.
- **Startup Flags:**
    - `--debug`: Redirects data to `boggle_stats_debug.db` and enables verbose logging.
    - `--force-update`: Bypasses the 24-hour limit to force an immediate update check.

## Technical Architecture
- **Logic & UI:** `boggle_game.py` (Tkinter)
- **Data Layer:** `boggle_history.py` (SQLite)
- **Visualization:** `boggle_visualizer.py` (Matplotlib/Plotly)
- **Simulation/Analysis:** `boggle_stats.py` (Simulation for distribution fitting)
