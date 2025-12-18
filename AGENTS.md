# Repository Guidelines

## Project Structure

- `src/`: application code (Python package)
  - `src/core/`: infrastructure + low-level utilities (`audio_engine.py`, `event_bus.py`, `metadata.py`, `database.py`)
  - `src/models/`: domain models (`Track`, `Album`, `Artist`, `Playlist`)
  - `src/services/`: orchestration/business logic (`PlayerService`, `LibraryService`, `PlaylistService`, `ConfigService`, `LLMQueueService`)
  - `src/ui/`: PyQt6 UI (`main_window.py`, `widgets/`, `dialogs/`, `styles/`, `resources/`)
  - `src/main.py`: app entry point
- `config/`: YAML configuration (`config/default_config.yaml`)
- `tests/`: pytest test suite (`test_*.py`, plus `pytest-qt` for Qt/UI tests)
- `docs/`: architecture and design notes
- Build/packaging: `build.py`, `build_config.yaml`, `build.bat`, `build.sh`, `MusicPlayer.spec`, `assets/`

Avoid editing or committing generated/host-specific artifacts like `venv/`, `__pycache__/`, `*.pyc`, and local `*.db` files.

## Build, Test, and Development Commands

- Install deps: `pip install -r requirements.txt`
- Run app (from repo root): `python src/main.py`
- Run all tests: `python -m pytest tests/ -v`
- Run a single file: `python -m pytest tests/test_core.py -v`
- Build executable: `python build.py` (or `build.bat` / `./build.sh`)
- Build with custom config: `python build.py --config build_config.yaml`

Keep commands run from the repository root so imports that rely on `src/` behave consistently.

## Architecture & Design Rules

- Follow the layered architecture: `core` -> `services` -> `ui`; `models` are shared data structures.
- Use `core.event_bus.EventBus` for cross-component communication (playback, library scan, config/theme, errors); avoid updating Qt widgets from worker threads.
  - `EventBus` dispatches callbacks onto the Qt main thread when a Qt app exists; prefer publishing events over direct cross-thread UI calls.
- Keep DB access behind `core.database.DatabaseManager` and service layer APIs (`LibraryService`, `PlaylistService`) rather than UI-side SQL.
- Prefer dependency injection for testability (e.g., pass `AudioEngineBase`, `DatabaseManager`, or an LLM client into services instead of hardcoding).
- Playback queue persistence is handled by `src/services/queue_persistence_service.py` (DB table `app_state`, key `playback.last_queue`) and wired from `src/ui/main_window.py`.
- LLM queue history/cache is handled by `src/services/llm_queue_cache_service.py` (DB table `llm_queue_history`) and surfaced in `src/ui/dialogs/llm_queue_chat_dialog.py` (history list + cache hit fast path).

## Coding Style & Naming Conventions

- Python 3.11+; use 4-space indentation and PEP 8 conventions.
- Type hints for public APIs; add docstrings for classes and non-trivial methods.
- Names: modules/files in `snake_case.py`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`.
- Prefer small, layered changes: `core` (foundations) -> `services` (logic) -> `ui` (presentation).
- No formatter/linter is enforced in-repo; keep diffs clean and consistent with surrounding code.

## Configuration & Secrets

- Default config lives in `config/default_config.yaml`; update docs/tests when defaults change.
- LLM queue management is implemented in `src/services/llm_queue_service.py` and configured under `llm.*`.
- LLM queue cache/history is configured under `llm.queue_manager.cache.*` (enabled/ttl/history size).
- Playback queue persistence is configured under `playback.persist_queue` and `playback.persist_queue_max_items`.
- Prefer API keys via env var `SILICONFLOW_API_KEY` (`llm.siliconflow.api_key_env`); never commit real API keys or personal endpoints.

## Testing Guidelines

- Frameworks: `pytest` (+ `pytest-qt` for Qt-related tests).
- Place new tests in `tests/test_<area>.py` and name tests `test_<behavior>()`.
- Tests may create temporary SQLite DB files (e.g., `test_*.db`); avoid committing generated artifacts.
- Tests should not make network calls; inject fakes/mocks (see `tests/test_llm_queue_service.py`).
- Singletons exist (`ConfigService`, `DatabaseManager`, `EventBus`); reset in tests when needed via `*.reset_instance()`.
- `tests/test_integration.py` scans a local music directory; adjust the path for your machine if you intend to run it.

## Commit & Pull Request Guidelines

- Follow the existing conventional-style subjects: `feat: ...`, `fix: ...`, `docs: ...`, `style: ...`.
  - Example: `fix: prevent crash when skipping tracks`
- PRs should include: a clear description, linked issue (if any), and screenshots/GIFs for UI changes.
- Update docs/tests when behavior changes (especially for `config/` defaults and library scanning).
