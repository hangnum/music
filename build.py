#!/usr/bin/env python3
"""
Music Player Build Script
Creates executable packages using PyInstaller for different platforms.
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path


class MusicPlayerBuilder:
    """Builder class for creating Music Player executables."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / "src"
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.icon_path = self.project_root / "assets" / "icon.ico"
        self.platform = platform.system().lower()

    def check_dependencies(self):
        """Check if required dependencies are installed."""
        print("Checking dependencies...")

        # Check Python version
        if sys.version_info < (3, 8):
            print("Error: Python 3.8 or higher is required")
            return False

        # Check PyInstaller
        try:
            import PyInstaller
            print(f"PyInstaller found: {PyInstaller.__version__}")
        except ImportError:
            print("Installing PyInstaller...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                         check=True)

        return True

    def create_app_icon(self):
        """Create application icon if it doesn't exist."""
        if not self.icon_path.exists():
            print(f"Creating placeholder icon at {self.icon_path}")
            self.icon_path.parent.mkdir(exist_ok=True)

            # Create a simple placeholder icon using PIL
            try:
                from PIL import Image, ImageDraw
                img_size = 256
                img = Image.new('RGBA', (img_size, img_size), (30, 30, 30, 255))
                draw = ImageDraw.Draw(img)

                # Draw a music note symbol
                draw.ellipse([50, 150, 100, 200], fill='white')
                draw.ellipse([150, 150, 200, 200], fill='white')
                draw.rectangle([90, 50, 110, 150], fill='white')
                draw.polygon([(110, 50), (180, 80), (180, 100), (110, 70)],
                           fill='white')

                img.save(self.icon_path, 'ICO', sizes=[(16, 16), (32, 32), (48, 48),
                                                     (64, 64), (128, 128), (256, 256)])
            except ImportError:
                print("Warning: PIL not installed, skipping icon creation")

    def create_spec_file(self):
        """Create PyInstaller spec file with custom configurations."""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Project configuration
project_root = Path(SPECPATH)
src_dir = project_root / "src"

# Analysis of the main script
a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        # Include configuration files
        (str(src_dir / "config" / "default_config.yaml"), "config"),
        # Include UI resources if they exist
        (str(src_dir / "ui" / "styles"), "ui/styles"),
    ],
    hiddenimports=[
        # Pygame hidden imports
        "pygame.sdl2_video",
        "pygame.mixer_music",
        "pygame.mixer",
        # PyQt6 hidden imports
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        # Audio formats
        "mutagen.mp3",
        "mutagen.flac",
        "mutagen.wavpack",
        "mutagen.oggvorbis",
        "mutagen.mp4",
        "mutagen.m4a",
        "mutagen.wma",
        "mutagen.apev2",
        # LLM queue dependencies
        "requests",
        "openai",
        "anthropic",
        # YAML
        "yaml",
        "yaml.scanner",
        "yaml.parser",
        "yaml.serializer",
        "yaml.resolver",
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "tkinter",
        "unittest",
        "test",
        "tests",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MusicPlayer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="{self.icon_path if self.icon_path.exists() else ''}",
    version="version_info.txt" if Path("version_info.txt").exists() else None,
)
'''

        spec_file = self.project_root / "MusicPlayer.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        return spec_file

    def create_version_info(self):
        """Create version info file for Windows executable."""
        if self.platform == "windows":
            version_info = '''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'080404B0',
          [StringStruct(u'CompanyName', u'Music Player'),
            StringStruct(u'FileDescription', u'Python Music Player'),
            StringStruct(u'FileVersion', u'1.0.0.0'),
            StringStruct(u'InternalName', u'musicplayer'),
            StringStruct(u'LegalCopyright', u'Copyright (C) 2024'),
            StringStruct(u'OriginalFilename', u'MusicPlayer.exe'),
            StringStruct(u'ProductName', u'Music Player'),
            StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)'''

            with open(self.project_root / "version_info.txt", 'w', encoding='utf-8') as f:
                f.write(version_info)

    def build_executable(self, single_file=True):
        """Build the executable using PyInstaller."""
        print(f"Building executable for {self.platform}...")

        # Clean previous builds
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)

        # Create spec file
        spec_file = self.create_spec_file()

        # Build command
        cmd = [
            "pyinstaller",
            "--clean",
            "--noconfirm",
        ]

        if single_file:
            cmd.append("--onefile")

        cmd.append(str(spec_file))

        # Run PyInstaller
        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        # Show results
        if self.dist_dir.exists():
            print(f"\nBuild successful! Executable created in: {self.dist_dir}")
            for file in self.dist_dir.rglob("*"):
                if file.is_file():
                    size_mb = file.stat().st_size / 1024 / 1024
                    print(f"  - {file.name} ({size_mb:.1f} MB)")

    def create_installer(self):
        """Create installer for the platform (optional)."""
        if self.platform == "windows":
            self.create_windows_installer()
        elif self.platform == "darwin":
            self.create_macos_bundle()
        else:
            self.create_linux_package()

    def create_windows_installer(self):
        """Create Windows installer using NSIS or Inno Setup."""
        print("\nCreating Windows installer...")

        # Create NSIS script
        nsis_script = f'''
!define APP_NAME "Music Player"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Music Player Team"
!define APP_URL "https://github.com/yourusername/music-player"
!define APP_EXECUTABLE "MusicPlayer.exe"

Name "${{APP_NAME}}"
OutFile "MusicPlayer-Setup-${{APP_VERSION}}.exe"
InstallDir "$PROGRAMFILES64\\${{APP_NAME}}"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "{self.dist_dir}\\*"

    CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
    CreateShortCut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXECUTABLE}}"
    CreateShortCut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXECUTABLE}}"

    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayName" "${{APP_NAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\\uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\*.*"
    RMDir "$SMPROGRAMS\\${{APP_NAME}}"
    Delete "$DESKTOP\\${{APP_NAME}}.lnk"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"
SectionEnd
'''

        with open(self.project_root / "installer.nsi", 'w', encoding='utf-8') as f:
            f.write(nsis_script)

        print("NSIS script created: installer.nsi")
        print("To create installer, run NSIS compiler with this script")

    def create_macos_bundle(self):
        """Create macOS app bundle."""
        print("\nCreating macOS app bundle...")
        # Implementation for macOS
        pass

    def create_linux_package(self):
        """Create Linux package (AppImage or deb)."""
        print("\nCreating Linux package...")
        # Implementation for Linux
        pass

    def run(self):
        """Run the complete build process."""
        print("Music Player Build Script")
        print("=" * 50)

        # Check dependencies
        if not self.check_dependencies():
            sys.exit(1)

        # Create icon
        self.create_app_icon()

        # Create version info for Windows
        if self.platform == "windows":
            self.create_version_info()

        # Build executable
        self.build_executable(single_file=True)

        # Optionally create installer
        create_installer = input("\nCreate installer package? (y/n): ").lower()
        if create_installer == 'y':
            self.create_installer()

        print("\nBuild process completed!")


if __name__ == "__main__":
    builder = MusicPlayerBuilder()
    builder.run()