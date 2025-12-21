"""
Detailed Tagging Dialog

Performs detailed AI tagging for a single track, displaying web search results and LLM analysis.
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
    """Background tagging worker thread"""
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
            logger.error("Tagging failed: %s", e)
            self.error.emit(str(e))


class DetailedTaggingDialog(QDialog):
    """
    Detailed Tagging Dialog
    
    Performs detailed AI tagging analysis for a single track.
    """
    
    # Tagging completion signal
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
        
        self.setWindowTitle("AI Detailed Tagging")
        self.setMinimumSize(550, 500)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # === Track Information ===
        info_group = QGroupBox("Track Information")
        info_layout = QVBoxLayout(info_group)
        
        title = self._track.title or "(Unknown Title)"
        artist = getattr(self._track, "artist_name", "") or "(Unknown Artist)"
        album = getattr(self._track, "album_name", "") or ""
        
        info_text = f"<b>{title}</b><br/>Artist: {artist}"
        if album:
            info_text += f"<br/>Album: {album}"
        
        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_group)
        
        # === Progress bar ===
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # Indeterminate progress
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)
        
        self._status_label = QLabel('Click "Start Tagging" to perform detailed AI analysis')
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #6C7686;")
        layout.addWidget(self._status_label)
        
        # === Results area (scrollable)===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tag results
        self._tags_group = QGroupBox("Generated Tags")
        tags_layout = QVBoxLayout(self._tags_group)
        self._tags_label = QLabel()
        self._tags_label.setWordWrap(True)
        self._tags_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        tags_layout.addWidget(self._tags_label)
        self._tags_group.setVisible(False)
        result_layout.addWidget(self._tags_group)
        
        # AI Analysis
        self._analysis_group = QGroupBox("AI Analysis")
        analysis_layout = QVBoxLayout(self._analysis_group)
        self._analysis_text = QTextEdit()
        self._analysis_text.setReadOnly(True)
        self._analysis_text.setMaximumHeight(120)
        analysis_layout.addWidget(self._analysis_text)
        self._analysis_group.setVisible(False)
        result_layout.addWidget(self._analysis_group)
        
        # Search Context
        self._context_group = QGroupBox("Web Search Results")
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
        
        # === Buttons ===
        button_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("Start Tagging")
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setDefault(True)
        button_layout.addWidget(self._start_btn)
        
        button_layout.addStretch()
        
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.close)
        button_layout.addWidget(self._close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_start(self):
        """Start Tagging"""
        self._start_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._status_label.setText("Searching and analyzing...")
        self._status_label.setStyleSheet("color: #3FB7A6;")
        
        # Hide results area
        self._tags_group.setVisible(False)
        self._analysis_group.setVisible(False)
        self._context_group.setVisible(False)
        
        # Start background thread
        self._worker = TaggingWorker(
            service=self._service,
            track=self._track,
            save_tags=True,
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_finished(self, result: dict):
        """Tagging completed"""
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        
        tags = result.get("tags", [])
        analysis = result.get("analysis", "")
        context = result.get("search_context", "")
        
        if tags:
            self._status_label.setText(f"✓ Generated {len(tags)} tags")
            self._status_label.setStyleSheet("color: #3FB7A6;")
            
            # Display tags (unescape first to avoid double encoding)
            tags_html = " ".join(
                f'<span style="background: #3FB7A6; color: white; '
                f'padding: 4px 10px; border-radius: 12px; margin: 2px;">{html.escape(html.unescape(t))}</span>'
                for t in tags
            )
            self._tags_label.setText(tags_html)
            self._tags_group.setVisible(True)
            
            self.tagging_completed.emit(tags)
        else:
            self._status_label.setText("No tags generated")
            self._status_label.setStyleSheet("color: #E46868;")
        
        # Display analysis
        if analysis:
            self._analysis_text.setPlainText(analysis)
            self._analysis_group.setVisible(True)
        
        # Display Search Context
        if context:
            # Format display
            formatted = context.replace(" | ", "\n\n---\n\n")
            self._context_text.setPlainText(formatted)
            self._context_group.setVisible(True)
    
    def _on_error(self, error: str):
        """Tagging failed"""
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        self._status_label.setText(f"✗ Tagging failed: {error}")
        self._status_label.setStyleSheet("color: #E46868;")
    
    def closeEvent(self, event):
        """Wait for the thread when closing."""
        if self._worker and self._worker.isRunning():
            self._worker.wait(1000)
        event.accept()

