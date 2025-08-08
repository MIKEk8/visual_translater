#!/bin/bash
# Screen Translator v2.0 - Development Helper (Unix/Linux/macOS)
# Wrapper for build.py with common commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    echo "============================================="
    echo "  Screen Translator v2.0 - Development Helper (Linux/macOS)"
    echo "============================================="
    echo ""
    echo -e "${BLUE}🐧 Platform: Linux/macOS - используется venv (Virtual Environment)${NC}"
    echo ""
    
    # Check venv status
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo -e "${GREEN}🐍 Virtual Environment (venv): ACTIVE${NC}"
        echo "    Location: $VIRTUAL_ENV"
        echo "    Commands will automatically use --venv flag"
    elif [[ -f "venv/bin/python" ]]; then
        echo -e "${GREEN}🐍 Virtual Environment (venv): AVAILABLE (using automatically)${NC}"
        echo "    Location: venv/"
        echo "    Commands will automatically use --venv flag"
    elif [[ -f ".venv/bin/python" ]]; then
        echo -e "${YELLOW}🐍 Virtual Environment (.venv): AVAILABLE (legacy - using automatically)${NC}"
        echo "    Location: .venv/"
        echo "    Commands will automatically use --venv flag"
    else
        echo -e "${RED}❌ Virtual Environment (venv): NOT FOUND${NC}"
        echo "    Run './dev.sh setup' to create venv and configure everything"
    fi
    echo ""
    
    echo "Common Commands (автоматически используют venv):"
    echo "  ./dev.sh setup                 - Setup venv development environment"
    echo "  ./dev.sh test                  - Run all tests in venv"
    echo "  ./dev.sh test unit             - Run unit tests in venv"
    echo "  ./dev.sh test integration      - Run integration tests in venv"
    echo "  ./dev.sh test coverage         - Run tests with coverage in venv"
    echo "  ./dev.sh lint                  - Check code quality in venv"
    echo "  ./dev.sh lint fix              - Fix code quality issues in venv"
    echo "  ./dev.sh build                 - Build release executable in venv"
    echo "  ./dev.sh build debug           - Build debug executable in venv"
    echo "  ./dev.sh run                   - Start application in venv"
    echo "  ./dev.sh run debug             - Start with debug logging in venv"
    echo "  ./dev.sh run test              - Run system tests in venv"
    echo ""
    echo "Full build.py options:"
    echo "  ./dev.sh clean                 - Clean build artifacts"
    echo "  ./dev.sh security              - Run security scans"
    echo "  ./dev.sh ci                    - Run full CI pipeline"
    echo ""
    echo "Advanced usage:"
    echo "  python build.py --help         - Show all options"
    echo ""
}

# Check if Python is available and detect venv
check_python() {
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        echo -e "${RED}❌ Python not found! Please install Python 3.8+${NC}"
        echo "Install instructions:"
        echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
        echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
        echo "  macOS:         brew install python3"
        exit 1
    fi
    
    # Prefer python3 over python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi
    
    # Check for virtual environment (prioritize venv over .venv)
    VENV_FLAG=""
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo -e "${GREEN}🐍 Virtual environment detected: $VIRTUAL_ENV${NC}"
        VENV_FLAG="--venv"
    elif [[ -f "venv/bin/python" ]]; then
        echo -e "${GREEN}🐍 Virtual environment (venv) available - using automatically${NC}"
        VENV_FLAG="--venv"
        PYTHON_CMD="venv/bin/python"
    elif [[ -f ".venv/bin/python" ]]; then
        echo -e "${YELLOW}🐍 Virtual environment (.venv) available - using automatically (legacy)${NC}"
        VENV_FLAG="--venv"
        PYTHON_CMD=".venv/bin/python"
    fi
}

# Main script
main() {
    if [[ $# -eq 0 ]] || [[ "$1" == "help" ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
        show_help
        exit 0
    fi
    
    check_python
    
    case "$1" in
        "setup")
            echo -e "${BLUE}🚀 Setting up venv development environment for Linux/macOS...${NC}"
            echo ""
            
            # Always create venv if it doesn't exist
            if [[ ! -f "venv/bin/python" ]]; then
                echo -e "${BLUE}📦 Creating virtual environment (venv)...${NC}"
                $PYTHON_CMD build.py venv-create
                if [[ $? -ne 0 ]]; then
                    echo -e "${RED}❌ Error creating virtual environment!${NC}"
                    exit 1
                fi
            else
                echo -e "${GREEN}✅ Virtual environment already exists${NC}"
            fi
            
            echo ""
            echo -e "${BLUE}📚 Installing development and build dependencies...${NC}"
            venv/bin/python build.py venv-install --dev --build
            if [[ $? -ne 0 ]]; then
                echo -e "${RED}❌ Error installing dependencies!${NC}"
                exit 1
            fi
            
            echo ""
            echo -e "${GREEN}============================================${NC}"
            echo -e "${GREEN}✅ venv environment configured successfully!${NC}"
            echo -e "${GREEN}============================================${NC}"
            echo ""
            echo "Available commands:"
            echo "  ./dev.sh test          - Run tests in venv"
            echo "  ./dev.sh build         - Build application in venv"
            echo "  ./dev.sh run           - Run from source in venv"
            echo "  ./dev.sh lint          - Check code quality in venv"
            ;;
        "test")
            case "$2" in
                "unit")
                    $PYTHON_CMD build.py test --type unit $VENV_FLAG "${@:3}"
                    ;;
                "integration")
                    $PYTHON_CMD build.py test --type integration $VENV_FLAG "${@:3}"
                    ;;
                "coverage")
                    $PYTHON_CMD build.py test --coverage $VENV_FLAG "${@:3}"
                    ;;
                *)
                    $PYTHON_CMD build.py test $VENV_FLAG "${@:2}"
                    ;;
            esac
            ;;
        "lint")
            if [[ "$2" == "fix" ]]; then
                $PYTHON_CMD build.py lint --fix $VENV_FLAG
            else
                $PYTHON_CMD build.py lint $VENV_FLAG "${@:2}"
            fi
            ;;
        "build")
            if [[ "$2" == "debug" ]]; then
                $PYTHON_CMD build.py build --mode debug $VENV_FLAG
            else
                $PYTHON_CMD build.py build $VENV_FLAG "${@:2}"
            fi
            ;;
        "run")
            echo -e "${BLUE}🚀 Starting Screen Translator...${NC}"
            case "$2" in
                "debug")
                    $PYTHON_CMD main.py --debug
                    ;;
                "test")
                    $PYTHON_CMD main.py --test
                    ;;
                *)
                    $PYTHON_CMD main.py "${@:2}"
                    ;;
            esac
            ;;
        *)
            # Pass through to build.py for other commands
            if [[ -n "$VENV_FLAG" ]]; then
                $PYTHON_CMD build.py "$1" $VENV_FLAG "${@:2}"
            else
                $PYTHON_CMD build.py "$@"
            fi
            ;;
    esac
}

main "$@"