#!/usr/bin/env python3
"""
Music Player Build Script v3.0
A modern, modular build system for creating cross-platform executables.

Usage:
    python build.py                          # Build with default (release) profile
    python build.py --profile dev            # Build with development profile
    python build.py --dry-run                # Generate spec file only
    python build.py --clean                  # Clean build artifacts
"""

import os
import sys
import shutil
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# ----------------------------------------------------------------------------
# Dependency Check
# ----------------------------------------------------------------------------

def ensure_dependencies():
    """Ensure required build dependencies are available."""
    missing = []
    
    try:
        import yaml  # noqa: F401
    except ImportError:
        missing.append("PyYAML")
    
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        missing.append("pyinstaller")
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + missing,
            check=True
        )
        print("Dependencies installed. Please re-run the script.")
        sys.exit(0)

ensure_dependencies()

import yaml  # noqa: E402

# ----------------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------------

def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure logging with colored output."""
    logger = logging.getLogger("build")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    return logger

log = setup_logging()

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

@dataclass
class BuildConfig:
    """Build configuration container."""
    # App metadata
    app_name: str = "MusicPlayer"
    app_version: str = "1.0.0"
    app_description: str = "Python Music Player with PyQt6"
    app_copyright: str = "Copyright (C) 2024 Music Player Team"
    app_author: str = "Music Player Team"
    app_url: str = ""
    
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
    
    # Data files, hidden imports, excludes
    data_files: List[Dict[str, str]] = field(default_factory=list)
    hidden_imports: List[str] = field(default_factory=list)
    excludes: List[str] = field(default_factory=list)
    
    # Platform settings
    platforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    upx_exclude: List[str] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, config_path: Path, profile: str = "release") -> "BuildConfig":
        """Load configuration from YAML file with profile merging."""
        if not config_path.exists():
            log.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Start with base build config
        config_data = dict(data.get("build", {}))
        
        # Merge profile-specific settings
        if profile in data:
            profile_data = data[profile]
            log.info(f"Applying '{profile}' profile settings")
            config_data.update(profile_data)
        
        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in config_data.items() if k in known_fields}
        
        return cls(**filtered)


class PathManager:
    """Manages all build-related paths."""
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.src = project_root / "src"
        self.assets = project_root / "assets"
        self.config = project_root / "config"
        self.dist = project_root / "dist"
        self.build = project_root / "build"
    
    def get_icon(self, platform: str) -> Optional[Path]:
        """Get platform-appropriate icon path."""
        icons = {
            "win32": self.assets / "icon.ico",
            "darwin": self.assets / "icon.icns",
            "linux": self.assets / "icon.png",
        }
        icon = icons.get(platform, self.assets / "icon.png")
        return icon if icon.exists() else None
    
    def get_version_info(self) -> Optional[Path]:
        """Get Windows version info file."""
        version_file = self.root / "version_info.txt"
        return version_file if version_file.exists() else None


# ----------------------------------------------------------------------------
# Spec File Generator
# ----------------------------------------------------------------------------

class SpecBuilder:
    """Generates PyInstaller spec files."""
    
    def __init__(self, config: BuildConfig, paths: PathManager):
        self.config = config
        self.paths = paths
        self.platform = sys.platform
    
    def generate(self) -> Path:
        """Generate the .spec file."""
        spec_path = self.paths.root / f"{self.config.app_name}.spec"
        
        # Get platform-specific settings
        platform_config = self.config.platforms.get(self.platform, {})
        
        # Determine icon path
        icon_path = self.paths.get_icon(self.platform)
        icon_line = f'    icon=r"{icon_path}",' if icon_path else "    icon=None,"
        
        # Windows version info
        version_info = self.paths.get_version_info()
        if self.platform == "win32" and version_info:
            version_line = f'    version=r"{version_info}",'
        else:
            version_line = "    version=None,"
        
        # Build data files list
        datas = self._build_datas()
        
        # Build hidden imports
        hidden_imports = self.config.hidden_imports + self._platform_imports()
        
        # Build excludes
        excludes = self.config.excludes + self._platform_excludes()
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Auto-generated by Music Player Build Script v3.0
# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

from pathlib import Path

project_root = Path(r"{self.paths.root}")
src_dir = project_root / "{self.config.src_dir}"

a = Analysis(
    [str(src_dir / "{self.config.main_script}")],
    pathex=[str(project_root), str(src_dir)],
    binaries=[],
    datas={datas},
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes},
    noarchive=False,
    optimize={0 if self.config.debug else 2},
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="{self.config.app_name}",
    debug={self.config.debug},
    bootloader_ignore_signals=False,
    strip={self.should_strip()},
    upx={self.config.upx_compression},
    upx_exclude={self.config.upx_exclude},
    runtime_tmpdir=None,
    console={self.config.console},
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
{icon_line}
{version_line}
)
'''
        
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(spec_content)
        
        log.info(f"✓ Generated spec file: {spec_path}")
        return spec_path
    
    def _build_datas(self) -> List[tuple]:
        """Build data files list for spec."""
        datas = []
        for item in self.config.data_files:
            src = self.paths.root / item.get("source", "")
            dest = item.get("destination", ".")
            if src.exists():
                datas.append((str(src), dest))
            else:
                log.warning(f"Data file not found: {src}")
        return datas
    
    def _platform_imports(self) -> List[str]:
        """Get platform-specific hidden imports."""
        imports = {
            "win32": ["win32timezone", "win32file", "win32gui", "win32con"],
            "darwin": ["AppKit", "Foundation", "Cocoa", "PyObjCTools"],
            "linux": [],
        }
        return imports.get(self.platform, [])
    
    def _platform_excludes(self) -> List[str]:
        """Get platform-specific excludes."""
        excludes = {
            "win32": ["gtk", "gobject", "gio"],
            "darwin": ["gtk", "gobject", "gio", "win32gui"],
            "linux": ["win32gui", "win32con", "win32file"],
        }
        return excludes.get(self.platform, [])
    
    def should_strip(self) -> bool:
        """Check if strip should be enabled for this platform.
        
        The 'strip' command is a Unix tool and not available on Windows by default.
        Enabling it on Windows causes harmless but noisy warnings.
        """
        if self.platform == "win32":
            return False
        return self.config.strip


# ----------------------------------------------------------------------------
# Build Runner
# ----------------------------------------------------------------------------

class BuildRunner:
    """Executes the build process."""
    
    def __init__(self, config: BuildConfig, paths: PathManager):
        self.config = config
        self.paths = paths
    
    def clean(self):
        """Clean build artifacts."""
        log.info("Cleaning build artifacts...")
        
        dirs_to_clean = [self.paths.build, self.paths.dist]
        for d in dirs_to_clean:
            if d.exists():
                shutil.rmtree(d)
                log.info(f"  Removed: {d}")
        
        # Clean __pycache__ directories
        for pycache in self.paths.root.rglob("__pycache__"):
            if "venv" not in str(pycache):
                shutil.rmtree(pycache)
        
        log.info("✓ Clean complete")
    
    def build(self, spec_path: Path) -> bool:
        """Execute PyInstaller build."""
        log.info("=" * 60)
        log.info(f"Building {self.config.app_name} v{self.config.app_version}")
        log.info(f"Platform: {sys.platform}")
        log.info(f"Python: {sys.version.split()[0]}")
        log.info("=" * 60)
        
        cmd = ["pyinstaller", "--clean", "--noconfirm"]
        
        if self.config.debug:
            cmd.append("--log-level=DEBUG")
        
        cmd.append(str(spec_path))
        
        log.info(f"Command: {' '.join(cmd)}")
        log.info("")
        
        try:
            result = subprocess.run(cmd, check=True)
            
            log.info("")
            log.info("=" * 60)
            log.info("✓ BUILD SUCCESSFUL")
            log.info("=" * 60)
            
            self._show_output_info()
            return True
            
        except subprocess.CalledProcessError as e:
            log.error(f"✗ Build failed with exit code: {e.returncode}")
            return False
    
    def _show_output_info(self):
        """Display information about built files."""
        if not self.paths.dist.exists():
            return
        
        log.info("")
        log.info("Output files:")
        
        total_size = 0
        for file in self.paths.dist.rglob("*"):
            if file.is_file():
                size = file.stat().st_size
                total_size += size
                size_mb = size / 1024 / 1024
                log.info(f"  {file.name}: {size_mb:.1f} MB")
        
        log.info(f"  Total: {total_size / 1024 / 1024:.1f} MB")
        log.info(f"\nOutput directory: {self.paths.dist}")


# ----------------------------------------------------------------------------
# Main Entry Point
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Music Player Build Script v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py                    # Build release version
  python build.py --profile dev      # Build development version
  python build.py --dry-run          # Generate spec file only
  python build.py --clean            # Clean build artifacts
        """
    )
    
    parser.add_argument(
        "--profile", "-p",
        choices=["dev", "release"],
        default="release",
        help="Build profile to use (default: release)"
    )
    
    parser.add_argument(
        "--config", "-c",
        default="build_config.yaml",
        help="Path to config file (default: build_config.yaml)"
    )
    
    parser.add_argument(
        "--console",
        action="store_true",
        help="Show console window (override profile setting)"
    )
    
    parser.add_argument(
        "--no-upx",
        action="store_true",
        help="Disable UPX compression"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate spec file only, don't build"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts only"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    # Setup paths - script is in scripts/ subdirectory
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent  # Go up one level to project root
    paths = PathManager(project_root)
    
    # Load configuration (config file is in same directory as script)
    config_path = script_dir / args.config
    config = BuildConfig.from_yaml(config_path, args.profile)
    
    # Apply command-line overrides
    if args.console:
        config.console = True
    if args.no_upx:
        config.upx_compression = False
    if args.debug:
        config.debug = True
        config.strip = False
    
    # Create runner
    runner = BuildRunner(config, paths)
    
    # Handle clean-only mode
    if args.clean:
        runner.clean()
        return 0
    
    # Clean before build if configured
    if config.clean_build:
        runner.clean()
    
    # Generate spec file
    spec_builder = SpecBuilder(config, paths)
    spec_path = spec_builder.generate()
    
    # Dry-run mode
    if args.dry_run:
        log.info("Dry-run complete. Spec file generated.")
        return 0
    
    # Execute build
    success = runner.build(spec_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())