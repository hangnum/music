@echo off
REM Music Player Build Script for Windows
REM Usage: build.bat [--dev|--release|--clean|--help]

setlocal enabledelayedexpansion

echo.
echo Music Player Build Script
echo =========================
echo.

REM Default values
set PROFILE=release
set EXTRA_ARGS=

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :main
if /i "%~1"=="--dev" (
    set PROFILE=dev
    shift
    goto :parse_args
)
if /i "%~1"=="--release" (
    set PROFILE=release
    shift
    goto :parse_args
)
if /i "%~1"=="--debug" (
    set EXTRA_ARGS=%EXTRA_ARGS% --debug
    shift
    goto :parse_args
)
if /i "%~1"=="--console" (
    set EXTRA_ARGS=%EXTRA_ARGS% --console
    shift
    goto :parse_args
)
if /i "%~1"=="--clean" (
    python build.py --clean
    goto :end
)
if /i "%~1"=="--dry-run" (
    set EXTRA_ARGS=%EXTRA_ARGS% --dry-run
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    goto :show_help
)
shift
goto :parse_args

:main
REM Get script directory
set SCRIPT_DIR=%~dp0

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Build command (run from script directory)
pushd "%SCRIPT_DIR%"
set CMD=python build.py --profile %PROFILE%%EXTRA_ARGS%

REM Execute build
echo Executing: %CMD%
echo.
%CMD%

if errorlevel 1 (
    popd
    echo.
    echo Build failed!
    pause
    exit /b 1
) else (
    popd
    echo.
    echo Build completed!
    set /p OPEN_DIST=Open output directory? [Y/N]: 
    if /i "!OPEN_DIST!"=="Y" explorer "%SCRIPT_DIR%..\dist"
)
goto :end

:show_help
echo Usage: build.bat [OPTIONS]
echo.
echo Options:
echo   --dev       Use development profile (debug, console, no UPX)
echo   --release   Use release profile (default)
echo   --debug     Enable debug mode
echo   --console   Show console window
echo   --clean     Clean build artifacts only
echo   --dry-run   Generate spec file only
echo   --help      Show this help
echo.
echo Examples:
echo   build.bat              # Build release version
echo   build.bat --dev        # Build development version
echo   build.bat --clean      # Clean build artifacts

:end
pause