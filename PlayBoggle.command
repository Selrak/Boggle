#!/bin/bash

# Move to the script directory
cd "$(dirname "$0")"

echo "Checking Boggle installation..."

# 1. Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python 3 is not installed."
    echo "Please install it from https://www.python.org/downloads/"
    read -p "Press enter to exit..."
    exit
fi

# 2. Setup Virtual Environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# 3. Launch the game
echo "Launching Boggle..."
./venv/bin/python3 boggle_game.py "$@"
