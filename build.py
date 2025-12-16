#!/usr/bin/env python3
"""
Music Player Build Script v2.0
A modern, configurable build system for creating cross-platform executables.
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

try:
    import yaml
except ImportError:
    print("Installing PyYAML...")
    subprocess.run([sys.executable, "-m", "pip", "install", "PyYAML"], check=True)
    import yaml

try:
    import PyInstaller
except ImportError:
    print("Installing PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    import PyInstaller


@dataclass
class BuildConfig:
    """Build configuration data class."""
    app_name: str = "MusicPlayer"
    app_version: str = "1.0.0"
    app_description: str = "Python Music Player with PyQt6"
    app_copyright: str = "Copyright (C) 2024 Music Player Team"
    app_author: str = "Music Player Team"
    app_url: str = "https://github.com/yourusername/music-player"

    # Build settings
    single_file: bool = True
    console: bool = False
    upx_compression: bool = True
    debug: bool = False
    strip: bool = True
    clean_build: bool = True

    # Paths
    src_dir: str = "src"
    main_script: str = "main.py"
    dist_dir: str = "dist"
    build_dir: str = "build"

    # Data files
    data_files: List[Dict[str, str]] = field(default_factory=list)

    # Imports
    hidden_imports: List[str] = field(default_factory=list)
    excludes: List[str] = field(default_factory=list)

    # Platform-specific settings
    platforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # UPX settings
    upx_exclude: List[str] = field(default_factory=list)

    # Splash screen
    splash_enabled: bool = False
    splash_image: Optional[str] = None
    splash_duration: int = 3000


class BuildLogger:
    """Centralized logging for build process."""

    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("MusicPlayerBuild")
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(file_handler)

    def info(self, message: str):
        self.logger.info(message)

    def success(self, message: str):
        self.logger.info(f"✓ {message}")

    def warning(self, message: str):
        self.logger.warning(f"⚠ {message}")

    def error(self, message: str):
        self.logger.error(f"✗ {message}")


class DependencyManager:
    """Manages build dependencies."""

    def __init__(self, logger: BuildLogger):
        self.logger = logger

    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        if sys.version_info < (3, 8):
            self.logger.error(f"Python 3.8+ required, found {sys.version}")
            return False
        self.logger.success(f"Python {sys.version.split()[0]}")
        return True

    def install_package(self, package: str) -> bool:
        """Install a package using pip."""
        self.logger.info(f"Installing {package}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True
            )
            self.logger.success(f"Installed {package}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package}: {e}")
            return False

    def check_dependencies(self, packages: List[str]) -> bool:
        """Check and install required packages."""
        all_ok = True
        for package in packages:
            try:
                __import__(package.lower().replace('-', '_'))
                self.logger.success(f"{package} is installed")
            except ImportError:
                self.logger.warning(f"{package} not found")
                all_ok &= self.install_package(package)
        return all_ok


class AssetManager:
    """Manages build assets like icons and resources."""

    def __init__(self, config: BuildConfig, logger: BuildLogger):
        self.config = config
        self.logger = logger
        self.project_root = Path.cwd()
        self.assets_dir = self.project_root / "assets"

    def create_icons(self):
        """Create application icons if they don't exist."""
        icons_needed = {
            "windows": "icon.ico",
            "darwin": "icon.icns",
            "linux": "icon.png"
        }

        for platform, icon_name in icons_needed.items():
            icon_path = self.assets_dir / icon_name
            if not icon_path.exists():
                self.logger.warning(f"{platform} icon missing: {icon_path}")
                if self._create_placeholder_icon(icon_path, platform):
                    self.logger.success(f"Created {platform} placeholder icon")

    def _create_placeholder_icon(self, icon_path: Path, platform: str) -> bool:
        """Create a placeholder icon."""
        try:
            from PIL import Image, ImageDraw

            # Ensure assets directory exists
            self.assets_dir.mkdir(exist_ok=True)

            # Create image
            size = 256 if platform == "linux" else 512
            img = Image.new('RGBA', (size, size), (30, 30, 30, 255))
            draw = ImageDraw.Draw(img)

            # Draw music note
            note_color = (66, 133, 244, 255)  # Blue
            margin = size // 8

            # Note stems
            stem_width = size // 20
            stem_height = size // 2
            draw.rectangle(
                [(size * 3 // 8, size // 4),
                 (size * 3 // 8 + stem_width, size * 3 // 4)],
                fill=note_color
            )
            draw.rectangle(
                [(size * 5 // 8, size // 6),
                 (size * 5 // 8 + stem_width, size * 5 // 8)],
                fill=note_color
            )

            # Note heads
            head_size = size // 6
            draw.ellipse(
                [(size * 3 // 8 - head_size, size * 3 // 4 - head_size // 2),
                 (size * 3 // 8 + stem_width + head_size, size * 3 // 4 + head_size // 2)],
                fill=note_color
            )
            draw.ellipse(
                [(size * 5 // 8 - head_size, size * 5 // 8 - head_size // 2),
                 (size * 5 // 8 + stem_width + head_size, size * 5 // 8 + head_size // 2)],
                fill=note_color
            )

            # Cross bar
            draw.rectangle(
                [(size * 3 // 8, size // 4), (size * 5 // 8 + stem_width, size // 4 + stem_width)],
                fill=note_color
            )

            # Save in appropriate format
            if platform == "windows":
                img.save(icon_path, 'ICO', sizes=[(16, 16), (32, 32), (48, 48),
                                                 (64, 64), (128, 128), (256, 256)])
            elif platform == "darwin":
                img.save(icon_path, 'ICNS')
            else:
                img.save(icon_path, 'PNG')

            return True
        except ImportError:
            self.logger.error("PIL not installed, cannot create icons")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create icon: {e}")
            return False

    def create_version_info(self) -> Optional[str]:
        """Create version info file for Windows."""
        version_file = self.project_root / "version_info.txt"

        version_info = {
            'FileVersion': self.config.app_version,
            'ProductVersion': self.config.app_version,
            'CompanyName': self.config.app_author,
            'FileDescription': self.config.app_description,
            'InternalName': self.config.app_name.lower(),
            'LegalCopyright': self.config.app_copyright,
            'OriginalFilename': f"{self.config.app_name}.exe",
            'ProductName': self.config.app_name,
        }

        content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({self.config.app_version.replace('.', ', ')}, 0),
    prodvers=({self.config.app_version.replace('.', ', ')}, 0),
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
          [StringStruct(u'CompanyName', u'{version_info["CompanyName"]}'),
            StringStruct(u'FileDescription', u'{version_info["FileDescription"]}'),
            StringStruct(u'FileVersion', u'{version_info["FileVersion"]}'),
            StringStruct(u'InternalName', u'{version_info["InternalName"]}'),
            StringStruct(u'LegalCopyright', u'{version_info["LegalCopyright"]}'),
            StringStruct(u'OriginalFilename', u'{version_info["OriginalFilename"]}'),
            StringStruct(u'ProductName', u'{version_info["ProductName"]}'),
            StringStruct(u'ProductVersion', u'{version_info["ProductVersion"]}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)"""

        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.success(f"Created version info: {version_file}")
            return str(version_file)
        except Exception as e:
            self.logger.error(f"Failed to create version info: {e}")
            return None


class SpecGenerator:
    """Generates PyInstaller spec files."""

    def __init__(self, config: BuildConfig, logger: BuildLogger):
        self.config = config
        self.logger = logger
        self.project_root = Path.cwd()
        self.platform = sys.platform.lower()

    def generate(self) -> Path:
        """Generate PyInstaller spec file."""
        spec_file = self.project_root / f"{self.config.app_name}.spec"

        # Platform-specific settings
        platform_config = self.config.platforms.get(self.platform, {})
        icon_path = platform_config.get('icon', 'assets/icon.png')

        # Prepare data files
        data_files_str = self._format_data_files()

        # Prepare hidden imports
        hidden_imports = self.config.hidden_imports + self._get_platform_imports()

        # Prepare excludes
        excludes = self.config.excludes + self._get_platform_excludes()

        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Generated by Music Player Build Script v2.0
# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

import sys
from pathlib import Path

# Project paths
project_root = Path(r"{self.project_root}")
src_dir = project_root / "{self.config.src_dir}"

# Analysis
a = Analysis(
    [str(src_dir / "{self.config.main_script}")],
    pathex=[
        str(project_root),
        str(src_dir),
    ],
    binaries=[],
    datas=[
{data_files_str}
    ],
    hiddenimports=[
{self._format_list(hidden_imports, 8)}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
{self._format_list(excludes, 8)}
    ],
    noarchive=False,
    optimize={0 if self.config.debug else 2},
)

# PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# EXE configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="{self.config.app_name}",
    debug={str(self.config.debug).lower()},
    bootloader_ignore_signals=False,
    strip={str(self.config.strip).lower()},
    upx={str(self.config.upx_compression).lower()},
    upx_exclude={self.config.upx_exclude},
    runtime_tmpdir=None,
    console={str(self.config.console).lower()},
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r"{icon_path}" if Path(r"{icon_path}").exists() else None,
    version=r"{self.project_root / 'version_info.txt'}" if sys.platform == "win32" and Path(r"{self.project_root / 'version_info.txt'}").exists() else None,
)
'''

        # Write spec file
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        self.logger.success(f"Generated spec file: {spec_file}")
        return spec_file

    def _format_data_files(self) -> str:
        """Format data files for spec file."""
        if not self.config.data_files:
            return "    ]"

        lines = []
        for item in self.config.data_files:
            source = item.get('source', '')
            dest = item.get('destination', '')
            lines.append(f'        (r"{source}", r"{dest}"),')

        return '\n'.join(lines) + '\n    ]'

    def _format_list(self, items: List[str], indent: int = 0) -> str:
        """Format a list for spec file."""
        if not items:
            return '    ]'

        prefix = ' ' * indent
        lines = [f'{prefix}{repr(item)},' for item in items]
        return '\n'.join(lines)

    def _get_platform_imports(self) -> List[str]:
        """Get platform-specific hidden imports."""
        if self.platform.startswith('win'):
            return [
                'win32timezone',
                'win32file',
                'win32gui',
                'win32con',
            ]
        elif self.platform.startswith('darwin'):
            return [
                'AppKit',
                'Foundation',
                'Cocoa',
                'PyObjCTools',
            ]
        else:
            return [
                'gtk',
                'gobject',
                'gio',
            ]

    def _get_platform_excludes(self) -> List[str]:
        """Get platform-specific excludes."""
        if self.platform.startswith('win'):
            return ['gtk', 'gobject', 'gio']
        elif self.platform.startswith('darwin'):
            return ['gtk', 'gobject', 'gio', 'win32gui']
        else:
            return ['win32gui', 'win32con', 'win32file']


class MusicPlayerBuilder:
    """Main builder class."""

    def __init__(self, config_file: Optional[str] = None):
        self.logger = BuildLogger("build.log")
        self.config = self._load_config(config_file)
        self.dep_manager = DependencyManager(self.logger)
        self.asset_manager = AssetManager(self.config, self.logger)
        self.spec_generator = SpecGenerator(self.config, self.logger)
        self.project_root = Path.cwd()

    def _load_config(self, config_file: Optional[str]) -> BuildConfig:
        """Load build configuration from file."""
        if config_file and Path(config_file).exists():
            self.logger.info(f"Loading config from: {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return BuildConfig(**data.get('build', {}))
        else:
            self.logger.info("Using default build configuration")
            return self._get_default_config()

    def _get_default_config(self) -> BuildConfig:
        """Get default build configuration."""
        return BuildConfig(
            data_files=[
                {"source": "src/config/default_config.yaml", "destination": "config"},
                {"source": "src/ui/styles", "destination": "ui/styles"},
                {"source": "src/ui/resources", "destination": "ui/resources"},
                {"source": "README.md", "destination": "."},
                {"source": "LICENSE", "destination": "."},
            ],
            hidden_imports=[
                # Pygame
                "pygame.sdl2_video",
                "pygame.mixer_music",
                "pygame.mixer",

                # PyQt6
                "PyQt6.QtCore",
                "PyQt6.QtGui",
                "PyQt6.QtWidgets",
                "PyQt6.QtSvg",

                # Audio formats
                "mutagen.mp3",
                "mutagen.flac",
                "mutagen.wavpack",
                "mutagen.oggvorbis",
                "mutagen.mp4",
                "mutagen.m4a",
                "mutagen.wma",
                "mutagen.apev2",

                # LLM Queue
                "requests",
                "openai",
                "anthropic",
                "tiktoken",

                # YAML
                "yaml",
                "yaml.scanner",
                "yaml.parser",
                "yaml.serializer",
                "yaml.resolver",

                # SSL
                "ssl",
                "_ssl",
                "certifi",
            ],
            excludes=[
                "tkinter",
                "unittest",
                "test",
                "tests",
                "doctest",
                "pdb",
                "matplotlib",
                "numpy",
                "scipy",
                "pandas",
                "IPython",
                "jupyter",
                "notebook",
                "tensorflow",
                "torch",
                "cv2",
            ],
            platforms={
                "windows": {
                    "icon": "assets/icon.ico",
                    "version_info": "version_info.txt",
                },
                "darwin": {
                    "icon": "assets/icon.icns",
                    "bundle_id": "com.musicplayer.app",
                },
                "linux": {
                    "icon": "assets/icon.png",
                    "desktop_file": "musicplayer.desktop",
                }
            }
        )

    def clean(self):
        """Clean build artifacts."""
        self.logger.info("Cleaning build artifacts...")

        dirs_to_clean = [
            self.project_root / "build",
            self.project_root / "dist",
            self.project_root / "__pycache__",
        ]

        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.logger.success(f"Cleaned: {dir_path}")

        # Clean spec files
        for spec_file in self.project_root.glob("*.spec"):
            spec_file.unlink()
            self.logger.success(f"Cleaned: {spec_file}")

    def build(self) -> bool:
        """Build the executable."""
        self.logger.info(f"Building {self.config.app_name} v{self.config.app_version}")
        self.logger.info("=" * 60)

        # Check dependencies
        if not self.dep_manager.check_python_version():
            return False

        required_packages = ["PyInstaller"]
        if not self.dep_manager.check_dependencies(required_packages):
            return False

        # Create assets
        self.asset_manager.create_icons()
        if sys.platform == "win32":
            self.asset_manager.create_version_info()

        # Clean previous build
        if self.config.clean_build:
            self.clean()

        # Generate spec file
        spec_file = self.spec_generator.generate()

        # Build command
        cmd = [
            "pyinstaller",
            "--clean",
            "--noconfirm",
        ]

        if self.config.debug:
            cmd.append("--debug")

        cmd.append(str(spec_file))

        # Run build
        self.logger.info("Starting PyInstaller build...")
        self.logger.info(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.success("Build completed successfully!")

            # Show results
            dist_path = self.project_root / self.config.dist_dir
            if dist_path.exists():
                self.logger.info(f"\nOutput directory: {dist_path}")
                for file in dist_path.rglob("*"):
                    if file.is_file():
                        size_mb = file.stat().st_size / 1024 / 1024
                        self.logger.info(f"  - {file.relative_to(dist_path)} ({size_mb:.1f} MB)")

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Build failed: {e}")
            self.logger.error(e.stderr)
            return False

    def package(self) -> bool:
        """Create distribution packages."""
        self.logger.info("\nCreating distribution packages...")

        if sys.platform == "win32":
            return self._create_windows_installer()
        elif sys.platform == "darwin":
            return self._create_macos_bundle()
        else:
            return self._create_linux_package()

    def _create_windows_installer(self) -> bool:
        """Create Windows installer."""
        # Implementation for NSIS/Inno Setup
        self.logger.info("Windows installer creation not implemented yet")
        return False

    def _create_macos_bundle(self) -> bool:
        """Create macOS app bundle."""
        self.logger.info("macOS bundle creation not implemented yet")
        return False

    def _create_linux_package(self) -> bool:
        """Create Linux package."""
        self.logger.info("Linux package creation not implemented yet")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Music Player Build Script v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py                    # Build with default settings
  python build.py --config custom.yaml  # Build with custom config
  python build.py --debug --console    # Debug build with console
  python build.py --clean-only         # Clean build artifacts only
  python build.py --package            # Build and create installer
        """
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to build configuration file (YAML)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    parser.add_argument(
        "--console",
        action="store_true",
        help="Show console window (Windows only)"
    )

    parser.add_argument(
        "--single-file",
        action="store_true",
        default=True,
        help="Create single file executable (default)"
    )

    parser.add_argument(
        "--dir",
        action="store_true",
        help="Create directory bundle instead of single file"
    )

    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean build artifacts, don't build"
    )

    parser.add_argument(
        "--package",
        "-p",
        action="store_true",
        help="Create distribution package after building"
    )

    parser.add_argument(
        "--no-upx",
        action="store_true",
        help="Disable UPX compression"
    )

    args = parser.parse_args()

    # Create builder
    builder = MusicPlayerBuilder(args.config)

    # Apply command line overrides
    if args.debug:
        builder.config.debug = True
        builder.config.strip = False
    if args.console:
        builder.config.console = True
    if args.dir:
        builder.config.single_file = False
    if args.no_upx:
        builder.config.upx_compression = False

    # Run build
    if args.clean_only:
        builder.clean()
    else:
        if builder.build():
            if args.package:
                builder.package()
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()