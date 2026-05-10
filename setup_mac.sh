#!/bin/bash

# Boggle macOS Setup Script
# This script installs dependencies and prepares the environment.

echo "--- Boggle macOS Setup ---"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python 3 is not installed."
    echo "Please download and install it from: https://www.python.org/downloads/"
    exit 1
fi

# 2. Check for Tkinter (sometimes missing on macOS Python versions)
python3 -c "import tkinter" &> /dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Tkinter is missing."
    echo "If you installed Python via Homebrew, run: brew install python-tk"
    echo "If you used the official installer, it should be included."
fi

# 3. Create virtual environment
echo "Setting up virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip

# 4. Install requirements
echo "Installing dependencies..."
./venv/bin/pip install -r requirements.txt

# 5. Make launcher executable
chmod +x PlayBoggle.command

# 6. Make the Finder-friendly app wrapper executable
chmod +x PlayBoggle.app/Contents/MacOS/PlayBoggle

echo "--- Setup Complete ---"
echo "You can now start the game by double-clicking 'PlayBoggle.app'."
