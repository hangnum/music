# 🎵 Python Music Player

A high-quality local music player designed with modular architecture.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

### Implemented

- 🎶 **Music Playback** - Support for MP3, FLAC, WAV, OGG, M4A, AAC and more formats
- 🎧 **Advanced Audio** - Gapless playback, crossfade, ReplayGain volume normalization
- 🎚️ **Equalizer** - 10-band professional equalizer with built-in presets (Rock, Pop, Jazz, etc.)
- 📚 **Library Management** - Automatically scan and index local music files
- 🔍 **Smart Search** - Search by track, artist, or album
- 📋 **Queue Management** - Flexible playback queue management
- 🔀 **Playback Modes** - Sequential, shuffle, single track repeat, list repeat
- 🏷️ **Tag Management** - Manually add custom tags to tracks
- 🏷️ **Smart Tagging** - LLM-powered automatic analysis of music style and mood for batch tagging
- 🤖 **Smart Queue** - Natural language queue reordering based on LLM (SiliconFlow/Gemini), supports semantic tag filtering
- 🎨 **Dark Theme** - Modern Spotify-inspired interface
- 📊 **Metadata Parsing** - Automatically read music file tag information

### In Development

- 📝 Lyrics display
- 🔔 System tray integration
- ⌨️ Global hotkeys

## 🛠️ Technology Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| GUI Framework | PyQt6 | Cross-platform graphical interface |
| Audio Engine | miniaudio / vlc / pygame | Multiple backend audio engine support, default miniaudio |
| Metadata Parsing | mutagen | Multi-format audio tag reading |
| Database | SQLite | Local data storage |
| Configuration | PyYAML | YAML format configuration files |
| LLM Service | SiliconFlow / Gemini | Smart features support (queue reordering, auto-tagging) |

## 📦 Installation

### Requirements

- Python 3.11+
- Conda (recommended) or pip
- (Optional) VLC Player (if using VLC backend)

### Using Conda

```bash
# Create virtual environment
conda create -n music python=3.11
conda activate music

# Install dependencies
pip install -r requirements.txt
```

### Using pip

```bash
pip install -r requirements.txt
```

## 🚀 Running

```bash
python src/main.py
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| `Space` | Play/Pause |
| `Ctrl+Right` | Next Track |
| `Ctrl+Left` | Previous Track |
| `Ctrl+Up` | Volume Up |
| `Ctrl+Down` | Volume Down |

## 📁 Project Structure

```text
music/
├── docs/                    # Design documents
│   ├── architecture.md      # System architecture
│   ├── technical_design.md  # Technical design
│   └── api.md               # API interface
├── src/                     # Source code
│   ├── core/                # Core modules
│   │   ├── audio_engine.py      # Audio engine base class
│   │   ├── engine_factory.py    # Audio engine factory
│   │   ├── miniaudio_engine.py  # Miniaudio backend (High Quality)
│   │   ├── vlc_engine.py        # VLC backend
│   │   ├── event_bus.py         # Event bus
│   │   ├── metadata.py          # Metadata parsing
│   │   ├── database.py          # Database management
│   │   └── llm_provider.py      # LLM provider abstraction
│   ├── models/              # Data models
│   │   ├── track.py         # Track
│   │   ├── album.py         # Album
│   │   ├── artist.py        # Artist
│   │   ├── playlist.py      # Playlist
│   │   └── eq_preset.py     # Equalizer presets
│   ├── services/            # Service layer
│   │   ├── player_service.py      # Playback service
│   │   ├── library_service.py     # Library service
│   │   ├── playlist_service.py    # Playlist service
│   │   ├── config_service.py      # Configuration service
│   │   ├── tag_service.py         # Tag service
│   │   ├── llm_queue_service.py   # Smart queue service
│   │   ├── llm_tagging_service.py # Smart tagging service
│   │   ├── tag_query_parser.py    # Tag query parser
│   │   └── llm_providers/         # LLM adapters (Gemini/SiliconFlow)
│   ├── ui/                  # UI layer
│   │   ├── main_window.py       # Main window
│   │   ├── widgets/             # UI components
│   │   ├── dialogs/             # Dialogs
│   │   │   ├── audio_settings_dialog.py # Audio settings
│   │   │   └── ...
│   │   └── styles/              # Stylesheets
│   └── main.py              # Program entry
├── tests/                   # Unit tests
├── config/                  # Configuration files
│   └── default_config.yaml  # Default configuration
└── requirements.txt         # Dependencies list
```

## 🏗️ Architecture Design

Adopts layered architecture design, following SOLID principles:

```text
┌─────────────────────────────────────┐
│            UI Layer                 │  PyQt6 Interface
├─────────────────────────────────────┤
│          Service Layer              │  Business Logic (Play, Library, LLM...)
├─────────────────────────────────────┤
│           Core Layer                │  Core Features (Audio, DB, EventBus)
├─────────────────────────────────────┤
│           Data Layer                │  Data Storage (SQLite, Config)
└─────────────────────────────────────┘
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run core module tests
python -m pytest tests/test_core.py -v

# Run service layer tests
python -m pytest tests/test_services.py -v
```

## 📄 Configuration

Configuration file is located at `config/default_config.yaml`:

```yaml
library:
  directories:
    - "D:\\User\\music\\music"  # Music library path
  supported_formats:
    - mp3
    - flac
    - wav
    - ogg

playback:
  default_volume: 0.8

ui:
  theme: dark
  window_width: 1200
  window_height: 800
```

## 📚 Documentation

For detailed design documents, please check the `docs/` directory:

- [System Architecture](docs/architecture.md) - Overall architecture design
- [Technical Design](docs/technical_design.md) - Module technical details
- [API Interface](docs/api.md) - Interface specifications

## 📝 License

MIT License