#!/bin/bash
# Setup Python alias for virtual environment

# Function to find and use appropriate Python
setup_python_alias() {
    if [ -d "wenv" ] && [ -f "wenv/Scripts/python.exe" ]; then
        # Windows environment
        alias python='wenv/Scripts/python.exe'
        alias pip='wenv/Scripts/pip.exe'
        export PYTHON_ENV="wenv"
        echo "Using Windows environment (wenv)"
    elif [ -d "venv" ] && [ -f "venv/bin/python" ]; then
        # Linux/macOS environment
        alias python='venv/bin/python'
        alias pip='venv/bin/pip'
        export PYTHON_ENV="venv"
        echo "Using Linux environment (venv)"
    elif [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
        # Alternative venv naming
        alias python='.venv/bin/python'
        alias pip='.venv/bin/pip'
        export PYTHON_ENV=".venv"
        echo "Using .venv environment"
    else
        echo "No virtual environment found! Using system Python"
        alias python='python3'
        alias pip='pip3'
        export PYTHON_ENV="system"
    fi
}

# Run the setup
setup_python_alias

# Export the function so it can be used in subshells
export -f setup_python_alias

echo "Python aliases configured. Use 'python' command."