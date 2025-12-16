#!/bin/bash
# Music Player Build Script for macOS and Linux
# This script builds the music player into an executable

set -e  # Exit on any error

echo "===================================="
echo "Music Player Build Script (Unix)"
echo "===================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please install Python 3 from https://python.org or using Homebrew: brew install python"
    else
        echo "Please install Python 3 using your package manager:"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  Fedora: sudo dnf install python3 python3-pip"
        echo "  Arch: sudo pacman -S python python-pip"
    fi
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi
print_info "Using Python $PYTHON_VERSION"

# Check if we're in the correct directory
if [ ! -f "src/main.py" ]; then
    print_error "src/main.py not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install requirements
print_info "Installing dependencies..."
pip install -r requirements.txt

# Install PyInstaller
print_info "Installing PyInstaller..."
pip install pyinstaller

# Install Pillow for icon creation
pip install Pillow

# Create assets directory if it doesn't exist
mkdir -p assets

# Platform-specific setup
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS specific settings
    export PYTHONOPTIMIZE=1
    print_info "Detected macOS"

    # Check if Xcode command line tools are installed
    if ! xcode-select -p &> /dev/null; then
        print_error "Xcode Command Line Tools are not installed"
        echo "Run: xcode-select --install"
        exit 1
    fi
else
    # Linux specific settings
    print_info "Detected Linux"

    # Check for necessary system packages
    if ! dpkg -l | grep -q libsdl2-2.0-0 2>/dev/null && ! rpm -qa | grep -q SDL2 2>/dev/null; then
        print_info "SDL2 not found. Installing may be required for pygame:"
        echo "  Ubuntu/Debian: sudo apt install libsdl2-2.0-0"
        echo "  Fedora: sudo dnf install SDL2"
        echo "  Arch: sudo pacman -S sdl2"
    fi
fi

# Run the build script
print_info "Running build script..."
python build.py

# Check if build was successful
EXECUTABLE_NAME="MusicPlayer"
if [[ "$OSTYPE" == "darwin"* ]]; then
    EXECUTABLE_PATH="dist/$EXECUTABLE_NAME"
else
    EXECUTABLE_PATH="dist/$EXECUTABLE_NAME"
fi

if [ -f "$EXECUTABLE_PATH" ]; then
    print_success "Build completed successfully!"
    echo "Executable location: $EXECUTABLE_PATH"

    # Show file size
    if command -v du &> /dev/null; then
        FILE_SIZE=$(du -h "$EXECUTABLE_PATH" | cut -f1)
        echo "File size: $FILE_SIZE"
    fi

    echo
    # Ask if user wants to run the application
    read -p "Do you want to run the application now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Launching application..."
        "$EXECUTABLE_PATH"
    fi
else
    print_error "Build failed!"
    echo "Check the error messages above for details"
    exit 1
fi

print_success "Script completed!"