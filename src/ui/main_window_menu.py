"""
Main Window Menu Manager

Responsible for menu bar creation and handling all menu actions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QAction

from ui.dialogs.llm_settings_dialog import LLMSettingsDialog
from ui.dialogs.audio_settings_dialog import AudioSettingsDialog
from ui.dialogs.llm_queue_chat_dialog import LLMQueueChatDialog
from ui.dialogs.daily_playlist_dialog import DailyPlaylistDialog

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from app.container import AppContainer


class MainWindowMenuManager:
    """Main window menu manager"""
    
    def __init__(self, main_window: "MainWindow"):
        """Initialize the menu manager.
        
        Args:
            main_window: Main window instance, used to access services and properties.
        """
        self.main_window = main_window
        self._setup_menu()
    
    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.main_window.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        
        add_folder = QAction("Add Folder", self.main_window)
        add_folder.triggered.connect(self.main_window._on_add_folder_clicked)
        file_menu.addAction(add_folder)
        
        scan_action = QAction("Scan Library", self.main_window)
        scan_action.triggered.connect(self.main_window._on_scan_clicked)
        file_menu.addAction(scan_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)
        
        # Play Menu
        play_menu = menubar.addMenu("Play")
        
        play_pause = QAction("Play/Pause", self.main_window)
        play_pause.setShortcut("Space")
        play_pause.triggered.connect(self.main_window.player.toggle_play)
        play_menu.addAction(play_pause)
        
        next_track = QAction("Next Track", self.main_window)
        next_track.setShortcut("Ctrl+Right")
        next_track.triggered.connect(self.main_window.player.next_track)
        play_menu.addAction(next_track)
        
        prev_track = QAction("Previous Track", self.main_window)
        prev_track.setShortcut("Ctrl+Left")
        prev_track.triggered.connect(self.main_window.player.previous_track)
        play_menu.addAction(prev_track)

        # AI Menu
        ai_menu = menubar.addMenu("AI")

        llm_settings = QAction("LLM Settings...", self.main_window)
        llm_settings.triggered.connect(self._open_llm_settings)
        ai_menu.addAction(llm_settings)

        queue_assistant = QAction("Queue Assistant...", self.main_window)
        queue_assistant.setShortcut("Ctrl+L")
        queue_assistant.triggered.connect(self._open_llm_queue_assistant)
        ai_menu.addAction(queue_assistant)
        
        ai_menu.addSeparator()
        
        llm_tagging = QAction("AI Tagging...", self.main_window)
        llm_tagging.triggered.connect(self._start_llm_tagging)
        ai_menu.addAction(llm_tagging)
        
        ai_menu.addSeparator()
        
        daily_playlist = QAction("Daily Playlist...", self.main_window)
        daily_playlist.setShortcut("Ctrl+D")
        daily_playlist.triggered.connect(self._open_daily_playlist)
        ai_menu.addAction(daily_playlist)
        
        # Settings Menu
        settings_menu = menubar.addMenu("Settings")
        
        audio_settings = QAction("Audio Settings...", self.main_window)
        audio_settings.triggered.connect(self._open_audio_settings)
        settings_menu.addAction(audio_settings)
        
        llm_settings_action = QAction("LLM Settings...", self.main_window)
        llm_settings_action.triggered.connect(self._open_llm_settings)
        settings_menu.addAction(llm_settings_action)
        
        # View Menu
        view_menu = menubar.addMenu("View")
        
        mini_mode = QAction("Mini Mode", self.main_window)
        mini_mode.setShortcut("Ctrl+M")
        mini_mode.triggered.connect(self.main_window._switch_to_mini_mode)
        view_menu.addAction(mini_mode)
        
        # Help Menu
        help_menu = menubar.addMenu("Help")
        
        about = QAction("About", self.main_window)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _open_llm_settings(self):
        dlg = LLMSettingsDialog(self.main_window.config, self.main_window)
        dlg.exec()

    def _open_audio_settings(self):
        dlg = AudioSettingsDialog(self.main_window.config, self.main_window)
        dlg.exec()

    def _open_llm_queue_assistant(self):
        dlg = LLMQueueChatDialog(facade=self.main_window.facade, parent=self.main_window)
        dlg.exec()
    
    def _start_llm_tagging(self):
        """Start LLM tagging."""
        if self.main_window.llm_tagging_service is None:
            QMessageBox.warning(
                self.main_window, "LLM Service Unavailable",
                "LLM tagging service is not initialized.\nPlease check if the LLM API Key is configured correctly."
            )
            return
        
        from ui.dialogs.llm_tagging_progress_dialog import LLMTaggingProgressDialog
        dlg = LLMTaggingProgressDialog(
            llm_tagging_service=self.main_window.llm_tagging_service,
            parent=self.main_window,
        )
        dlg.exec()
    
    def _open_daily_playlist(self):
        """Open the Daily Playlist dialog."""
        dlg = DailyPlaylistDialog(
            facade=self.main_window.facade,
            parent=self.main_window,
        )
        dlg.exec()
    
    def _show_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self.main_window,
            "About Python Music Player",
            "Python Music Player v1.0\n\n"
            "A high-quality local music player.\n\n"
            "Tech stack: PyQt6 + pygame + mutagen"
        )
