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

## Technical Architecture
- **Logic & UI:** `boggle_game.py` (Tkinter)
- **Data Layer:** `boggle_history.py` (SQLite)
- **Visualization:** `boggle_visualizer.py` (Matplotlib/Plotly)
- **Simulation/Analysis:** `boggle_stats.py` (Simulation for distribution fitting)
