"""
LLM Tagging Progress Dialog

Displays LLM batch tagging task progress, supports web search enhancement.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QCheckBox, QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

if TYPE_CHECKING:
    from services.llm_tagging_service import LLMTaggingService, TaggingJobStatus

logger = logging.getLogger(__name__)


class LLMTaggingProgressDialog(QDialog):
    """
    LLM Tagging Progress Dialog
    
    Used to start and monitor LLM batch tagging tasks.
    Supports web search enhancement feature.
    """
    
    # Task completion signal
    tagging_completed = pyqtSignal(dict)
    # Progress update signal
    progress_updated = pyqtSignal(int, int)
    
    def __init__(
        self,
        llm_tagging_service: "LLMTaggingService",
        parent=None,
    ):
        super().__init__(parent)
        
        self._service = llm_tagging_service
        self._current_job_id: Optional[str] = None
        self._poll_timer: Optional[QTimer] = None
        
        self.setWindowTitle("AI Tagging")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        # Connect signals
        self.progress_updated.connect(self._on_progress_updated)
        
        self._setup_ui()
        self._update_stats()
    
    def _setup_ui(self):
        """Set up UI layout"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # === Statistics ===
        stats_group = QGroupBox("Tagging Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self._stats_label = QLabel("Loading...")
        self._stats_label.setWordWrap(True)
        stats_layout.addWidget(self._stats_label)
        
        layout.addWidget(stats_group)
        
        # === Options ===
        options_group = QGroupBox("Tagging Options")
        options_layout = QVBoxLayout(options_group)
        
        self._web_search_checkbox = QCheckBox("Enable web search enhancement")
        self._web_search_checkbox.setToolTip(
            "Uses DuckDuckGo to search for additional track information,\n"
            "allowing for more accurate determination of genre and features.\n"
            "Note: This will increase tagging time."
        )
        options_layout.addWidget(self._web_search_checkbox)
        
        layout.addWidget(options_group)
        
        # === Progress ===
        progress_group = QGroupBox("Tagging Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)
        
        self._progress_label = QLabel("Ready")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self._progress_label)
        
        layout.addWidget(progress_group)
        
        # === Buttons ===
        button_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("Start Tagging")
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._start_btn.setDefault(True)
        button_layout.addWidget(self._start_btn)
        
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._stop_btn.setEnabled(False)
        button_layout.addWidget(self._stop_btn)
        
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.close)
        button_layout.addWidget(self._close_btn)
        
        layout.addLayout(button_layout)
    
    def _update_stats(self):
        """Update statistics."""
        try:
            stats = self._service.get_tagging_stats()
            tagged = stats.get("tagged_tracks", 0)
            total = stats.get("total_tracks", 0)
            llm_tags = stats.get("llm_tags", 0)
            untagged = total - tagged
            
            self._stats_label.setText(
                f"Total tracks: {total} | "
                f"Tagged: {tagged} | "
                f"To be tagged: {untagged}\n"
                f"AI-generated tags: {llm_tags}"
            )
            
            # If no tracks need tagging, disable the start button
            if untagged == 0:
                self._start_btn.setEnabled(False)
                self._start_btn.setText("All tagged")
            else:
                self._start_btn.setEnabled(True)
                self._start_btn.setText(f"Start Tagging ({untagged} tracks)")
                
        except Exception as e:
            logger.warning("Failed to fetch statistics: %s", e)
            self._stats_label.setText("Failed to fetch statistics")
    
    def _on_progress_updated(self, current: int, total: int):
        """Handle progress update signal"""
        if total > 0:
            progress_percent = int((current / total) * 100)
            self._progress_bar.setValue(progress_percent)
            self._progress_label.setText(
                f"{current} / {total} ({progress_percent}%)"
            )
    
    def _on_start_clicked(self):
        """Handle start button click."""
        use_web_search = self._web_search_checkbox.isChecked()
        
        try:
            # Progress callback (called in background thread, updates UI via signals)
            def progress_callback(current: int, total: int):
                # Send progress update via signal (thread-safe)
                self.progress_updated.emit(current, total)
            
            # Start task
            job_id = self._service.start_tagging_job(
                progress_callback=progress_callback,
                batch_size=30,  # Use smaller batch if search is enabled
                tags_per_track=5,
                use_web_search=use_web_search,
            )
            
            if not job_id:
                QMessageBox.information(
                    self, "Information",
                    "No tracks need tagging"
                )
                return
            
            self._current_job_id = job_id
            
            # Update UI state
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._web_search_checkbox.setEnabled(False)
            self._progress_label.setText("Tagging...")
            
            # Start polling timer (lower frequency, as backup)
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._poll_progress)
            self._poll_timer.start(5000)  # Update every 5 seconds (signal-based primary)
            
        except Exception as e:
            logger.error("Failed to start tagging task: %s", e)
            QMessageBox.critical(
                self, "Error",
                f"Failed to start tagging task: {e}"
            )
    
    def _on_stop_clicked(self):
        """Handle stop button click."""
        if self._current_job_id:
            self._service.stop_job(self._current_job_id)
            self._progress_label.setText("Stopping...")
            self._stop_btn.setEnabled(False)
    
    def _poll_progress(self):
        """Poll task progress"""
        if not self._current_job_id:
            return
        
        status = self._service.get_job_status(self._current_job_id)
        if not status:
            return
        
        # Update progress
        progress_percent = int(status.progress * 100)
        self._progress_bar.setValue(progress_percent)
        self._progress_label.setText(
            f"{status.processed_tracks} / {status.total_tracks} "
            f"({progress_percent}%)"
        )
        
        # Check if completed
        if status.status in ("completed", "failed", "stopped"):
            self._on_job_finished(status)
    
    def _on_job_finished(self, status: "TaggingJobStatus"):
        """Task completion handling"""
        # Stop timer
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None
        
        # Update UI
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._web_search_checkbox.setEnabled(True)
        
        # Display results
        if status.status == "completed":
            self._progress_label.setText("Tagging completed!")
            self._progress_bar.setValue(100)
            QMessageBox.information(
                self, "Complete",
                f"Tagging completed!\nProcessed {status.processed_tracks} tracks."
            )
        elif status.status == "stopped":
            self._progress_label.setText("Stopped")
            QMessageBox.information(
                self, "Stopped",
                f"Task stopped.\nProcessed {status.processed_tracks} / {status.total_tracks} tracks."
            )
        elif status.status == "failed":
            self._progress_label.setText("Tagging failed")
            error_msg = status.error_message or "Unknown error"
            QMessageBox.critical(
                self, "Failed",
                f"Tagging failed: {error_msg}"
            )
        
        # Update statistics
        self._update_stats()
        
        # Emit completion signal
        self.tagging_completed.emit({
            "job_id": status.job_id,
            "status": status.status,
            "processed": status.processed_tracks,
            "total": status.total_tracks,
        })
        
        self._current_job_id = None
    
    def closeEvent(self, event):
        """Handle close event."""
        # If task is running, ask to stop
        if self._current_job_id:
            reply = QMessageBox.question(
                self, "Confirm",
                "Tagging task is running. Are you sure you want to close?\nThe task will continue in the background.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # Stop timer
        if self._poll_timer:
            self._poll_timer.stop()
        
        event.accept()
