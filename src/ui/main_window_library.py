"""
Main Window Library Manager

Responsible for media library folder operations and scan management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from app.container import AppContainer


class MainWindowLibraryManager:
    """Main window library manager"""
    
    def __init__(self, main_window: "MainWindow"):
        """Initialize the library manager.
        
        Args:
            main_window: Main window instance, used to access services and properties.
        """
        self.main_window = main_window
        self._connect_library_events()
    
    def _connect_library_events(self):
        """Connect library-related events."""
        from app.events import EventType
        self.main_window.event_bus.subscribe(EventType.LIBRARY_SCAN_COMPLETED, 
                                              self._on_scan_completed)
        self.main_window.event_bus.subscribe(EventType.LIBRARY_SCAN_PROGRESS,
                                              self._on_scan_progress)
    
    def _on_scan_clicked(self):
        """Scan the media library."""
        dirs = self.main_window.config.get("library.directories", [])
        if dirs:
            self.main_window.scan_btn.setText("🔄  Scanning...")
            self.main_window.scan_btn.setEnabled(False)
            self.main_window.library.scan_async(dirs)
        else:
            QMessageBox.information(
                self.main_window, "Information", 
                "Please add music folders to the configuration first."
            )
    
    def _on_add_folder_clicked(self):
        """Add a folder."""
        folder = QFileDialog.getExistingDirectory(
            self.main_window, "Select Music Folder", ""
        )
        
        if folder:
            dirs = self.main_window.config.get("library.directories", [])
            if folder not in dirs:
                dirs.append(folder)
                self.main_window.config.set("library.directories", dirs)
                self.main_window.config.save()
                
                # Automatic scan
                self.main_window.scan_btn.setText("🔄  Scanning...")
                self.main_window.scan_btn.setEnabled(False)
                self.main_window.library.scan_async([folder])
    
    def _on_scan_completed(self, data):
        """Handle scan completion."""
        self.main_window.scan_btn.setText("🔍  Scan Library")
        self.main_window.scan_btn.setEnabled(True)
        self._update_status()
        
        QMessageBox.information(
            self.main_window, "Scan Completed",
            f"Scan completed!\nAdded {data.get('total_added', 0)} tracks."
        )
    
    def _on_scan_progress(self, data):
        """Handle scan progress updates."""
        current = data.get('current', 0)
        total = data.get('total', 0)
        self.main_window.scan_btn.setText(f"🔄  {current}/{total}")
    
    def _update_status(self):
        """Update status information."""
        count = self.main_window.library.get_track_count()
        self.main_window.status_label.setText(f"Library: {count} tracks")
