@echo off
REM Music Player Build Script for Windows
REM This script provides easy access to common build configurations

setlocal enabledelayedexpansion

echo Music Player Build Script
echo =========================
echo.

REM Default values
set BUILD_TYPE=release
set CONFIG_FILE=build_config.yaml
set CLEAN_ONLY=0
SET PACKAGE=0

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :main
if /i "%~1"=="--dev" (
    set BUILD_TYPE=dev
    shift
    goto :parse_args
)
if /i "%~1"=="--debug" (
    set BUILD_TYPE=debug
    shift
    goto :parse_args
)
if /i "%~1"=="--clean" (
    set CLEAN_ONLY=1
    shift
    goto :parse_args
)
if /i "%~1"=="--package" (
    set PACKAGE=1
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    goto :show_help
)
shift
goto :parse_args

:main
REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Show current build type
echo Build Type: %BUILD_TYPE%
echo Config File: %CONFIG_FILE%
echo.

REM Build command
set CMD=python build.py --config %CONFIG_FILE%

REM Apply build type specific settings
if "%BUILD_TYPE%"=="dev" (
    set CMD=%CMD% --debug --console --no-upx
) else if "%BUILD_TYPE%"=="debug" (
    set CMD=%CMD% --debug --console
)

REM Add package flag if requested
if "%PACKAGE%"=="1" (
    set CMD=%CMD% --package
)

REM Handle clean only
if "%CLEAN_ONLY%"=="1" (
    echo Cleaning build artifacts...
    python build.py --clean-only
    goto :end
)

REM Execute build
echo Executing: %CMD%
echo.
%CMD%

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
) else (
    echo.
    echo Build completed successfully!

    REM Ask if user wants to open dist folder
    set /p OPEN_DIST=Open output directory? (Y/N):
    if /i "!OPEN_DIST!"=="Y" (
        explorer "dist"
    )
)

goto :end

:show_help
echo Usage: build.bat [OPTIONS]
echo.
echo Options:
echo   --dev       Build development version (debug, console, no UPX)
echo   --debug     Build debug version (debug, console)
echo   --clean     Clean build artifacts only
echo   --package   Create installer package after building
echo   --help      Show this help message
echo.
echo Examples:
echo   build.bat                 # Build release version
echo   build.bat --dev           # Build development version
echo   build.bat --clean         # Clean build artifacts
echo   build.bat --dev --package # Build dev version and create package

:end
pause