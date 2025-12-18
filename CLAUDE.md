# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a high-quality desktop music player application built with Python, featuring a modular architecture, modern UI design inspired by Apple Music, and comprehensive audio format support.

**Technology Stack:**
- GUI Framework: PyQt6 (cross-platform desktop interface)
- Audio Engine: pygame (with VLC backend support)
- Metadata: mutagen (multi-format audio tag parsing)
- Database: SQLite (local data storage)
- Configuration: PyYAML (human-readable config files)
- Testing: pytest + pytest-qt (comprehensive test suite)

## Key Development Commands

### Environment Setup
```bash
# Create virtual environment (recommended)
conda create -n music python=3.11
conda activate music

# Install dependencies
pip install -r requirements.txt

# Alternative pip setup
pip install -r requirements.txt
```

### Running the Application
```bash
# Run from project root
python src/main.py

# Run from src directory
cd src && python main.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_core.py -v
python -m pytest tests/test_services.py -v
python -m pytest tests/test_integration.py -v

# Run with coverage (if coverage installed)
python -m pytest tests/ --cov=src -v
```

### Building Executables
```bash
# Build for current platform (automated script)
python build.py

# Windows - run batch file
build.bat

# Unix/Linux/macOS - run shell script
chmod +x build.sh
./build.sh

# Build with custom config
python build.py --config build_config.yaml
```

### Code Quality (Development Tools)
```bash
# Format code (if black is installed)
black src/ tests/

# Lint code (if flake8 is installed)
flake8 src/ tests/

# Type checking (if mypy is installed)
mypy src/
```

### Database Management
```bash
# The application creates SQLite database automatically
# Database file: music_library.db

# Manual database inspection (if needed)
sqlite3 music_library.db
.tables
.schema tracks
```

## Architecture Overview

### Layered Architecture Design

The application follows a strict 4-layer architecture pattern to ensure separation of concerns and maintainability:

```
┌─────────────────────────────────────┐
│            UI Layer                 │  PyQt6 Interface + Widgets
├─────────────────────────────────────┤
│          Service Layer              │  Business Logic Orchestration
├─────────────────────────────────────┤
│           Core Layer                │  Fundamental Capabilities
├─────────────────────────────────────┤
│           Data Layer                │  Persistence & Storage
└─────────────────────────────────────┘
```

#### Layer Responsibilities

**UI Layer (`src/ui/`)**
- Presentation logic only
- Event handling and user interaction
- No business logic embedded
- Key components:
  - `MainWindow.py` - Main application window
  - `widgets/` - Reusable UI components
  - `styles/` - Theme and styling (dark/light themes)
  - `dialogs/` - Modal dialogs and settings windows

**Service Layer (`src/services/`)**
- Business logic coordination
- Orchestrate core layer components
- Provide clean interfaces for UI layer
- Key services:
  - `PlayerService.py` - Playback control and queue management
  - `LibraryService.py` - Media library operations
  - `PlaylistService.py` - Playlist CRUD operations
  - `ConfigService.py` - Configuration management
  - `LLMQueueService.py` - AI-powered queue management with semantic fetch

**Core Layer (`src/core/`)**
- Fundamental capabilities and utilities
- Abstract interfaces for extensibility
- Thread-safe operations
- Key modules:
  - `audio_engine.py` - Audio playback with multiple backends
  - `event_bus.py` - Publish-subscribe event system
  - `metadata.py` - Audio file metadata extraction
  - `database.py` - SQLite operations with connection pooling

**Data Layer (`src/models/` & Database)**
- Data persistence and modeling
- SQLite database with proper schema
- Entity-relationship design
- Key models:
  - `Track.py` - Music track information
  - `Album.py` - Album metadata
  - `Artist.py` - Artist information
  - `Playlist.py` - Playlist data structure

### Database Schema

The application uses SQLite with a well-structured schema:

```sql
-- Core entities with relationships
artists (id, name, image_path, created_at)
albums (id, title, artist_id, year, cover_path, created_at)
tracks (id, title, file_path, duration_ms, bitrate, sample_rate, format, artist_id, album_id, track_number, genre, year, play_count, last_played, rating, created_at)
playlists (id, name, description, cover_path, created_at, updated_at)
playlist_tracks (playlist_id, track_id, position, added_at)

-- Performance indexes
CREATE INDEX idx_tracks_artist ON tracks(artist_id);
CREATE INDEX idx_tracks_album ON tracks(album_id);
CREATE INDEX idx_tracks_title ON tracks(title);
```

## Important Patterns and Conventions

### Design Patterns Implementation

**Singleton Pattern**
- `EventBus`, `DatabaseManager`, `AudioEngine` use singleton pattern
- Thread-safe implementation with double-checked locking
- Instance reset methods available for testing

**Observer Pattern**
- Event-driven architecture using EventBus
- Asynchronous event processing with ThreadPoolExecutor
- Type-safe event types and data structures

**Strategy Pattern**
- Audio engine backends (pygame/VLC)
- Metadata parsers for different audio formats
- Sorting and filtering strategies

**Factory Pattern**
- Metadata parser creation based on file format
- UI widget factories for themes

### Code Organization Patterns

**Dependency Injection**
- Services receive dependencies through constructors
- Abstract base classes for interfaces
- Easy mocking for testing

