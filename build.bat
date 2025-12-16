@echo off
REM Music Player Build Script for Windows
REM This script builds the music player into a Windows executable

echo ====================================
echo Music Player Build Script (Windows)
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the correct directory
if not exist "src\main.py" (
    echo [ERROR] src\main.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo [INFO] Installing dependencies...
pip install -r requirements.txt

REM Install PyInstaller
echo [INFO] Installing PyInstaller...
pip install pyinstaller

REM Install Pillow for icon creation
pip install Pillow

REM Create assets directory if it doesn't exist
if not exist "assets" mkdir assets

REM Run the build script
echo [INFO] Running build script...
python build.py

REM Check if build was successful
if exist "dist\MusicPlayer.exe" (
    echo.
    echo [SUCCESS] Build completed successfully!
    echo Executable location: dist\MusicPlayer.exe

    REM Show file size
    for %%I in (dist\MusicPlayer.exe) do echo File size: %%~zI bytes

    echo.
    echo Press any key to run the application...
    pause >nul
    dist\MusicPlayer.exe
) else (
    echo.
    echo [ERROR] Build failed!
    echo Check the error messages above for details
)

pause