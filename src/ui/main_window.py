"""
Main Window

The application's main window, containing the layout of all UI components.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMainWindow, QMessageBox

logger = logging.getLogger(__name__)

from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog

from ui.main_window_menu import MainWindowMenuManager
from ui.main_window_navigator import MainWindowNavigator
from ui.main_window_library import MainWindowLibraryManager
from ui.main_window_system_tray import MainWindowSystemTrayManager
from ui.main_window_ui import MainWindowUIBuilder

if TYPE_CHECKING:
    from app.container import AppContainer


class MainWindow(QMainWindow):
    """
    Main Window
    
    The application's entry interface.
    
    Design principles:
    - MainWindow holds the AppContainer, but sub-components only receive facades.
    - Prohibit passing the container to sub-components.
    """
    
    def __init__(self, container: "AppContainer"):
        """Initialize main window
        
        Args:
            container: Application dependency container
        """
        super().__init__()
        
        self.setWindowTitle("Python Music Player")
        self.setMinimumSize(1000, 700)
        
        # === Get service references from container ===
        self._container = container
        self.config = container.config
        self.db = container.db
        self.event_bus = container.event_bus
        self.facade = container.facade
        
        # Internal service references (for scenarios requiring direct access)
        self.player = container._player
        self.library = container._library
        self.playlist_service = container._playlist_service
        self.queue_persistence = container._queue_persistence
        self.favorites_service = container._favorites_service
        
        # Load styles
        self._load_styles()
        
        # Initialize managers
        self.menu_manager = MainWindowMenuManager(self)
        self.navigator = MainWindowNavigator(self)
        self.library_manager = MainWindowLibraryManager(self)
        self.system_tray_manager = MainWindowSystemTrayManager(self)
        self.ui_builder = MainWindowUIBuilder(self)
        
        # Set up UI
        self.ui_builder.setup_ui()

        # Restore last playback queue (must trigger QUEUE_CHANGED after UI creation to refresh interface)
        try:
            self.queue_persistence.restore_last_queue(self.player, self.library)
        except Exception as e:
            logger.warning("Failed to restore playback queue: %s", e)
        
        # Restore window state
        self._restore_state()
    
    def _load_styles(self):
        """Load stylesheet"""
        from ui.styles.theme_manager import ThemeManager
        self.setStyleSheet(ThemeManager.get_global_stylesheet())
    
    def _restore_state(self):
        """Restore window state"""
        width = self.config.get("ui.window_width", 1200)
        height = self.config.get("ui.window_height", 800)
        self.resize(width, height)
    
    @property
    def llm_tagging_service(self):
        """Get LLM tagging service (public property for sub-component access)"""
        return self._container._llm_tagging_service
    
    # ===== Delegated methods to managers (for sidebar button signal connections) =====
    
    def _switch_page(self, index: int):
        """Switch page (delegated to navigator)"""
        self.navigator._switch_page(index)
    
    def _on_daily_playlist_clicked(self):
        """Click daily playlist navigation button (delegated to navigator)"""
        self.navigator._on_daily_playlist_clicked()
    
    def _open_favorites_playlist(self):
        """Open favorites (delegated to navigator)"""
        self.navigator._open_favorites_playlist()
    
    def _on_playlist_selected(self, playlist):
        """Playlist selected (delegated to navigator)"""
        self.navigator._on_playlist_selected(playlist)
    
    def _on_scan_clicked(self):
        """Scan media library (delegated to library manager)"""
        self.library_manager._on_scan_clicked()
    
    def _on_add_folder_clicked(self):
        """Add folder (delegated to library manager)"""
        self.library_manager._on_add_folder_clicked()
    
    def _update_status(self):
        """Update status information (delegated to library manager)"""
        self.library_manager._update_status()
    
    def _on_create_playlist(self):
        """Create new playlist (Delegated to menu manager? Actually no such option in menu, but shared by sidebar button)"""
        dialog = CreatePlaylistDialog(self)
        if dialog.exec() == CreatePlaylistDialog.DialogCode.Accepted:
            name = dialog.get_name()
            description = dialog.get_description()
            self.playlist_service.create(name, description)
            self.playlist_manager.refresh()
    
    def _open_llm_queue_assistant(self):
        """Open LLM queue assistant (delegated to menu manager)"""
        self.menu_manager._open_llm_queue_assistant()
    
    def _switch_to_mini_mode(self):
        """Switch to mini mode (delegated to navigator)"""
        self.navigator._switch_to_mini_mode()
    
    def _switch_from_mini_mode(self):
        """Return to main window from mini mode (delegated to navigator)"""
        self.navigator._switch_from_mini_mode()
    
    # ===== Window Event Overrides =====
    
    def closeEvent(self, event):
        """Close event - delegated to system tray manager"""
        self.system_tray_manager.handle_close_event(event)
    
    def activate_from_external(self):
        """Request window activation from external source (single instance support)"""
        self.system_tray_manager.activate_from_external()