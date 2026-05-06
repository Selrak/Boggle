# Boggle Progress Tracker - Agent Instructions

## Project Overview
This project is a fully functional Boggle game implementation in Python (Tkinter). Its primary goal is to provide a smooth gameplay experience while rigorously tracking player progress over time through statistical analysis and visualization.

## Core Mandates for Agents
1.  **DATABASE INTEGRITY (CRITICAL):** The file `boggle_stats.db` contains the user's entire gameplay history. **NEVER** delete, reset, or modify this file unless explicitly instructed by the user. If you are writing tests, use a temporary in-memory database or a separate `.db` file.
2.  **Accuracy of Metrics:** Any changes to the game logic must ensure that the "Max Possible Score" and "Total Words" remain accurate, as these are the baseline for all progress tracking.
3.  **Visualization Performance:** The end-of-game stats window must load in under 1 second. Avoid adding heavy dependencies or complex queries that block the main UI thread.

## System Architecture
- `boggle_game.py`: The main entry point. Handles the UI, timer, word validation (DFS), and game loop.
- `boggle_history.py`: Data Access Layer. Manages SQLite operations, rankings, and data persistence.
- `boggle_visualizer.py`: Visualization Layer. Uses Matplotlib for embedded Tkinter graphs and Plotly for interactive 3D browser-based charts.
- `mots_boggle.txt`: The dictionary used for word validation.

## Key Metrics Tracked
- **Score Ratio:** Percentage of the total possible score achieved.
- **Words Ratio:** Percentage of the total possible words found.
- **Top-Tier Catch Rate:** Percentage of words found within the [MaxLength-2, MaxLength] range for a given grid.
- **Grid Richness:** Grids are binned into 'Poor', 'Average', and 'Rich' based on their maximum potential to allow for differentiated progress analysis.

## Development Guidelines
- **Testing:** Use `test_boggle.py` for logic verification. It uses a fixed grid to ensure deterministic results (Expected Score: 112).
- **Styling:** Maintain the "White/Minimalist" aesthetic. Use `draw_rounded_rect` for custom canvas elements.
- **Git Hooks:** Avoid re-introducing the tracker ID hook or any interactive hooks that might break automated environments.
