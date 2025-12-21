from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import TYPE_CHECKING, List, Optional
import json

from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QFrame,
)
from PyQt6.QtGui import QKeyEvent

from models.track import Track
from services.llm_queue_cache_service import LLMQueueCacheService
from services.llm_queue_service import LLMQueueError, LLMQueueService, QueueReorderPlan

from ui.dialogs.llm_settings_dialog import LLMSettingsDialog
from ui.resources.design_tokens import tokens

if TYPE_CHECKING:
    from services.music_app_facade import MusicAppFacade
    from services.config_service import ConfigService
    from services.library_service import LibraryService


class ChatInputWidget(QPlainTextEdit):
    """Input box supporting Enter to send"""
    
    submit_requested = pyqtSignal()
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Enter to send, Ctrl+Enter/Shift+Enter for new line
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            modifiers = event.modifiers()
            if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                # Insert new line
                super().keyPressEvent(event)
            else:
                # Send
                self.submit_requested.emit()
                return
        super().keyPressEvent(event)


@dataclass(frozen=True)
class _QueueSnapshot:
    queue: List[Track]
    current_track_id: Optional[str]

@dataclass(frozen=True)
class _ResolvedResult:
    plan: QueueReorderPlan
    queue: List[Track]
    start_index: int


class _SuggestWorker(QObject):
    finished = pyqtSignal(object, object)  # result, error

    def __init__(
        self,
        config: "ConfigService",
        instruction: str,
        snapshot: _QueueSnapshot,
        library_context: dict,
        library: "LibraryService",
    ):
        super().__init__()
        self._config = config
        self._instruction = instruction
        self._snapshot = snapshot
        self._library_context = library_context
        self._library = library

    def run(self) -> None:
        try:
            svc = LLMQueueService(config=self._config)
            plan = svc.suggest_reorder(
                instruction=self._instruction,
                queue=self._snapshot.queue,
                current_track_id=self._snapshot.current_track_id,
                library_context=self._library_context,
            )
            new_queue, new_index = svc.resolve_plan(
                plan=plan,
                queue=self._snapshot.queue,
                current_track_id=self._snapshot.current_track_id,
                library=self._library,
            )
            self.finished.emit(_ResolvedResult(plan=plan, queue=new_queue, start_index=new_index), None)
        except Exception as e:
            self.finished.emit(None, e)


