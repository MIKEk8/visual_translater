#!/bin/bash
# Aliases for Python virtual environment

# Check which virtual environment exists and set appropriate aliases
if [ -d "wenv" ]; then
    # Windows environment
    alias python='wenv/Scripts/python.exe'
    alias pip='wenv/Scripts/pip.exe'
    alias pytest='wenv/Scripts/pytest.exe'
    echo "🪟 Using Windows environment (wenv)"
elif [ -d "venv" ]; then
    # Linux/macOS environment
    alias python='venv/bin/python'
    alias pip='venv/bin/pip'
    alias pytest='venv/bin/pytest'
    echo "🐧 Using Linux environment (venv)"
elif [ -d ".venv" ]; then
    # Alternative venv naming
    alias python='.venv/bin/python'
    alias pip='.venv/bin/pip'
    alias pytest='.venv/bin/pytest'
    echo "📦 Using .venv environment"
else
    echo "⚠️  No virtual environment found! Using system Python"
    alias python='python3'
    alias pip='pip3'
fi

# Additional helpful aliases
alias venv-activate='source venv/bin/activate 2>/dev/null || source wenv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null'
alias venv-python='python'
alias venv-pip='pip'

# Project-specific aliases
alias build='python build.py'
alias test='python -m pytest'
alias lint='python -m flake8'
alias format='python -m black .'

echo "✅ Python aliases loaded"