# Gemini Context: Python Music Player

## Project Overview

This project is a modular, high-quality local music player written in Python 3.11+. It features a modern GUI built with **PyQt6**, uses **miniaudio** (default) or **VLC/pygame** for audio playback, **mutagen** for metadata parsing, and **SQLite** for data persistence.

The application follows a strict **Layered Architecture** (UI, Service, Core, Data) and uses an **Event Bus** for decoupled communication between components.

## Key Technologies

* **Language:** Python 3.11+
* **GUI:** PyQt6
* **Audio Engine:** miniaudio (High Fidelity), VLC, pygame
* **Metadata:** mutagen
* **LLM Providers:** SiliconFlow, Google Gemini
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
* **Components:** `MainWindow`, `PlayerControls`, `LibraryWidget`, `AudioSettingsDialog`.
* **Note:** The UI layer subscribes to events from the `EventBus` to update itself (e.g., progress bar, current track).

### 2. Service Layer (`src/services/`)

* **Responsibility:** Orchestrates business logic and coordinates between the UI and Core layers.
* **Key Services:**
  * `PlayerService`: Manages playback state, queue, and engine selection (via Factory).
  * `LibraryService`: Handles scanning and indexing music files.
  * `PlaylistService`: Manages user playlists.
  * `TagService`: Manages music tags.
  * `LLMQueueService`: Orchestrates LLM-based reordering.
  * `LLMTaggingService`: Manages batch tagging of tracks using LLM.
  * `TagQueryParser`: Parses natural language into tag queries.

### 3. Core Layer (`src/core/`)

* `EventBus`: A thread-safe, singleton event system that enables decoupled communication. It handles dispatching events to the main Qt thread when necessary.
* `DatabaseManager`: Handles SQLite connections.
* `AudioEngineFactory`: Creates audio engine instances (`miniaudio`, `vlc`, `pygame`).

### 4. Data Layer (`src/models/`, `config/`)

* **Responsibility:** Defines data structures and persistence.
* **Models:** `Track`, `Album`, `Artist`, `Playlist`.
* **Config:** YAML-based configuration.

## Directory Structure

```text
src/
├── app/            # Application Bootstrap & DI Container
├── core/           # Low-level logic (AudioEngine, EventBus, Database, LLMProvider)
├── models/         # Data classes (Track, Album, Tag, etc.)
├── services/       # Business logic (PlayerService, LibraryService, TagService)
│   └── llm_providers/ # LLM implementations (Gemini, SiliconFlow)
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

| File Type | Target Directory | Example |
|-----------|------------------|---------|
| Documentation | `docs/` | `docs/architecture.md` |
| Test Code | `tests/` | `tests/test_tag_service.py` |
| Source Code | `src/` (corresponding layer) | `src/services/tag_service.py` |
| Configuration | `config/` | `config/default_config.yaml` |

Do not create source code or test files in the project root or other non-standard locations.

## 6. Agent Directives

As an agent, you need to act as a senior software engineer who highly adheres to software engineering standards.
To write the code, please refer to the docs/code_style.md file to ensure that the code style meets the project requirements.

* **Planning**: Through detailed planning, design executable plans in advance to effectively avoid errors.
* **Architecture**: The architecture design should fully consider scalability, maintainability, and testability.
* **Code Quality**: The code should maintain a low degree of coupling, high reusability, and high readability.
