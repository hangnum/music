from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
)

from models.track import Track
from services.config_service import ConfigService
from services.llm_queue_service import LLMQueueError, LLMQueueService, QueueReorderPlan
from services.library_service import LibraryService
from services.player_service import PlayerService

from ui.dialogs.llm_settings_dialog import LLMSettingsDialog


class _NoopClient:
    def chat_completions(self, _messages):
        raise RuntimeError("noop")


@dataclass(frozen=True)
class _QueueSnapshot:
    queue: List[Track]
    current_track_id: Optional[str]


class _SuggestWorker(QObject):
    finished = pyqtSignal(object, object)  # plan, error

    def __init__(
        self,
        config: ConfigService,
        instruction: str,
        snapshot: _QueueSnapshot,
        library_context: dict,
    ):
        super().__init__()
        self._config = config
        self._instruction = instruction
        self._snapshot = snapshot
        self._library_context = library_context

    def run(self) -> None:
        try:
            svc = LLMQueueService(config=self._config)
            plan = svc.suggest_reorder(
                instruction=self._instruction,
                queue=self._snapshot.queue,
                current_track_id=self._snapshot.current_track_id,
                library_context=self._library_context,
            )
            self.finished.emit(plan, None)
        except Exception as e:
            self.finished.emit(None, e)


class LLMQueueChatDialog(QDialog):
    def __init__(self, player: PlayerService, library: LibraryService, config: ConfigService, parent=None):
        super().__init__(parent)
        self._player = player
        self._library = library
        self._config = config
        self._apply_service = LLMQueueService(config=self._config, client=_NoopClient())

        self.setWindowTitle("队列助手（LLM）")
        self.setMinimumSize(720, 520)

        self._chat = QTextEdit()
        self._chat.setReadOnly(True)

        self._input = QPlainTextEdit()
        self._input.setPlaceholderText("例如：把节奏慢的放后面；去掉重复的；清空队列；把当前类似风格的放前面…")
        self._input.setFixedHeight(90)

        self._send_btn = QPushButton("发送")
        self._send_btn.clicked.connect(self._on_send)

        self._settings_btn = QPushButton("LLM 设置…")
        self._settings_btn.clicked.connect(self._open_settings)

        self._status = QLabel("")

        top = QHBoxLayout()
        top.addWidget(self._settings_btn)
        top.addStretch()
        top.addWidget(self._status)

        bottom = QHBoxLayout()
        bottom.addWidget(self._input, 1)
        bottom.addWidget(self._send_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._chat, 1)
        layout.addLayout(bottom)

        self._thread: Optional[QThread] = None
        self._worker: Optional[_SuggestWorker] = None

        self._append_system("你可以用自然语言描述想要的队列操作，我会调用 LLM 给出重排计划并应用到当前队列。")

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

        snapshot = self._make_snapshot()
        if not snapshot.queue:
            self._append_system("当前队列为空，将尝试按你的指令从音乐库调取/生成队列。")

        self._append_user(instruction)
        self._input.clear()
        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = _SuggestWorker(self._config, instruction, snapshot, self._build_library_context())
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

    def _on_worker_finished(self, plan: Optional[QueueReorderPlan], error: Optional[BaseException]) -> None:
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

        if not plan:
            QMessageBox.critical(self, "错误", "未获取到 LLM 结果")
            return

        try:
            self._apply_service.apply_plan(self._player, plan, library=self._library)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        if plan.clear_queue and plan.library_request is None:
            self._append_assistant("已清空队列。")
            return

        if plan.library_request is not None:
            mode = plan.library_request.mode
            q = plan.library_request.genre or plan.library_request.query or "（未指定条件）"
            self._append_assistant(plan.reason or f"已从音乐库{('替换' if mode=='replace' else '追加')}队列：{q}")
            return

        self._append_assistant(plan.reason or "已应用队列变更。")
