"""
Mini Player Window

Compact borderless playback control window that can be dragged to move.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QMouseEvent
from pathlib import Path

from services.player_service import PlayerService
from models.track import Track
from core.event_bus import EventBus
from app.events import EventType
from ui.resources.design_tokens import tokens


class MiniPlayer(QWidget):
    """
    Mini player window

    Compact playback control interface that can be dragged to move.

    Signals:
        expand_requested: Request to return to main window
    """
    
    expand_requested = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, parent=None):
        """
        Initialize mini player

        Args:
            player_service: Player service
            parent: Parent window
        """
        super().__init__(parent)
        self._player = player_service
        self._event_bus = EventBus()
        self._drag_position: QPoint = None
        
        self._setup_window()
        self._setup_ui()
        self._connect_events()
        self._update_display()
    
    def _setup_window(self):
        """Set up window properties"""
        self.setWindowTitle("Mini Player")
        self.setFixedSize(320, 80)

        # Borderless, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Rounded corner styles
        self.setStyleSheet("""
            MiniPlayer {
                background-color: #151B26;
                border-radius: 12px;
                border: 1px solid #253043;
            }
            QLabel {
                color: #E6E8EC;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #E6E8EC;
                font-size: 16px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #223044;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #1C2734;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #2A3342;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 8px;
                height: 8px;
                margin: -2px 0;
                background: #E6E8EC;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #3FB7A6;
                border-radius: 2px;
            }
        """)
    
    def _setup_ui(self):
        """Set up UI layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Album cover
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(60, 60)
        self.cover_label.setStyleSheet("""
            background-color: #1B2230;
            border-radius: 6px;
        """)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setText("🎵")
        layout.addWidget(self.cover_label)

        # Info area
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.title_label = QLabel("Not Playing")
        self.title_label.setStyleSheet(f"font-size: {tokens.FONT_SIZE_SM}px; font-weight: bold;")
        self.title_label.setMaximumWidth(140)
        info_layout.addWidget(self.title_label)
        
        self.artist_label = QLabel("-")
        self.artist_label.setStyleSheet(f"font-size: {tokens.FONT_SIZE_MINI}px; color: {tokens.NEUTRAL_500};")
        self.artist_label.setMaximumWidth(140)
        info_layout.addWidget(self.artist_label)
        
        # Progress bar
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setFixedWidth(140)
        self.progress_slider.sliderReleased.connect(self._on_seek)
        info_layout.addWidget(self.progress_slider)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(4)
        
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.clicked.connect(self._player.previous_track)
        controls_layout.addWidget(self.prev_btn)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.clicked.connect(self._player.toggle_play)
        controls_layout.addWidget(self.play_btn)
        
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.clicked.connect(self._player.next_track)
        controls_layout.addWidget(self.next_btn)
        
        # Expand button
        self.expand_btn = QPushButton("⬜")
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setToolTip("Back to Main Window")
        self.expand_btn.clicked.connect(self.expand_requested.emit)
        controls_layout.addWidget(self.expand_btn)
        
        layout.addLayout(controls_layout)
    
    def _connect_events(self):
        """Connect events"""
        self._event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
        self._event_bus.subscribe(EventType.TRACK_PAUSED, self._on_playback_paused)
        self._event_bus.subscribe(EventType.TRACK_RESUMED, self._on_playback_resumed)
        self._event_bus.subscribe(EventType.POSITION_CHANGED, self._on_position_changed)
    
    def _update_display(self):
        """Update display"""
        track = self._player.current_track
        if track:
            self.title_label.setText(track.title or "Unknown Track")
            self.artist_label.setText(track.artist_name or "Unknown Artist")
            self._update_play_button(self._player.is_playing)
        else:
            self.title_label.setText("Not Playing")
            self.artist_label.setText("-")
            self.play_btn.setText("▶")
    
    def _on_track_started(self, track: Track):
        """Track started playing"""
        if track:
            self.title_label.setText(track.title or "Unknown Track")
            self.artist_label.setText(track.artist_name or "Unknown Artist")
        self._update_play_button(True)

    def _on_playback_paused(self, data=None):
        """Playback paused"""
        self._update_play_button(False)

    def _on_playback_resumed(self, data=None):
        """Playback resumed"""
        self._update_play_button(True)

    def _on_position_changed(self, data):
        """Playback position changed"""
        if data and 'position' in data and 'duration' in data:
            duration = data['duration']
            if duration > 0:
                position = data['position']
                self.progress_slider.blockSignals(True)
                self.progress_slider.setValue(int(position / duration * 1000))
                self.progress_slider.blockSignals(False)
    
    def _on_seek(self):
        """Progress bar dragged"""
        if self._player.current_track:
            duration = self._player.current_track.duration_ms
            position = int(self.progress_slider.value() / 1000 * duration)
            self._player.seek(position)

    def _update_play_button(self, is_playing: bool):
        """Update play button state"""
        self.play_btn.setText("⏸" if is_playing else "▶")

    # Drag to move support
    def mousePressEvent(self, event: QMouseEvent):
        """Mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Mouse move"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Mouse release"""
        self._drag_position = None
