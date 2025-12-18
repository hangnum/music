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
- Treat `config/default_config.yaml` as a read-only template; user/runtime state should be written to a user data directory (e.g., `%APPDATA%`, `~/.config`), not back into the repo.
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

## 代码审查（中文）

作为代码审查的默认检查清单：

1. 代码风格：遵循 `docs/code_style.md` 与 PEP 8（以仓库既有风格为准）。
2. 架构设计：遵循 `docs/architecture.md`，保持 `core -> services -> ui` 分层；跨组件通信优先使用 `core.event_bus.EventBus`。
3. 异常处理：避免 `except Exception: pass` 吞错；需要记录日志或通过 `EventBus` 上报错误。
4. 线程与 Qt：后台线程不得直接操作 Qt 控件；使用 `QThread`/worker 时需要可取消，并在窗口/对话框关闭时做清理。
5. 配置与本地状态：`config/default_config.yaml` 仅作为默认模板；运行时的用户配置/窗口状态/扫描路径应写入用户目录（如 `%APPDATA%`/`~/.config`），不要回写仓库文件。
6. 安全与隐私：不得提交任何真实 API Key/Token；优先使用环境变量（例如 `SILICONFLOW_API_KEY`）注入密钥；避免提交本机路径/本地工具配置（例如 `.claude/settings.local.json`）。
