# Repository Guidelines

## Project Structure

- `src/`: application code
  - `src/core/`: low-level utilities (audio, events, metadata, database)
  - `src/models/`: domain models (`Track`, `Album`, `Artist`, `Playlist`)
  - `src/services/`: business logic (player, library scan, playlists, config)
  - `src/ui/`: PyQt6 UI (windows, widgets, styles)
  - `src/main.py`: app entry point
- `tests/`: pytest test suite (`test_*.py`)
- `config/`: YAML configuration (`config/default_config.yaml`)
- `docs/`: architecture and design notes

## Build, Test, and Development Commands

- Install deps: `pip install -r requirements.txt`
- Run app (from repo root): `python src/main.py`
- Run all tests: `python -m pytest tests/ -v`
- Run a single file: `python -m pytest tests/test_core.py -v`

Keep commands run from the repository root so imports that rely on `src/` behave consistently.

## Coding Style & Naming Conventions

- Python 3.11+; use 4-space indentation and PEP 8 conventions.
- Names: modules/files in `snake_case.py`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`.
- Prefer small, layered changes: `core` (foundations) → `services` (logic) → `ui` (presentation).
- No formatter/linter is enforced in-repo; keep diffs clean and consistent with surrounding code.

## Testing Guidelines

- Frameworks: `pytest` (+ `pytest-qt` for Qt-related tests).
- Place new tests in `tests/test_<area>.py` and name tests `test_<behavior>()`.
- Tests may create temporary SQLite DB files (e.g., `test_*.db`); avoid committing generated artifacts.
- `tests/test_integration.py` scans a local music directory; adjust the path for your machine if you intend to run it.

## Commit & Pull Request Guidelines

- Follow the existing conventional-style subjects: `feat: ...`, `fix: ...`, `docs: ...`, `style: ...`.
  - Example: `fix: prevent crash when skipping tracks`
- PRs should include: a clear description, linked issue (if any), and screenshots/GIFs for UI changes.
- Update docs/tests when behavior changes (especially for `config/` defaults and library scanning).
