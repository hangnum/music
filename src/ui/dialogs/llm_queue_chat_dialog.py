from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional
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
from services.config_service import ConfigService
from services.llm_queue_cache_service import LLMQueueCacheService
from services.llm_queue_service import LLMQueueError, LLMQueueService, QueueReorderPlan
from services.library_service import LibraryService
from services.player_service import PlayerService

from ui.dialogs.llm_settings_dialog import LLMSettingsDialog


class ChatInputWidget(QPlainTextEdit):
    """支持回车发送的输入框"""
    
    submit_requested = pyqtSignal()
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Enter 发送，Ctrl+Enter/Shift+Enter 换行
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            modifiers = event.modifiers()
            if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                # 插入换行
                super().keyPressEvent(event)
            else:
                # 发送
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
        config: ConfigService,
        instruction: str,
        snapshot: _QueueSnapshot,
        library_context: dict,
        library: LibraryService,
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
    def __init__(self, player: PlayerService, library: LibraryService, config: ConfigService, parent=None):
        super().__init__(parent)
        self._player = player
        self._library = library
        self._config = config
        self._cache = LLMQueueCacheService(config=self._config)
        self._pending_instruction: Optional[str] = None

        self.setWindowTitle("队列助手（LLM）")
        self.setMinimumSize(780, 580)
        
        self._setup_styles()
        self._setup_ui()

        self._thread: Optional[QThread] = None
        self._worker: Optional[_SuggestWorker] = None

        self._append_system("你可以用自然语言描述想要的队列操作，我会调用 LLM 给出重排计划并应用到当前队列。")
        self._refresh_history()
    
    def _setup_styles(self):
        """设置现代化样式"""
        self.setStyleSheet("""
            LLMQueueChatDialog {
                background-color: #1a1a1a;
            }
            QTextEdit#chatArea {
                background-color: #242424;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #e0e0e0;
            }
            QPlainTextEdit#inputArea {
                background-color: #2a2a2a;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #ffffff;
            }
            QPlainTextEdit#inputArea:focus {
                border-color: #1DB954;
            }
            QPushButton#sendBtn {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#sendBtn:hover {
                background-color: #1ed760;
            }
            QPushButton#sendBtn:pressed {
                background-color: #169c46;
            }
            QPushButton#sendBtn:disabled {
                background-color: #555;
                color: #888;
            }
            QPushButton#settingsBtn {
                background-color: transparent;
                color: #888;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton#settingsBtn:hover {
                background-color: #333;
                color: #fff;
            }
            QListWidget#historyList {
                background-color: #242424;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget#historyList::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget#historyList::item:hover {
                background-color: #333;
            }
            QListWidget#historyList::item:selected {
                background-color: #1DB954;
            }
            QLineEdit#historyFilter {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px;
                color: #e0e0e0;
            }
            QLabel#statusLabel {
                color: #1DB954;
                font-size: 13px;
            }
            QLabel#hintLabel {
                color: #666;
                font-size: 11px;
            }
        """)
    
    def _setup_ui(self):
        """设置 UI 布局"""
        self._chat = QTextEdit()
        self._chat.setObjectName("chatArea")
        self._chat.setReadOnly(True)

        self._history_list = QListWidget()
        self._history_list.setObjectName("historyList")
        self._history_list.setMinimumWidth(220)
        self._history_list.itemDoubleClicked.connect(self._on_history_item_activated)

        self._history_filter = QLineEdit()
        self._history_filter.setObjectName("historyFilter")
        self._history_filter.setPlaceholderText("🔍 过滤历史…")
        self._history_filter.textChanged.connect(self._apply_history_filter)

        # 使用自定义输入框支持回车发送
        self._input = ChatInputWidget()
        self._input.setObjectName("inputArea")
        self._input.setPlaceholderText("例如：把节奏慢的放后面；去掉重复的；清空队列；把当前类似风格的放前面…")
        self._input.setFixedHeight(80)
        self._input.submit_requested.connect(self._on_send)

        self._send_btn = QPushButton("发送")
        self._send_btn.setObjectName("sendBtn")
        self._send_btn.clicked.connect(self._on_send)
        self._send_btn.setFixedSize(80, 80)

        self._settings_btn = QPushButton("⚙ LLM 设置")
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.clicked.connect(self._open_settings)

        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        
        self._hint = QLabel("Enter 发送 · Ctrl+Enter 换行")
        self._hint.setObjectName("hintLabel")

        # 顶部工具栏
        top = QHBoxLayout()
        top.addWidget(self._settings_btn)
        top.addStretch()
        top.addWidget(self._status)

        # 底部输入区
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

        # 中部内容区
        center = QHBoxLayout()
        center.setSpacing(12)
        center.addWidget(self._chat, 3)

        history_box = QVBoxLayout()
        history_label = QLabel("📜 历史（双击加载）")
        history_label.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 4px;")
        history_box.addWidget(history_label)
        history_box.addWidget(self._history_filter)
        history_box.addWidget(self._history_list, 1)
        center.addLayout(history_box, 1)

        layout.addLayout(center, 1)
        layout.addLayout(bottom)

    def _append_system(self, text: str) -> None:
        self._chat.append(f"[系统] {text}")

    def _append_user(self, text: str) -> None:
        self._chat.append(f"[你] {text}")

    def _append_assistant(self, text: str) -> None:
        self._chat.append(f"[LLM] {text}")

    def _open_settings(self) -> None:
        dlg = LLMSettingsDialog(self._config, self)
        dlg.exec()

    def _set_busy(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._settings_btn.setEnabled(not busy)
        self._status.setText("处理中…" if busy else "")

    def _make_snapshot(self) -> _QueueSnapshot:
        queue = self._player.queue
        current = self._player.current_track
        return _QueueSnapshot(queue=queue, current_track_id=(current.id if current else None))

    def _build_library_context(self) -> dict:
        try:
            genres = self._library.get_top_genres(limit=30)
        except Exception:
            genres = []
        try:
            track_count = int(self._library.get_track_count())
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
            self._append_system("当前队列为空，将尝试按你的指令从音乐库调取/生成队列。")

        self._append_user(instruction)
        self._input.clear()

        # 缓存命中：直接加载历史队列，避免重复调用 LLM
        try:
            cached = self._cache.load_cached_queue(instruction, self._library) if self._cache.enabled() else None
        except Exception:
            cached = None

        if cached is not None:
            queue, start_index, entry = cached
            try:
                self._player.set_queue(queue, start_index if queue else -1)
                self._append_assistant(f"命中缓存：{entry.label}（{len(queue)}首，{entry.created_at}）")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))
                return
            finally:
                self._pending_instruction = None
            self._refresh_history()
            return

        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = _SuggestWorker(self._config, instruction, snapshot, self._build_library_context(), self._library)
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
        """对话框关闭时安全停止工作线程"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            # 等待5秒，不强制终止以避免资源泄漏
            self._thread.wait(5000)
        self._cleanup_thread()
        event.accept()

    def _on_worker_finished(self, result: Optional[_ResolvedResult], error: Optional[BaseException]) -> None:
        self._set_busy(False)

        if error:
            if isinstance(error, LLMQueueError):
                res = QMessageBox.question(
                    self,
                    "LLM 调用失败",
                    f"{error}\n\n是否现在去设置 API Key？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if res == QMessageBox.StandardButton.Yes:
                    self._open_settings()
            else:
                QMessageBox.critical(self, "错误", str(error))
            return

        if not result:
            QMessageBox.critical(self, "错误", "未获取到 LLM 结果")
            return

        try:
            if result.plan.clear_queue and hasattr(self._player, "clear_queue"):
                self._player.clear_queue()
            self._player.set_queue(result.queue, result.start_index if result.queue else -1)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        # 保存到查询历史（也作为后续缓存来源）
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
            self._append_assistant("已清空队列。")
            return

        if plan.library_request is not None:
            mode = plan.library_request.mode
            q = plan.library_request.genre or plan.library_request.query or "（未指定条件）"
            self._append_assistant(plan.reason or f"已从音乐库{('替换' if mode=='replace' else '追加')}队列：{q}")
            return

        self._append_assistant(plan.reason or "已应用队列变更。")

    def _refresh_history(self) -> None:
        self._history_list.clear()
        if not self._cache.enabled():
            item = QListWidgetItem("（缓存已关闭）")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._history_list.addItem(item)
            return

        try:
            entries = self._cache.list_history(limit=30)
        except Exception:
            entries = []

        if not entries:
            item = QListWidgetItem("（暂无）")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._history_list.addItem(item)
            return

        for entry in entries:
            text = f"{entry.label} · {len(entry.track_ids)}首"
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
            loaded = self._cache.load_entry_queue(int(entry_id), self._library)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        if not loaded:
            QMessageBox.information(self, "提示", "该历史队列已不可用（曲目可能已被移除）。")
            return

        queue, start_index = loaded
        try:
            self._player.set_queue(queue, start_index if queue else -1)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        self._append_assistant(f"已从历史加载：{item.text()}")
