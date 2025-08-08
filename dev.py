#!/usr/bin/env python3
"""
Development wrapper for Screen Translator v2.0
Cross-platform development commands
"""

import sys
import subprocess
from pathlib import Path

def run_dev_command():
    """Run development command"""
    if len(sys.argv) < 2:
        print("Usage: python3 dev.py <command> [args]")
        print("Commands: setup, test, lint, build, run")
        return False
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    workspace = Path(__file__).parent
    build_script = workspace / "build.py"
    
    # Map dev commands to build.py commands
    command_map = {
        'setup': ['install', '--dev'],
        'test': ['test'],
        'lint': ['lint'],
        'build': ['build'],
        'clean': ['clean'],
        'quality': ['lint', '--fix']
    }
    
    if command == 'run':
        # Run the main application
        main_script = workspace / "main.py"
        if main_script.exists():
            try:
                result = subprocess.run([sys.executable, str(main_script)] + args)
                return result.returncode == 0
            except Exception as e:
                print(f"Error running application: {e}")
                return False
        else:
            print("main.py not found")
            return False
    
    elif command in command_map:
        build_cmd = [sys.executable, str(build_script)] + command_map[command] + args
        try:
            result = subprocess.run(build_cmd)
            return result.returncode == 0
        except Exception as e:
            print(f"Error running build command: {e}")
            return False
    
    else:
        print(f"Unknown command: {command}")
        print("Available: setup, test, lint, build, run, clean, quality")
        return False

if __name__ == "__main__":
    success = run_dev_command()
    exit(0 if success else 1)
