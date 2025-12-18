#!/bin/bash
# Music Player Build Script for Linux/macOS
# Usage: ./build.sh [--dev|--release|--clean|--help]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    echo "Music Player Build Script"
    echo "========================"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --dev       Use development profile (debug, console, no UPX)"
    echo "  --release   Use release profile (default)"
    echo "  --debug     Enable debug mode"
    echo "  --console   Show console window"
    echo "  --clean     Clean build artifacts only"
    echo "  --dry-run   Generate spec file only"
    echo "  --help      Show this help"
    echo
    echo "Examples:"
    echo "  $0                  # Build release version"
    echo "  $0 --dev            # Build development version"
    echo "  $0 --clean          # Clean build artifacts"
}

# Default values
PROFILE="release"
EXTRA_ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            PROFILE="dev"
            shift
            ;;
        --release)
            PROFILE="release"
            shift
            ;;
        --debug)
            EXTRA_ARGS="$EXTRA_ARGS --debug"
            shift
            ;;
        --console)
            EXTRA_ARGS="$EXTRA_ARGS --console"
            shift
            ;;
        --clean)
            python3 build.py --clean || python build.py --clean
            exit 0
            ;;
        --dry-run)
            EXTRA_ARGS="$EXTRA_ARGS --dry-run"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Find Python
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    print_error "Python is not installed or not in PATH"
    exit 1
fi

# Get script directory and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

echo
echo "Music Player Build Script"
echo "========================"
echo
print_info "Profile: $PROFILE"
print_info "Python: $PYTHON"
print_info "Project: $PROJECT_ROOT"
echo

# Build command
CMD="$PYTHON build.py --profile $PROFILE$EXTRA_ARGS"

print_info "Executing: $CMD"
echo
$CMD

if [ $? -eq 0 ]; then
    echo
    print_info "Build completed!"
    
    # Open dist folder if possible
    if command -v xdg-open &> /dev/null || command -v open &> /dev/null; then
        read -p "Open output directory? [Y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v open &> /dev/null; then
                open "$PROJECT_ROOT/dist"
            else
                xdg-open "$PROJECT_ROOT/dist"
            fi
        fi
    fi
else
    echo
    print_error "Build failed!"
    exit 1
fi