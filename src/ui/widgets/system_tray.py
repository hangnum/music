"""
System Tray Component

Implements system tray icon, menu, and notification functionality, completely decoupled from the main window.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject
from pathlib import Path

from services.player_service import PlayerService
from app.events import EventType


class SystemTray(QObject):
    """
    System tray component

    Provides tray icon, menu, and notification functionality, decoupled from the main window.

    Signals:
        show_window_requested: Request to show main window
        exit_requested: Request to exit application
    """
    
    show_window_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, event_bus, parent=None):
        """
        Initialize system tray

        Args:
            player_service: Player service
            event_bus: Event bus
            parent: Parent object
        """
        super().__init__(parent)
        self._player = player_service
        self._event_bus = event_bus
        self._show_notifications = True
        
        self._setup_tray()
        self._connect_events()
    
    def _setup_tray(self):
        """Set up tray icon and menu"""
        self._tray = QSystemTrayIcon(self.parent())
        
        # Set icon
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "app_icon.svg"
        if icon_path.exists():
            self._tray.setIcon(QIcon(str(icon_path)))
        else:
            # Use default application icon
            from PyQt6.QtWidgets import QApplication
            self._tray.setIcon(QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_MediaPlay
            ))
        
        self._tray.setToolTip("Python Music Player")

        # Create menu
        self._menu = QMenu()
        self._create_menu()
        self._tray.setContextMenu(self._menu)

        # Double-click event
        self._tray.activated.connect(self._on_tray_activated)
    
    def _create_menu(self):
        """Create tray menu"""
        # Show main window
        self._show_action = QAction("Show Main Window", self._menu)
        self._show_action.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(self._show_action)

        self._menu.addSeparator()

        # Playback controls
        self._play_action = QAction("▶ Play", self._menu)
        self._play_action.triggered.connect(self._on_play_clicked)
        self._menu.addAction(self._play_action)

        self._prev_action = QAction("⏮ Previous", self._menu)
        self._prev_action.triggered.connect(self._player.previous_track)
        self._menu.addAction(self._prev_action)

        self._next_action = QAction("⏭ Next", self._menu)
        self._next_action.triggered.connect(self._player.next_track)
        self._menu.addAction(self._next_action)

        self._menu.addSeparator()

        # Exit
        self._exit_action = QAction("Exit", self._menu)
        self._exit_action.triggered.connect(self.exit_requested.emit)
        self._menu.addAction(self._exit_action)
    
    def _connect_events(self):
        """Connect events"""
        self._event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
        self._event_bus.subscribe(EventType.TRACK_PAUSED, self._on_playback_paused)
        self._event_bus.subscribe(EventType.TRACK_RESUMED, self._on_playback_resumed)
    
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Tray icon activated"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()
    
    def _on_play_clicked(self):
        """Play button clicked"""
        self._player.toggle_play()
    
    def _on_track_started(self, track):
        """Track started playing"""
        self._update_play_action(is_playing=True)

        if self._show_notifications and track:
            title = track.title or "Unknown Track"
            artist = track.artist_name or "Unknown Artist"
            self._tray.showMessage(
                "Now Playing",
                f"{title}\n{artist}",
                QSystemTrayIcon.MessageIcon.Information,
                2000  # 2 seconds
            )
    
    def _on_playback_paused(self, data=None):
        """Playback paused"""
        self._update_play_action(is_playing=False)

    def _on_playback_resumed(self, data=None):
        """Playback resumed"""
        self._update_play_action(is_playing=True)

    def _update_play_action(self, is_playing: bool):
        """Update play button state"""
        if is_playing:
            self._play_action.setText("⏸ Pause")
        else:
            self._play_action.setText("▶ Play")

    def show(self):
        """Show tray icon"""
        self._tray.show()

    def hide(self):
        """Hide tray icon"""
        self._tray.hide()

    def is_visible(self) -> bool:
        """Is tray visible"""
        return self._tray.isVisible()

    def set_show_notifications(self, enabled: bool):
        """Set whether to show notifications"""
        self._show_notifications = enabled

    @property
    def tray_icon(self) -> QSystemTrayIcon:
        """Get tray icon object"""
        return self._tray
