"""
Main Window Navigator

Responsible for page switching, navigation state management, and mini mode.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt
from datetime import datetime

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from app.container import AppContainer


class MainWindowNavigator:
    """Main window navigator"""
    
    def __init__(self, main_window: "MainWindow"):
        """Initialize the navigator.
        
        Args:
            main_window: Main window instance, used to access services and properties.
        """
        self.main_window = main_window
        self._connect_navigation_events()
    
    def _connect_navigation_events(self):
        """Connect navigation-related events."""
        from app.events import EventType
        self.main_window.event_bus.subscribe(EventType.TRACK_STARTED,
                                              self._on_track_started)
    
    def _switch_page(self, index: int):
        """Switch current page."""
        self.main_window.content_stack.setCurrentIndex(index)
        
        # Update navigation button states
        self.main_window.nav_library.setChecked(index == 0)
        self.main_window.nav_queue.setChecked(index == 1)
        
        # Handle selected state for playlists and daily playlist
        is_daily = False
        is_favorites = False
        if index == 3:
            current_playlist = self.main_window.playlist_detail.playlist
            if current_playlist:
                today_str = datetime.now().strftime('%Y-%m-%d')
                if current_playlist.name == f"Daily Playlist {today_str}":
                    is_daily = True
                if self.main_window.favorites_service:
                    try:
                        is_favorites = current_playlist.id == self.main_window.favorites_service.get_playlist_id()
                    except Exception:
                        is_favorites = False
        
        self.main_window.nav_daily_playlist.setChecked(is_daily)
        self.main_window.nav_favorites.setChecked(is_favorites)
        self.main_window.nav_playlists.setChecked(index == 2 or (index == 3 and not is_daily and not is_favorites))
        
        # Refresh content based on page
        if index == 1:
            self.main_window.playlist_widget.update_list()
        elif index == 2:
            self.main_window.playlist_manager.refresh()
    
    def _switch_to_mini_mode(self):
        """Switch to mini player mode."""
        if not hasattr(self.main_window, '_mini_player') or self.main_window._mini_player is None:
            from ui.mini_player import MiniPlayer
            self.main_window._mini_player = MiniPlayer(self.main_window.player)
            self.main_window._mini_player.expand_requested.connect(self._switch_from_mini_mode)
        
        # Save main window position
        self.main_window._main_window_geometry = self.main_window.geometry()
        
        # Hide main window, show mini player
        self.main_window.hide()
        self.main_window._mini_player.show()
        
        # Place mini player at bottom-right of screen
        screen = QApplication.primaryScreen().geometry()
        self.main_window._mini_player.move(
            screen.width() - self.main_window._mini_player.width() - 20,
            screen.height() - self.main_window._mini_player.height() - 100
        )
    
    def _switch_from_mini_mode(self):
        """Return to main window from mini player mode."""
        if hasattr(self.main_window, '_mini_player') and self.main_window._mini_player:
            self.main_window._mini_player.hide()
        
        # Restore main window
        self.main_window.show()
        if hasattr(self.main_window, '_main_window_geometry'):
            self.main_window.setGeometry(self.main_window._main_window_geometry)
        self.main_window.activateWindow()
        self.main_window.raise_()
    
    def _on_daily_playlist_clicked(self):
        """Handle daily playlist navigation button click."""
        today_str = datetime.now().strftime('%Y-%m-%d')
        target_name = f"Daily Playlist {today_str}"
        
        # Find today's playlist
        playlists = self.main_window.playlist_service.get_all()
        today_playlist = next((p for p in playlists if p.name == target_name), None)
        
        if today_playlist:
            # If already exists, jump directly
            self._on_playlist_selected(today_playlist)
            self.main_window.nav_daily_playlist.setChecked(True)
        else:
            # If not exists, open generation dialog
            self.main_window.nav_daily_playlist.setChecked(False)
            self.main_window._open_daily_playlist()
    
    def _open_favorites_playlist(self):
        """Open 'My Favorites' playlist."""
        if not self.main_window.favorites_service:
            QMessageBox.information(
                self.main_window, "Information", "Favorites service is unavailable."
            )
            return

        playlist = self.main_window.favorites_service.get_or_create_playlist()
        self._on_playlist_selected(playlist)
        self.main_window.nav_favorites.setChecked(True)
    
    def _on_playlist_selected(self, playlist):
        """Handle playlist selection."""
        self.main_window.playlist_detail.set_playlist(playlist)
        self._switch_page(3)
    
    def _on_track_started(self, track):
        """Handle track start event."""
        if track:
            self.main_window.setWindowTitle(f"{track.title} - Python Music Player")