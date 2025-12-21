"""
Player Control Component

Contains play/pause, previous/next, progress bar, volume control, etc.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QSlider, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap

from services.player_service import PlayerService, PlayMode
from core.event_bus import EventBus
from app.events import EventType
from ui.styles.theme_manager import ThemeManager


class PlayerControls(QWidget):
    """
    Player Control Component

    Displays current track information and playback control buttons.
    """
    
    # Signals
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, parent=None):
        super().__init__(parent)
        self.player = player_service
        self.event_bus = EventBus()
        self._subscriptions: list = []  # Track event subscription IDs
        
        self.setObjectName("playerBar")
        self.setFixedHeight(100)
        
        self._setup_ui()
        self._connect_signals()
        self._start_position_timer()
    
    def _setup_ui(self):
        """Set up UI"""
        # Main layout: two vertical rows
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # First row: progress bar (spans entire width)
        self.progress_container = QWidget()
        self.progress_container.setFixedHeight(20) # Reserve some height for handle
        prog_layout = QHBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(0)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        
        prog_layout.addWidget(self.progress_slider)
        main_layout.addWidget(self.progress_container)
        
        # Second row: control panel
        self.control_panel = QWidget()
        control_layout = QHBoxLayout(self.control_panel)
        control_layout.setContentsMargins(24, 4, 24, 12)
        control_layout.setSpacing(24)
        
        # Left: track information
        self.track_info = self._create_track_info()
        control_layout.addWidget(self.track_info)

        # Middle: playback control buttons
        control_layout.addStretch(1)
        self.controls = self._create_button_controls()
        control_layout.addWidget(self.controls)
        control_layout.addStretch(1)

        # Right: volume and tools
        self.volume_control = self._create_volume_control()
        control_layout.addWidget(self.volume_control)
        
        main_layout.addWidget(self.control_panel)
    
    def _create_track_info(self) -> QWidget:
        """Create track information area"""
        widget = QWidget()
        widget.setFixedWidth(240)
        widget.setObjectName("trackInfo")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setStyleSheet(ThemeManager.get_cover_style())
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.cover_label)

        # Track text information
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("Not Playing")
        self.title_label.setStyleSheet(ThemeManager.get_track_title_style())
        # Limit text length, simple truncation
        self.title_label.setFixedWidth(160)

        self.artist_label = QLabel("Apple Music")
        self.artist_label.setObjectName("secondaryLabel")
        self.artist_label.setStyleSheet(ThemeManager.get_track_artist_style())
        self.artist_label.setFixedWidth(160)
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        layout.addLayout(info_layout)
        
        return widget
    
    def _create_button_controls(self) -> QWidget:
        """Create playback control button group (without progress bar)"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Previous button
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(ThemeManager.get_icon("previous"))
        self.prev_btn.setIconSize(QSize(24, 24))
        self.prev_btn.setObjectName("controlButton")
        self.prev_btn.setToolTip("Previous")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.prev_btn)

        # Play/Pause button (Hero Button)
        self.play_btn = QPushButton()
        self.play_btn.setIcon(ThemeManager.get_icon("play"))
        self.play_btn.setIconSize(QSize(32, 32))
        self.play_btn.setObjectName("PlayPauseButton")
        self.play_btn.setToolTip("Play")
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setStyleSheet(ThemeManager.get_primary_button_style())
        self.play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.play_btn)

        # Next button
        self.next_btn = QPushButton()
        self.next_btn.setIcon(ThemeManager.get_icon("next"))
        self.next_btn.setIconSize(QSize(24, 24))
        self.next_btn.setObjectName("controlButton")
        self.next_btn.setToolTip("Next")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.next_btn.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.next_btn)
        
        return widget
    
    def _create_volume_control(self) -> QWidget:
        """Create volume and auxiliary function area"""
        widget = QWidget()
        widget.setFixedWidth(200) # Slightly wider to accommodate time information
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Current time/total time (moved to right side display)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(ThemeManager.get_time_label_style())
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)

        # Shuffle button
        self.shuffle_btn = QPushButton()
        self.shuffle_btn.setIcon(ThemeManager.get_icon("shuffle"))
        self.shuffle_btn.setIconSize(QSize(20, 20))
        self.shuffle_btn.setObjectName("controlButton")
        self.shuffle_btn.setToolTip("Shuffle")
        self.shuffle_btn.setFixedSize(28, 28)
        self.shuffle_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.clicked.connect(self._on_shuffle_clicked)
        layout.addWidget(self.shuffle_btn)

        # Repeat button
        self.repeat_btn = QPushButton()
        self.repeat_btn.setIcon(ThemeManager.get_icon("repeat"))
        self.repeat_btn.setIconSize(QSize(20, 20))
        self.repeat_btn.setObjectName("controlButton")
        self.repeat_btn.setToolTip("Repeat")
        self.repeat_btn.setFixedSize(28, 28)
        self.repeat_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.repeat_btn.setCheckable(True)
        self.repeat_btn.clicked.connect(self._on_repeat_clicked)
        layout.addWidget(self.repeat_btn)
        
        # Volume button
        self.volume_btn = QPushButton()
        self.volume_btn.setIcon(ThemeManager.get_icon("volume_high"))
        self.volume_btn.setIconSize(QSize(20, 20))
        self.volume_btn.setObjectName("controlButton")
        self.volume_btn.setFixedSize(28, 28)
        self.volume_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.volume_btn.clicked.connect(self._on_mute_clicked)
        layout.addWidget(self.volume_btn)
        
        # Volume slider (Optional: could be a popup or mini-style like this)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(60)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.volume_slider)
        
        return widget
    
    def _connect_signals(self):
        """Connect event signals."""
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_PAUSED, self._on_track_paused)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_RESUMED, self._on_track_resumed)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_ENDED, self._on_track_ended)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.PLAYBACK_STOPPED, self._on_playback_stopped)
        )
    
    def cleanup(self):
        """Clean up event subscriptions (should be called before component destruction)."""
        for sub_id in self._subscriptions:
            self.event_bus.unsubscribe(sub_id)
        self._subscriptions.clear()
    
    def _start_position_timer(self):
        """Start position update timer."""
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(500)  # Update every 500ms
        self._slider_dragging = False
    
    def _update_position(self):
        """Update playback position and detect end of playback."""
        if self._slider_dragging:
            return
        
        # Detect if playback ended (thread-safe)
        if self.player.check_playback_ended():
            self._update_play_button()
            return
        
        if self.player.is_playing:
            state = self.player.state
            if state.duration_ms > 0:
                progress = int((state.position_ms / state.duration_ms) * 1000)
                self.progress_slider.setValue(progress)
                
                # Update time label "0:00 / 3:45"
                current_str = self._format_time(state.position_ms)
                total_str = self._format_time(state.duration_ms)
                self.time_label.setText(f"{current_str} / {total_str}")
    
    def _format_time(self, ms: int) -> str:
        """Format time in ms to MM:SS."""
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _on_play_clicked(self):
        """Handle play/pause button click."""
        self.player.toggle_play()
        self._update_play_button()
    
    def _on_prev_clicked(self):
        """Handle previous track button click."""
        self.player.previous_track()
        self.previous_clicked.emit()
    
    def _on_next_clicked(self):
        """Handle next track button click."""
        self.player.next_track()
        self.next_clicked.emit()
    
    def _on_shuffle_clicked(self):
        """Handle shuffle button click."""
        mode = self.player.get_play_mode()
        if mode == PlayMode.SHUFFLE:
            self.player.set_play_mode(PlayMode.SEQUENTIAL)
            self.shuffle_btn.setChecked(False)
        else:
            self.player.set_play_mode(PlayMode.SHUFFLE)
            self.shuffle_btn.setChecked(True)
    
    def _on_repeat_clicked(self):
        """Handle repeat button click."""
        mode = self.player.get_play_mode()
        if mode == PlayMode.REPEAT_ONE:
            self.player.set_play_mode(PlayMode.SEQUENTIAL)
            self.repeat_btn.setIcon(ThemeManager.get_icon("repeat"))
            self.repeat_btn.setChecked(False)
        elif mode == PlayMode.REPEAT_ALL:
            self.player.set_play_mode(PlayMode.REPEAT_ONE)
            self.repeat_btn.setIcon(ThemeManager.get_icon("repeat_1"))
            self.repeat_btn.setChecked(True)
        else:
            self.player.set_play_mode(PlayMode.REPEAT_ALL)
            self.repeat_btn.setChecked(True)
    
    def _on_slider_pressed(self):
        """Handle progress slider press."""
        self._slider_dragging = True
    
    def _on_slider_released(self):
        """Handle progress slider release."""
        self._slider_dragging = False
        state = self.player.state
        if state.duration_ms > 0:
            position = int((self.progress_slider.value() / 1000) * state.duration_ms)
            self.player.seek(position)
    
    def _on_volume_changed(self, value):
        """Handle volume slider value change."""
        volume = value / 100
        self.player.set_volume(volume)
        
        # Update volume icon
        if value == 0:
            self.volume_btn.setIcon(ThemeManager.get_icon("volume_mute"))
        elif value < 50:
            self.volume_btn.setIcon(ThemeManager.get_icon("volume_high"))
        else:
            self.volume_btn.setIcon(ThemeManager.get_icon("volume_high"))
    
    def _on_mute_clicked(self):
        """Handle mute button click."""
        if self.volume_slider.value() > 0:
            self._saved_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
        else:
            self.volume_slider.setValue(getattr(self, '_saved_volume', 80))
    
    def _on_track_started(self, track):
        """Handle track start event."""
        if track:
            self.title_label.setText(track.title)
            self.artist_label.setText(track.artist_name)
            # Update initial state of the time label
            total_str = self._format_time(track.duration_ms)
            self.time_label.setText(f"0:00 / {total_str}")
        self._update_play_button()
    
    def _on_track_paused(self, _=None):
        """Handle track pause event."""
        self._update_play_button()
    
    def _on_track_resumed(self, _=None):
        """Handle track resume event."""
        self._update_play_button()
    
    def _on_track_ended(self, _=None):
        """Handle track completion event."""
        self._update_play_button()

    def _on_playback_stopped(self, _=None):
        """Handle playback stop event."""
        self._update_play_button()
    
    def _update_play_button(self):
        """Update play button state and tooltip."""
        if self.player.is_playing:
            self.play_btn.setIcon(ThemeManager.get_icon("pause"))
            self.play_btn.setToolTip("Pause")
        else:
            self.play_btn.setIcon(ThemeManager.get_icon("play"))
            self.play_btn.setToolTip("Play")
