"""
Main Window System Tray Manager

Responsible for system tray management and window display control.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from app.container import AppContainer


class MainWindowSystemTrayManager:
    """Main window system tray manager"""
    
    def __init__(self, main_window: "MainWindow"):
        """Initialize the system tray manager.
        
        Args:
            main_window: Main window instance, used to access services and properties.
        """
        self.main_window = main_window
        self._setup_system_tray()
    
    def _setup_system_tray(self):
        """Initialize the system tray."""
        from ui.widgets.system_tray import SystemTray
        self._system_tray = SystemTray(self.main_window.player, self.main_window.event_bus, self.main_window)
        self._system_tray.show_window_requested.connect(self._show_from_tray)
        self._system_tray.exit_requested.connect(self._exit_application)
        
        # Show tray icon
        self._system_tray.show()
        
        # Read notification settings
        show_notifications = self.main_window.config.get("ui.show_tray_notifications", True)
        self._system_tray.set_show_notifications(show_notifications)
    
    def _show_from_tray(self):
        """Display the window from the tray."""
        self.main_window.show()
        self.main_window.activateWindow()
        self.main_window.raise_()
    
    def _exit_application(self):
        """Exit the application from the tray menu."""
        self._do_cleanup_and_exit()
        QApplication.quit()
    
    def handle_close_event(self, event):
        """Handle close event - hide to tray instead of exiting."""
        # Check if window should minimize to tray
        minimize_to_tray = self.main_window.config.get("ui.minimize_to_tray", True)
        
        if minimize_to_tray and self._system_tray.is_visible():
            # Hide to tray
            event.ignore()
            self.main_window.hide()
        else:
            # Actually exit
            self._do_cleanup_and_exit(event)
    
    def _do_cleanup_and_exit(self, event=None):
        """Clean up resources and exit."""
        # Save window dimensions
        self.main_window.config.set("ui.window_width", self.main_window.width())
        self.main_window.config.set("ui.window_height", self.main_window.height())
        if hasattr(self.main_window, 'splitter'):
             self.main_window.config.set("ui.sidebar_width", self.main_window.splitter.sizes()[0])
        self.main_window.config.save()

        try:
            self.main_window.queue_persistence.persist_from_player()
            self.main_window.queue_persistence.shutdown()
        except Exception as e:
            logger.warning("Failed to save playback queue: %s", e)
        
        # Hide the tray icon
        self._system_tray.hide()
        
        # Wait for the scan thread to complete
        self.main_window.library.join_scan_thread()
        
        # Cleanup resources
        self.main_window.player.cleanup()
        self.main_window.event_bus.shutdown()
        self.main_window.db.close()
        
        if event:
            event.accept()
    
    def activate_from_external(self):
        """
        Request window activation from an external source (single-instance support).
        
        Called when another instance attempts to start and sends an activation message.
        Ensures the window is restored, shown, and focused.
        """
        # Restore if minimized
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        
        self.main_window.show()           # Ensure visible
        self.main_window.raise_()         # Bring to top
        self.main_window.activateWindow() # Set focus