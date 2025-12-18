# Gemini Context: Python Music Player

## Project Overview

This project is a modular, high-quality local music player written in Python 3.11+. It features a modern GUI built with **PyQt6**, uses **pygame** for audio playback, **mutagen** for metadata parsing, and **SQLite** for data persistence.

The application follows a strict **Layered Architecture** (UI, Service, Core, Data) and uses an **Event Bus** for decoupled communication between components.

## Key Technologies

* **Language:** Python 3.11+
* **GUI:** PyQt6
* **Audio Engine:** pygame (extensible to others like VLC)
* **Metadata:** mutagen
* **Configuration:** PyYAML
* **Testing:** pytest

## Getting Started

### Installation

Ensure you have Python 3.11+ installed.

```bash
pip install -r requirements.txt
```

### Running the Application

The entry point is located at `src/main.py`.

```bash
python src/main.py
```

### Running Tests

Tests are located in the `tests/` directory.

```bash
# Run all tests
python -m pytest tests/

# Run specific modules
python -m pytest tests/test_core.py
```

## Architecture

The project adheres to SOLID principles and separates concerns into four main layers:

### 1. UI Layer (`src/ui/`)

* **Responsibility:** Handles user interaction and display.
* **Components:** `MainWindow`, `PlayerControls`, `LibraryWidget`.
* **Note:** The UI layer subscribes to events from the `EventBus` to update itself (e.g., progress bar, current track).

### 2. Service Layer (`src/services/`)

* **Responsibility:** Orchestrates business logic and coordinates between the UI and Core layers.
* **Key Services:**
  * `PlayerService`: Manages playback state (playing, paused), queue, and playback modes (shuffle, repeat).
  * `LibraryService`: Handles scanning and indexing music files.
  * `PlaylistService`: Manages user playlists.

### 3. Core Layer (`src/core/`)

* **Responsibility:** Provides low-level functionality and infrastructure.
* **Key Components:**
  * `AudioEngine`: Abstract wrapper around audio libraries (currently `pygame`).
  * `EventBus`: A thread-safe, singleton event system that enables decoupled communication. It handles dispatching events to the main Qt thread when necessary.
  * `DatabaseManager`: Handles SQLite connections.

### 4. Data Layer (`src/models/`, `config/`)

* **Responsibility:** Defines data structures and persistence.
* **Models:** `Track`, `Album`, `Artist`, `Playlist`.
* **Config:** YAML-based configuration.

## Directory Structure

```text
src/
├── core/           # Low-level logic (AudioEngine, EventBus, Database)
├── models/         # Data classes (Track, Album, etc.)
├── services/       # Business logic (PlayerService, LibraryService)
├── ui/             # PyQt6 Widgets and Windows
└── main.py         # Application Entry Point
docs/               # Detailed documentation (Architecture, API)
tests/              # Unit and Integration tests
```

## Development Conventions

* **Type Hinting:** Extensive use of Python type hints (`typing` module).
* **Event-Driven:** Major state changes (track change, volume change) are propagated via `EventBus`.
* **Dependency Injection:** Services often take dependencies (like `AudioEngine`) in their constructors to facilitate testing.
* **Thread Safety:** The `EventBus` handles bridging background threads (e.g., audio playback monitoring) to the UI thread.

## File Organization Rules

> **IMPORTANT**: All files must be placed in their corresponding directories.

| 文件类型 | 目标目录 | 示例 |
|---------|---------|------|
| 文档 | `docs/` | `docs/architecture.md` |
| 测试代码 | `tests/` | `tests/test_tag_service.py` |
| 源代码 | `src/` 对应层 | `src/services/tag_service.py` |
| 配置文件 | `config/` | `config/default_config.yaml` |

禁止在项目根目录或其他非标准位置创建源代码或测试文件。

细化任务，序列化任务，每次在接受用户指令后，指定长序列可执行的计划