class LLMQueueChatDialog(QDialog):
    def __init__(self, facade: "MusicAppFacade", parent=None):
        """Initialize queue assistant dialog
        
        Args:
            facade: Application facade providing access to all services
            parent: Parent component
        """
        super().__init__(parent)
        self._facade = facade
        self._cache = LLMQueueCacheService(config=self._facade._config)
        self._pending_instruction: Optional[str] = None

        self.setWindowTitle("Queue Assistant (LLM)")
        self.setMinimumSize(780, 580)
        
        self._setup_styles()
        self._setup_ui()

        self._thread: Optional[QThread] = None
        self._worker: Optional[_SuggestWorker] = None

        self._append_system("You can describe the desired queue operation in natural language, and I will call LLM to provide a reorder plan and apply it to the current queue.")
        self._refresh_history()
    
    def _setup_styles(self):
        """Set modern styles"""
        self.setStyleSheet("""
            LLMQueueChatDialog {
                background-color: #121722;
            }
            QTextEdit#chatArea {
                background-color: #151B26;
                border: 1px solid #253043;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #E6E8EC;
            }
            QPlainTextEdit#inputArea {
                background-color: #141923;
                border: 2px solid #263041;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #E6E8EC;
            }
            QPlainTextEdit#inputArea:focus {
                border-color: #3FB7A6;
            }
            QPushButton#sendBtn {
                background-color: #3FB7A6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#sendBtn:hover {
                background-color: #5BC0B0;
            }
            QPushButton#sendBtn:pressed {
                background-color: #2FA191;
            }
            QPushButton#sendBtn:disabled {
                background-color: #3A465C;
                color: #7B8595;
            }
            QPushButton#settingsBtn {
                background-color: transparent;
                color: #9AA2AF;
                border: 1px solid #2A3342;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton#settingsBtn:hover {
                background-color: #1C2734;
                color: #E6E8EC;
            }
            QListWidget#historyList {
                background-color: #151B26;
                border: 1px solid #253043;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget#historyList::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget#historyList::item:hover {
                background-color: #1C2734;
            }
            QListWidget#historyList::item:selected {
                background-color: #3FB7A6;
            }
            QLineEdit#historyFilter {
                background-color: #141923;
                border: 1px solid #263041;
                border-radius: 6px;
                padding: 8px;
                color: #E6E8EC;
            }
            QLabel#statusLabel {
                color: #3FB7A6;
                font-size: 13px;
            }
            QLabel#hintLabel {
                color: #6C7686;
                font-size: 11px;
            }
        """)
    
    def _setup_ui(self):
        """Set up UI layout"""
        self._chat = QTextEdit()
        self._chat.setObjectName("chatArea")
        self._chat.setReadOnly(True)

        self._history_list = QListWidget()
        self._history_list.setObjectName("historyList")
        self._history_list.setMinimumWidth(220)
        self._history_list.itemDoubleClicked.connect(self._on_history_item_activated)

        self._history_filter = QLineEdit()
        self._history_filter.setObjectName("historyFilter")
        self._history_filter.setPlaceholderText("🔍 Filter history...")
        self._history_filter.textChanged.connect(self._apply_history_filter)

        # Use custom input box to support Enter to send
        self._input = ChatInputWidget()
        self._input.setObjectName("inputArea")
        self._input.setPlaceholderText("e.g.: Put slower tracks at the end; remove duplicates; clear queue; put similar tracks first...")
        self._input.setFixedHeight(80)
        self._input.submit_requested.connect(self._on_send)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("sendBtn")
        self._send_btn.clicked.connect(self._on_send)
        self._send_btn.setFixedSize(80, 80)

        self._settings_btn = QPushButton("⚙ LLM Settings")
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.clicked.connect(self._open_settings)

        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        
        self._hint = QLabel("Enter to Send · Ctrl+Enter for new line")
        self._hint.setObjectName("hintLabel")

        # Top toolbar
        top = QHBoxLayout()
        top.addWidget(self._settings_btn)
        top.addStretch()
        top.addWidget(self._status)

        # Bottom input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(12)
        input_layout.addWidget(self._input, 1)
        input_layout.addWidget(self._send_btn)
        
        bottom = QVBoxLayout()
        bottom.addWidget(self._hint)
        bottom.addLayout(input_layout)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addLayout(top)

        # Center content area
        center = QHBoxLayout()
        center.setSpacing(12)
        center.addWidget(self._chat, 3)

        history_box = QVBoxLayout()
        history_label = QLabel("📜 History (double-click to load)")
        history_label.setStyleSheet(f"color: {tokens.NEUTRAL_600}; font-size: {tokens.FONT_SIZE_XS}px; margin-bottom: 4px;")
        history_box.addWidget(history_label)
        history_box.addWidget(self._history_filter)
        history_box.addWidget(self._history_list, 1)
        center.addLayout(history_box, 1)

        layout.addLayout(center, 1)
        layout.addLayout(bottom)

    def _append_system(self, text: str) -> None:
        self._chat.append(f"[System] {text}")

    def _append_user(self, text: str) -> None:
        self._chat.append(f"[You] {text}")

    def _append_assistant(self, text: str) -> None:
        self._chat.append(f"[LLM] {text}")

    def _open_settings(self) -> None:
        dlg = LLMSettingsDialog(self._facade._config, self)
        dlg.exec()

    def _set_busy(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._settings_btn.setEnabled(not busy)
        self._status.setText("Processing..." if busy else "")

    def _make_snapshot(self) -> _QueueSnapshot:
        queue = self._facade.queue
        current = self._facade.current_track
        return _QueueSnapshot(queue=queue, current_track_id=(current.id if current else None))

    def _build_library_context(self) -> dict:
        try:
            genres = self._facade._library.get_top_genres(limit=30)
        except Exception:
            genres = []
        try:
            track_count = int(self._facade.get_track_count())
        except Exception:
            track_count = None

        return {
            "track_count": track_count,
            "has_genre_tags": bool(genres),
            "top_genres": genres,
        }

    def _on_send(self) -> None:
        if self._thread and self._thread.isRunning():
            return

        instruction = self._input.toPlainText().strip()
        if not instruction:
            return

        self._pending_instruction = instruction
        snapshot = self._make_snapshot()
        if not snapshot.queue:
            self._append_system("Current queue is empty, will try to fetch/generate queue from library according to your instruction.")

        self._append_user(instruction)
        self._input.clear()

        # Cache hit: Load history queue directly to avoid repeating LLM call
        try:
            cached = self._cache.load_cached_queue(instruction, self._facade._library) if self._cache.enabled() else None
        except Exception:
            cached = None

        if cached is not None:
            queue, start_index, entry = cached
            try:
                self._facade.set_queue(queue, start_index if queue else -1)
                self._append_assistant(f"Cache hit: {entry.label} ({len(queue)} tracks, {entry.created_at})")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            finally:
                self._pending_instruction = None
            self._refresh_history()
            return

        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = _SuggestWorker(
            self._facade._config, instruction, snapshot, 
            self._build_library_context(), self._facade._library
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _cleanup_thread(self) -> None:
        if self._worker:
            self._worker.deleteLater()
        if self._thread:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None

    def closeEvent(self, event) -> None:
        """Safely stop worker thread when dialog closes"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            # Wait 5 seconds, not forced termination to avoid resource leaks
            self._thread.wait(5000)
        self._cleanup_thread()
        event.accept()

    def _on_worker_finished(self, result: Optional[_ResolvedResult], error: Optional[BaseException]) -> None:
        self._set_busy(False)

        if error:
            if isinstance(error, LLMQueueError):
                res = QMessageBox.question(
                    self,
                    "LLM call failed",
                    f"{error}\n\nDo you want to set up API Key now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if res == QMessageBox.StandardButton.Yes:
                    self._open_settings()
            else:
                QMessageBox.critical(self, "Error", str(error))
            return

        if not result:
            QMessageBox.critical(self, "Error", "No LLM result received")
            return

        try:
            if result.plan.clear_queue and hasattr(self._facade._player, "clear_queue"):
                self._facade._player.clear_queue()
            self._facade.set_queue(result.queue, result.start_index if result.queue else -1)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Save to query history (also as future cache source)
        try:
            instruction = result.plan.instruction or (self._pending_instruction or "")
            if instruction and result.queue:
                plan_json = json.dumps(asdict(result.plan), ensure_ascii=False)
                self._cache.save_history(
                    instruction=instruction,
                    track_ids=[t.id for t in result.queue if getattr(t, "id", None)],
                    start_index=result.start_index,
                    label=instruction,
                    plan_json=plan_json,
                )
        except Exception:
            pass
        finally:
            self._pending_instruction = None
            self._refresh_history()

        plan = result.plan
        if plan.clear_queue and plan.library_request is None and not plan.ordered_track_ids:
            self._append_assistant("Queue cleared.")
            return

        if plan.library_request is not None:
            mode = plan.library_request.mode
            q = plan.library_request.genre or plan.library_request.query or "(No condition specified)"
            self._append_assistant(plan.reason or f"Queue {('replaced' if mode=='replace' else 'appended')} from library: {q}")
            return

        self._append_assistant(plan.reason or "Queue changes applied.")

    def _refresh_history(self) -> None:
        self._history_list.clear()
        if not self._cache.enabled():
            item = QListWidgetItem("(Cache disabled)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._history_list.addItem(item)
            return

        try:
            entries = self._cache.list_history(limit=30)
        except Exception:
            entries = []

        if not entries:
            item = QListWidgetItem("(No entries)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._history_list.addItem(item)
            return

        for entry in entries:
            text = f"{entry.label} · {len(entry.track_ids)} tracks"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self._history_list.addItem(item)

        self._apply_history_filter(self._history_filter.text())

    def _apply_history_filter(self, text: str) -> None:
        needle = (text or "").strip().lower()
        for i in range(self._history_list.count()):
            item = self._history_list.item(i)
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            if entry_id is None:
                item.setHidden(False)
                continue
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_history_item_activated(self, item: QListWidgetItem) -> None:
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        if entry_id is None:
            return

        try:
            loaded = self._cache.load_entry_queue(int(entry_id), self._facade._library)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        if not loaded:
            QMessageBox.information(self, "Information", "This historical queue is no longer available (tracks may have been removed).")
            return

        queue, start_index = loaded
        try:
            self._facade.set_queue(queue, start_index if queue else -1)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._append_assistant(f"Loaded from history: {item.text()}")
