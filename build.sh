#!/bin/bash
# Music Player Build Script for Linux/macOS
# This script provides easy access to common build configurations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BUILD_TYPE="release"
CONFIG_FILE="build_config.yaml"
CLEAN_ONLY=0
PACKAGE=0

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    echo "Music Player Build Script"
    echo "========================"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --dev       Build development version (debug, console, no UPX)"
    echo "  --debug     Build debug version (debug, console)"
    echo "  --clean     Clean build artifacts only"
    echo "  --package   Create installer package after building"
    echo "  --help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Build release version"
    echo "  $0 --dev              # Build development version"
    echo "  $0 --clean            # Clean build artifacts"
    echo "  $0 --dev --package    # Build dev version and create package"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            BUILD_TYPE="dev"
            shift
            ;;
        --debug)
            BUILD_TYPE="debug"
            shift
            ;;
        --clean)
            CLEAN_ONLY=1
            shift
            ;;
        --package)
            PACKAGE=1
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

# Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Show build information
echo "Music Player Build Script"
echo "========================"
echo
print_info "Build Type: $BUILD_TYPE"
print_info "Config File: $CONFIG_FILE"
print_info "Python Command: $PYTHON_CMD"
echo

# Build command
CMD="$PYTHON_CMD build.py --config $CONFIG_FILE"

# Apply build type specific settings
case $BUILD_TYPE in
    dev)
        CMD="$CMD --debug --console --no-upx"
        ;;
    debug)
        CMD="$CMD --debug --console"
        ;;
esac

# Add package flag if requested
if [ $PACKAGE -eq 1 ]; then
    CMD="$CMD --package"
fi

# Handle clean only
if [ $CLEAN_ONLY -eq 1 ]; then
    print_info "Cleaning build artifacts..."
    $PYTHON_CMD build.py --clean-only
    exit 0
fi

# Execute build
print_info "Executing: $CMD"
echo
$CMD

if [ $? -eq 0 ]; then
    echo
    print_info "Build completed successfully!"

    # Ask if user wants to open dist folder (only on macOS and Linux with GUI)
    if command -v xdg-open &> /dev/null || command -v open &> /dev/null; then
        read -p "Open output directory? (Y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v open &> /dev/null; then
                open dist
            elif command -v xdg-open &> /dev/null; then
                xdg-open dist
            fi
        fi
    fi
else
    echo
    print_error "Build failed!"
    exit 1
fi