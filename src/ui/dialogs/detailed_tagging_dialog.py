"""
精细标注对话框

对单首曲目进行详细的 AI 标注，显示网络搜索结果和 LLM 分析。
"""

from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING, Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QProgressBar,
    QScrollArea, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

if TYPE_CHECKING:
    from models.track import Track
    from services.llm_tagging_service import LLMTaggingService

logger = logging.getLogger(__name__)


class TaggingWorker(QThread):
    """后台标注工作线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        service: "LLMTaggingService",
        track: "Track",
        save_tags: bool,
    ):
        super().__init__()
        self._service = service
        self._track = track
        self._save_tags = save_tags
    
    def run(self):
        try:
            result = self._service.tag_single_track_detailed(
                track=self._track,
                save_tags=self._save_tags,
            )
            self.finished.emit(result)
        except Exception as e:
            logger.error("标注失败: %s", e)
            self.error.emit(str(e))


class DetailedTaggingDialog(QDialog):
    """
    精细标注对话框
    
    对单首曲目进行详细的 AI 标注分析。
    """
    
    # 标注完成信号
    tagging_completed = pyqtSignal(list)  # tags
    
    def __init__(
        self,
        track: "Track",
        llm_tagging_service: "LLMTaggingService",
        parent=None,
    ):
        super().__init__(parent)
        
        self._track = track
        self._service = llm_tagging_service
        self._worker: Optional[TaggingWorker] = None
        
        self.setWindowTitle("AI 精细标注")
        self.setMinimumSize(550, 500)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # === 曲目信息 ===
        info_group = QGroupBox("曲目信息")
        info_layout = QVBoxLayout(info_group)
        
        title = self._track.title or "(未知标题)"
        artist = getattr(self._track, "artist_name", "") or "(未知艺术家)"
        album = getattr(self._track, "album_name", "") or ""
        
        info_text = f"<b>{title}</b><br/>艺术家: {artist}"
        if album:
            info_text += f"<br/>专辑: {album}"
        
        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_group)
        
        # === 进度条 ===
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # 不确定进度
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)
        
        self._status_label = QLabel('点击"开始标注"进行 AI 精细分析')
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #6C7686;")
        layout.addWidget(self._status_label)
        
        # === 结果区域（可滚动）===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签结果
        self._tags_group = QGroupBox("生成的标签")
        tags_layout = QVBoxLayout(self._tags_group)
        self._tags_label = QLabel()
        self._tags_label.setWordWrap(True)
        self._tags_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        tags_layout.addWidget(self._tags_label)
        self._tags_group.setVisible(False)
        result_layout.addWidget(self._tags_group)
        
        # LLM 分析
        self._analysis_group = QGroupBox("AI 分析")
        analysis_layout = QVBoxLayout(self._analysis_group)
        self._analysis_text = QTextEdit()
        self._analysis_text.setReadOnly(True)
        self._analysis_text.setMaximumHeight(120)
        analysis_layout.addWidget(self._analysis_text)
        self._analysis_group.setVisible(False)
        result_layout.addWidget(self._analysis_group)
        
        # 搜索上下文
        self._context_group = QGroupBox("网络搜索结果")
        context_layout = QVBoxLayout(self._context_group)
        self._context_text = QTextEdit()
        self._context_text.setReadOnly(True)
        self._context_text.setMaximumHeight(150)
        context_layout.addWidget(self._context_text)
        self._context_group.setVisible(False)
        result_layout.addWidget(self._context_group)
        
        result_layout.addStretch()
        scroll.setWidget(result_widget)
        layout.addWidget(scroll, 1)
        
        # === 按钮 ===
        button_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("开始标注")
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setDefault(True)
        button_layout.addWidget(self._start_btn)
        
        button_layout.addStretch()
        
        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.close)
        button_layout.addWidget(self._close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_start(self):
        """开始标注"""
        self._start_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("正在搜索和分析...")
        self._status_label.setStyleSheet("color: #3FB7A6;")
        
        # 隐藏结果区域
        self._tags_group.setVisible(False)
        self._analysis_group.setVisible(False)
        self._context_group.setVisible(False)
        
        # 启动后台线程
        self._worker = TaggingWorker(
            service=self._service,
            track=self._track,
            save_tags=True,
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_finished(self, result: dict):
        """标注完成"""
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        
        tags = result.get("tags", [])
        analysis = result.get("analysis", "")
        context = result.get("search_context", "")
        
        if tags:
            self._status_label.setText(f"✓ 生成了 {len(tags)} 个标签")
            self._status_label.setStyleSheet("color: #3FB7A6;")
            
            # 显示标签（避免双重转义）
            tags_html = " ".join(
                f'<span style="background: #3FB7A6; color: white; '
                f'padding: 4px 10px; border-radius: 12px; margin: 2px;">{html.escape(html.unescape(t))}</span>'
                for t in tags
            )
            self._tags_label.setText(tags_html)
            self._tags_group.setVisible(True)
            
            self.tagging_completed.emit(tags)
        else:
            self._status_label.setText("未生成标签")
            self._status_label.setStyleSheet("color: #E46868;")
        
        # 显示分析
        if analysis:
            self._analysis_text.setPlainText(analysis)
            self._analysis_group.setVisible(True)
        
        # 显示搜索上下文
        if context:
            # 格式化显示
            formatted = context.replace(" | ", "\n\n---\n\n")
            self._context_text.setPlainText(formatted)
            self._context_group.setVisible(True)
    
    def _on_error(self, error: str):
        """标注失败"""
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        self._status_label.setText(f"✗ 标注失败: {error}")
        self._status_label.setStyleSheet("color: #E46868;")
    
    def closeEvent(self, event):
        """关闭时等待线程"""
        if self._worker and self._worker.isRunning():
            self._worker.wait(1000)
        event.accept()

