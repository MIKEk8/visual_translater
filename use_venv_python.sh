#!/bin/bash
# Simple script to use Python from virtual environment

if [ -f "wenv/Scripts/python.exe" ]; then
    wenv/Scripts/python.exe "$@"
elif [ -f "venv/bin/python" ]; then
    venv/bin/python "$@"
elif [ -f ".venv/bin/python" ]; then
    .venv/bin/python "$@"
else
    python3 "$@"
fi