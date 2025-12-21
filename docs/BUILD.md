# Building Executable Files

This document describes how to package the music player project into an executable file. The project uses PyInstaller for packaging and provides automated scripts to simplify the build process.

## Quick Start

All build scripts are now located in the `scripts/` directory.

### Windows

```batch
# Execute from the project root directory
.\scripts\build.bat
```

### macOS 和 Linux

```bash
# Give the script execution permissions (only needs to be done once)
chmod +x scripts/build.sh

# Run the build script
./scripts/build.sh
```

## Build Options

The build system supports multiple modes, which can be configured via command-line arguments or by modifying `scripts/build_config.yaml`.

### Common Commands

| Platform | Command | Description |
|------|------|------|
| Windows | `.\scripts\build.bat` | Build release version (single file) |
| Windows | `.\scripts\build.bat --dev` | Build development version (with console, fast startup) |
| Linux/macOS | `./scripts/build.sh` | Build release version |
| Linux/macOS | `./scripts/build.sh --dev` | Build development version |

### Build Mode Descriptions

- **Release Mode**:
  - Generates a single executable file.
  - Enables UPX compression.
  - Hides the console window.
- **Dev Mode (Dev)**:
  - Generates a directory containing all dependencies.
  - Disables compression to speed up the build.
  - Shows the console window for debugging convenience.

## Detailed Configuration

All build behavior is controlled by `scripts/build_config.yaml`. You can modify the following as needed:

- **App Information**: Name, version, description.
- **Icons**: Icon files located in the `assets/` directory.
- **Data Files**: Resources that need to be packaged into the program (e.g., QSS styles, icons).
- **Hidden Imports**: Modules that PyInstaller cannot automatically detect.

## Troubleshooting

1. **ModuleNotFoundError**: Check if `hidden_imports` in `build_config.yaml` includes the reporting module.
2. **Permission Error**: Ensure `chmod +x scripts/build.sh` has been executed on macOS/Linux.
3. **Build Failed**: Run with `--dev` mode to see detailed error logs in the console.

For more information, please refer to the PyInstaller [official documentation](https://pyinstaller.readthedocs.io/).