**Layer Communication**
- UI → Services → Core → Data (top-down only)
- Services communicate via EventBus (horizontal)
- No circular dependencies allowed

**Data Flow**
```python
# Typical data flow
User Action → UI Widget → Service Method → Core Operation → Database
                                 ↓
                            EventBus → UI Updates
```

### Conventions

**File Structure**
```
src/
├── main.py              # Application entry point
├── core/               # Core capabilities
│   ├── audio_engine.py # Audio playback with multiple backends
│   ├── event_bus.py   # Event system
│   ├── metadata.py     # Metadata extraction
│   └── database.py     # Database operations
├── services/          # Business logic layer
│   ├── player_service.py
│   ├── library_service.py
│   ├── playlist_service.py
│   ├── config_service.py
│   └── llm_queue_service.py  # AI queue management
├── models/            # Data models
│   ├── track.py
│   ├── album.py
│   ├── artist.py
│   └── playlist.py
└── ui/               # Presentation layer
    ├── main_window.py
    ├── widgets/      # Reusable components
    ├── dialogs/      # Modal dialogs
    ├── styles/       # CSS/Qt stylesheets
    └── resources/    # Icons, images
```

**Naming Conventions**
- Classes: PascalCase (e.g., `PlayerService`, `AudioEngine`)
- Methods: snake_case (e.g., `play_track`, `set_volume`)
- Constants: UPPER_SNAKE_CASE (e.g., `SUPPORTED_FORMATS`)
- Private members: _leading_underscore (e.g., `_current_index`)

**Error Handling**
- Graceful degradation for audio playback errors
- Event-based error reporting through EventBus
- Comprehensive logging for debugging

**Thread Safety**
- UI operations on main thread
- Database operations use thread-local connections
- Event processing in separate thread pool
- Audio engine monitoring in background thread

## Key Technical Features

### Audio Engine Architecture
- Abstract base class for multiple backends
- Currently implemented: PygameAudioEngine
- Planned: VLC backend for better format support
- Thread-safe playback control with state management

### Event System
- Type-safe event types using Enum
- Both synchronous and asynchronous event publishing
- Automatic cleanup and error handling
- Support for event filtering and prioritization

### Configuration Management
- YAML-based configuration files
- Hot-reload capability for some settings
- Validation and fallback mechanisms
- User preferences persistence

### LLM Queue Service (New Feature)
- AI-powered music queue management
- Semantic library fetching with configurable providers
- JSON mode support for structured responses
- Fallback mechanisms for large catalogs
- Integration with existing event system

### Testing Strategy
- Comprehensive unit tests for all layers
- Integration tests for service interactions
- UI tests using pytest-qt
- Test database isolation and cleanup

### Performance Optimizations
- Lazy loading for large music libraries
- Metadata caching to minimize file I/O
- Database connection pooling
- Incremental library scanning

## Development Guidelines

### Adding New Features
1. **Data Layer**: Define models and database schema
2. **Core Layer**: Implement core capabilities if needed
3. **Service Layer**: Add business logic coordination
4. **UI Layer**: Create interface components
5. **Testing**: Write comprehensive tests

### Audio Format Support
- Supported formats: MP3, FLAC, WAV, OGG, M4A, AAC, WMA, APE
- Metadata parsing for each format
- Cover art extraction where available
- Fallback to filename when metadata missing

### UI Development
- Use Qt Designer for complex layouts (if needed)
- Follow Apple Music-inspired design patterns
- Implement responsive layouts for different screen sizes
- Support both dark and light themes

### Code Quality Standards
- Follow PEP 8 style guidelines
- Type hints for all public APIs
- Docstrings for all classes and methods
- Comprehensive error handling
- Logging for debugging and monitoring

## Project Status and Roadmap

### Current Status (v1.0.0)
- ✅ Core playback functionality
- ✅ Library management and scanning
- ✅ Playlist creation and management
- ✅ Apple Music-inspired UI design
- ✅ Dark theme implementation
- ✅ Event-driven architecture
- ✅ Comprehensive test suite
- ✅ LLM queue assistant with semantic library fetch

### Planned Features
- 🚧 Audio equalizer
- 🚧 Lyrics display and synchronization
- 🚧 System tray integration
- 🚧 Global keyboard shortcuts
- 🚧 Crossfade playback
- 🚧 Plugin system for extensibility

### Performance Targets
- Startup time: < 3 seconds
- Memory usage: < 200MB (idle)
- Library scan: 1000 tracks/minute
- Search response: < 50ms
- Playback latency: < 100ms

## Troubleshooting

### Common Issues
- **Audio playback fails**: Check file format support and pygame installation
- **Database locked**: Ensure only one instance running
- **High memory usage**: Check for large music libraries, consider pagination
- **Slow startup**: Verify library database integrity

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=src
python -m pytest tests/ -v --log-cli-level=DEBUG
```

### Development Environment Setup
```bash
# Ensure all development dependencies
pip install -r requirements.txt
pip install pytest pytest-qt black flake8 mypy

# Run pre-commit hooks (if configured)
pre-commit run --all-files
```

This music player application demonstrates modern software architecture patterns with a clean separation of concerns, comprehensive testing, and extensible design suitable for desktop music playback requirements.