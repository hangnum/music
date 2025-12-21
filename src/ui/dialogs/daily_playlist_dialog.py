"""
Daily Playlist Dialog

Used for generating today's playlist based on tags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.track import Track
from services.daily_playlist_service import DailyPlaylistResult, DailyPlaylistService
from ui.resources.design_tokens import tokens

if TYPE_CHECKING:
    from services.music_app_facade import MusicAppFacade


class _GenerateWorker(QObject):
    """Background worker thread for generating playlist"""
    
    finished = pyqtSignal(object, object)  # result, error
    
    def __init__(
        self,
        service: DailyPlaylistService,
        tags: List[str],
        limit: int,
    ):
        super().__init__()
        self._service = service
        self._tags = tags
        self._limit = limit
    
    def run(self) -> None:
        try:
            result = self._service.generate(self._tags, limit=self._limit)
            self.finished.emit(result, None)
        except Exception as e:
            self.finished.emit(None, e)


class DailyPlaylistDialog(QDialog):
    """
    Daily Playlist Dialog

    Allows users to select tags or enter descriptions to generate today's playlist.
    """
    
    playlist_generated = pyqtSignal(list)  # List[Track]
    
    def __init__(
        self,
        facade: "MusicAppFacade",
        parent=None,
    ):
        """Initialize daily playlist dialog

        Args:
            facade: Application facade providing access to all services
            parent: Parent component
        """
        super().__init__(parent)
        
        self._facade = facade
        
        self._result: Optional[DailyPlaylistResult] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[_GenerateWorker] = None
        
        self.setWindowTitle("Daily Playlist")
        self.setMinimumSize(700, 600)
        
        self._setup_styles()
        self._setup_ui()
        self._load_tags()
    
    def _setup_styles(self):
        """Set up modern styles using DesignTokens"""
        self.setStyleSheet(f"""
            DailyPlaylistDialog {{
                background-color: {tokens.NEUTRAL_900};
            }}
            QGroupBox {{
                color: {tokens.NEUTRAL_200};
                font-size: {tokens.FONT_SIZE_BASE}px;
                font-weight: bold;
                border: 1px solid {tokens.NEUTRAL_700};
                border-radius: {tokens.RADIUS_MD}px;
                margin-top: {tokens.SPACING_3}px;
                padding-top: {tokens.SPACING_3}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {tokens.SPACING_3}px;
                padding: 0 {tokens.SPACING_2}px;
            }}
            QLabel {{
                color: {tokens.NEUTRAL_500};
            }}
            QLabel#titleLabel {{
                color: {tokens.NEUTRAL_200};
                font-size: {tokens.FONT_SIZE_2XL}px;
                font-weight: bold;
            }}
            QLabel#subtitleLabel {{
                color: {tokens.NEUTRAL_300};
                font-size: {tokens.FONT_SIZE_SM}px;
            }}
            QLabel#summaryLabel {{
                color: {tokens.PRIMARY_500};
                font-size: {tokens.FONT_SIZE_SM}px;
            }}
            QLineEdit {{
                background-color: {tokens.NEUTRAL_800};
                border: 1px solid {tokens.NEUTRAL_600};
                border-radius: {tokens.RADIUS_SM}px;
                padding: 10px;
                color: {tokens.NEUTRAL_200};
                font-size: {tokens.FONT_SIZE_BASE}px;
            }}
            QLineEdit:focus {{
                border-color: {tokens.PRIMARY_500};
            }}
            QSpinBox {{
                background-color: {tokens.NEUTRAL_800};
                border: 1px solid {tokens.NEUTRAL_600};
                border-radius: {tokens.RADIUS_SM}px;
                padding: {tokens.SPACING_2}px;
                color: {tokens.NEUTRAL_200};
            }}
            QCheckBox {{
                color: {tokens.NEUTRAL_500};
                spacing: {tokens.SPACING_2}px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {tokens.RADIUS_SM}px;
                border: 1px solid {tokens.NEUTRAL_700};
                background-color: {tokens.NEUTRAL_750};
            }}
            QCheckBox::indicator:checked {{
                background-color: {tokens.PRIMARY_500};
                border-color: {tokens.PRIMARY_500};
            }}
            QCheckBox:hover {{
                color: {tokens.NEUTRAL_200};
            }}
            QPushButton#generateBtn {{
                background-color: {tokens.PRIMARY_500};
                color: {tokens.NEUTRAL_50};
                border: none;
                border-radius: {tokens.RADIUS_MD}px;
                padding: 14px 32px;
                font-size: {tokens.FONT_SIZE_LG}px;
                font-weight: bold;
            }}
            QPushButton#generateBtn:hover {{
                background-color: {tokens.PRIMARY_600};
            }}
            QPushButton#generateBtn:pressed {{
                background-color: {tokens.PRIMARY_700};
            }}
            QPushButton#generateBtn:disabled {{
                background-color: {tokens.NEUTRAL_700};
                color: {tokens.NEUTRAL_300};
            }}
            QPushButton#actionBtn {{
                background-color: {tokens.NEUTRAL_750};
                color: {tokens.NEUTRAL_200};
                border: 1px solid {tokens.NEUTRAL_700};
                border-radius: {tokens.RADIUS_SM}px;
                padding: 10px 20px;
                font-size: {tokens.FONT_SIZE_SM}px;
            }}
            QPushButton#actionBtn:hover {{
                background-color: {tokens.NEUTRAL_600};
            }}
            QPushButton#actionBtn:disabled {{
                color: {tokens.NEUTRAL_300};
            }}
            QListWidget {{
                background-color: {tokens.NEUTRAL_850};
                border: 1px solid {tokens.NEUTRAL_700};
                border-radius: {tokens.RADIUS_MD}px;
                padding: {tokens.SPACING_1}px;
            }}
            QListWidget::item {{
                padding: {tokens.SPACING_2}px {tokens.SPACING_3}px;
                border-radius: {tokens.RADIUS_SM}px;
                color: {tokens.NEUTRAL_200};
            }}
            QListWidget::item:hover {{
                background-color: {tokens.NEUTRAL_750};
            }}
            QListWidget::item:selected {{
                background-color: {tokens.PRIMARY_500};
            }}
            QProgressBar {{
                border: none;
                background-color: {tokens.NEUTRAL_750};
                border-radius: {tokens.RADIUS_SM}px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {tokens.PRIMARY_500};
                border-radius: {tokens.RADIUS_SM}px;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
    
    def _setup_ui(self):
        """Set up UI layout"""
        layout = QVBoxLayout(self)
        layout.setSpacing(tokens.SPACING_4)
        layout.setContentsMargins(tokens.SPACING_6, tokens.SPACING_6, 
                                   tokens.SPACING_6, tokens.SPACING_6)
        
        # Title area
        title = QLabel("🎵 What do you want to listen to today?")
        title.setObjectName("titleLabel")

        subtitle = QLabel("Select tags or enter a description to generate your personalized daily playlist")
        subtitle.setObjectName("subtitleLabel")
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(tokens.SPACING_2)
        
        # Tag input area
        tag_group = QGroupBox("Select Tags")
        tag_layout = QVBoxLayout(tag_group)
        
        # Search filter
        self._tag_filter = QLineEdit()
        self._tag_filter.setPlaceholderText("🔍 Search tags...")
        self._tag_filter.textChanged.connect(self._filter_tags)
        tag_layout.addWidget(self._tag_filter)

        # Tag scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(180)
        
        self._tag_container = QWidget()
        self._tag_grid = QGridLayout(self._tag_container)
        self._tag_grid.setSpacing(tokens.SPACING_2)
        scroll.setWidget(self._tag_container)
        
        tag_layout.addWidget(scroll)
        
        # Manual tag input
        manual_label = QLabel("Or manually enter tags (comma-separated):")
        manual_label.setStyleSheet(f"font-size: {tokens.FONT_SIZE_XS}px;")
        self._manual_tags = QLineEdit()
        self._manual_tags.setPlaceholderText("e.g.: Pop, Relax, Jay Chou")
        
        tag_layout.addWidget(manual_label)
        tag_layout.addWidget(self._manual_tags)
        
        layout.addWidget(tag_group)
        
        # Options area
        options_layout = QHBoxLayout()

        limit_label = QLabel("Playlist size:")
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(10, 100)
        self._limit_spin.setValue(50)
        self._limit_spin.setSuffix(" tracks")
        
        options_layout.addWidget(limit_label)
        options_layout.addWidget(self._limit_spin)
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        # Generate button
        self._generate_btn = QPushButton("✨ Generate Playlist")
        self._generate_btn.setObjectName("generateBtn")
        self._generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self._generate_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Progress bar
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setRange(0, 0)  # Indeterminate progress
        self._progress.hide()
        layout.addWidget(self._progress)
        
        # Result area
        self._result_group = QGroupBox("Generation Results")
        result_layout = QVBoxLayout(self._result_group)
        
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summaryLabel")
        result_layout.addWidget(self._summary_label)
        
        self._track_list = QListWidget()
        self._track_list.setMinimumHeight(150)
        result_layout.addWidget(self._track_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()

        self._play_btn = QPushButton("▶ Play Now")
        self._play_btn.setObjectName("actionBtn")
        self._play_btn.clicked.connect(self._on_play)
        self._play_btn.setEnabled(False)
        
        self._save_btn = QPushButton("💾 Save as Playlist")
        self._save_btn.setObjectName("actionBtn")
        self._save_btn.clicked.connect(self._on_save)
        self._save_btn.setEnabled(False)
        
        btn_layout.addWidget(self._play_btn)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addStretch()
        
        result_layout.addLayout(btn_layout)
        
        self._result_group.hide()
        layout.addWidget(self._result_group)
        
        # Store tag checkboxes
        self._tag_checkboxes: List[QCheckBox] = []

    def _load_tags(self):
        """Load all tags"""
        tags = self._facade.get_all_tags()

        # Clear old checkboxes
        for cb in self._tag_checkboxes:
            cb.deleteLater()
        self._tag_checkboxes.clear()
        
        # Create new checkboxes
        row, col = 0, 0
        cols_per_row = 4
        
        for tag in tags:
            cb = QCheckBox(tag.name)
            cb.setProperty("tag_name", tag.name)
            self._tag_grid.addWidget(cb, row, col)
            self._tag_checkboxes.append(cb)
            
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1
        
        if not tags:
            no_tag_label = QLabel("No tags available, please add tags to your music first")
            no_tag_label.setStyleSheet(f"color: {tokens.NEUTRAL_300};")
            self._tag_grid.addWidget(no_tag_label, 0, 0)
    
    def _filter_tags(self, text: str):
        """Filter tags"""
        needle = text.strip().lower()
        for cb in self._tag_checkboxes:
            tag_name = cb.property("tag_name") or ""
            cb.setVisible(not needle or needle in tag_name.lower())
    
    def _get_selected_tags(self) -> List[str]:
        """Get selected tags"""
        selected = []

        # Get from checkboxes
        for cb in self._tag_checkboxes:
            if cb.isChecked():
                tag_name = cb.property("tag_name")
                if tag_name:
                    selected.append(tag_name)
        
        # Get from manual input
        manual = self._manual_tags.text().strip()
        if manual:
            parts = [p.strip() for p in manual.replace("，", ",").split(",")]
            selected.extend([p for p in parts if p and p not in selected])
        
        return selected
    
    def _on_generate(self):
        """Generate playlist"""
        if self._thread and self._thread.isRunning():
            return
        
        tags = self._get_selected_tags()
        limit = self._limit_spin.value()
        
        if not tags:
            QMessageBox.warning(
                self,
                "Tip",
                "Please select at least one tag or enter a tag description"
            )
            return
        
        self._set_busy(True)
        
        # Use facade to generate playlist (execute in background thread)
        from services.daily_playlist_service import DailyPlaylistService
        from services.llm_providers import create_llm_provider
        
        # Create LLM Provider
        try:
            llm_provider = create_llm_provider(self._facade.config)
        except Exception:
            llm_provider = None
        
        # Create service
        service = DailyPlaylistService(
            tag_service=self._facade.tag_service,
            library_service=self._facade.library_service,
            llm_provider=llm_provider,
        )
        
        # Start background thread
        self._thread = QThread(self)
        self._worker = _GenerateWorker(service, tags, limit)
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_generate_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()
    
    def _set_busy(self, busy: bool):
        """Set busy state"""
        self._generate_btn.setEnabled(not busy)
        self._progress.setVisible(busy)
        if busy:
            self._result_group.hide()
    
    def _cleanup_thread(self):
        """Clean up thread"""
        if self._worker:
            self._worker.deleteLater()
        if self._thread:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
    
    def _on_generate_finished(
        self,
        result: Optional[DailyPlaylistResult],
        error: Optional[BaseException],
    ):
        """Generation complete callback"""
        self._set_busy(False)

        if error:
            QMessageBox.critical(self, "Generation Failed", str(error))
            return
        
        if not result or not result.tracks:
            QMessageBox.information(
                self,
                "Tip",
                "Could not find matching music. Please try other tags or ensure there are enough tagged tracks in your music library."
            )
            return
        
        self._result = result
        self._display_result(result)
    
    def _display_result(self, result: DailyPlaylistResult):
        """Display generation result"""
        self._summary_label.setText(f"Total {result.total} tracks · {result.summary}")

        self._track_list.clear()
        for i, track in enumerate(result.tracks, 1):
            artist = getattr(track, 'artist', '') or 'Unknown Artist'
            text = f"{i}. {track.title} - {artist}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, track.id)
            self._track_list.addItem(item)
        
        self._play_btn.setEnabled(True)
        self._save_btn.setEnabled(True)  # Always enable, facade provides playlist service
        self._result_group.show()

        # Emit signal
        self.playlist_generated.emit(result.tracks)
    
    def _on_play(self):
        """Play now"""
        if not self._result or not self._result.tracks:
            return

        try:
            self._facade.set_queue(self._result.tracks, 0)
            self._facade.play()
            self.accept()  # Close dialog
        except Exception as e:
            QMessageBox.critical(self, "Playback Failed", str(e))
    
    def _on_save(self):
        """Save as playlist"""
        if not self._result or not self._result.tracks:
            return

        # Generate playlist name
        from datetime import datetime
        name = f"Daily Playlist {datetime.now().strftime('%Y-%m-%d')}"
        
        try:
            playlist = self._facade.create_playlist(name)
            if playlist:
                for track in self._result.tracks:
                    self._facade.add_track_to_playlist(playlist.id, track.id)
                
                QMessageBox.information(
                    self,
                    "Save Successful",
                    f"Playlist \"{name}\" has been created with {len(self._result.tracks)} tracks"
                )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    def closeEvent(self, event):
        """Clean up on close"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)
        self._cleanup_thread()
        event.accept()
