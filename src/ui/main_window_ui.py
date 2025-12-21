"""
Main Window UI Builder

Responsible for window UI layout and sidebar creation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QSplitter,
    QLabel
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class MainWindowUIBuilder:
    """Main window UI builder"""
    
    def __init__(self, main_window: "MainWindow"):
        """Initialize UI builder

        Args:
            main_window: Main window instance for accessing services and properties
        """
        self.main_window = main_window
    
    def setup_ui(self):
        """Set up UI layout"""
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Use QSplitter instead of fixed QHBoxLayout
        self.main_window.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_window.splitter.setHandleWidth(1) # Thin divider
        self.main_window.splitter.setChildrenCollapsible(False)
        
        # Sidebar
        sidebar = self._create_sidebar()
        self.main_window.splitter.addWidget(sidebar)

        # Main content area
        self.main_window.content_stack = QStackedWidget()

        # Page indices: 0=Library, 1=Play Queue, 2=Playlist Management, 3=Playlist Details

        # Library page
        from ui.widgets.library_widget import LibraryWidget
        self.main_window.library_widget = LibraryWidget(
            facade=self.main_window.facade,
            llm_tagging_service=self.main_window.llm_tagging_service,
        )
        self.main_window.content_stack.addWidget(self.main_window.library_widget)
        
        # Play Queue page
        from ui.widgets.playlist_widget import PlaylistWidget
        self.main_window.playlist_widget = PlaylistWidget(self.main_window.player, self.main_window.event_bus)
        self.main_window.playlist_widget.llm_chat_requested.connect(self.main_window._open_llm_queue_assistant)
        self.main_window.content_stack.addWidget(self.main_window.playlist_widget)

        # Playlist Management page
        from ui.widgets.playlist_manager_widget import PlaylistManagerWidget
        self.main_window.playlist_manager = PlaylistManagerWidget(self.main_window.playlist_service)
        self.main_window.playlist_manager.create_requested.connect(self.main_window._on_create_playlist)
        self.main_window.playlist_manager.playlist_selected.connect(self.main_window._on_playlist_selected)
        self.main_window.content_stack.addWidget(self.main_window.playlist_manager)
        
        # Playlist Details page
        from ui.widgets.playlist_detail_widget import PlaylistDetailWidget
        self.main_window.playlist_detail = PlaylistDetailWidget(
            self.main_window.playlist_service, self.main_window.player
        )
        self.main_window.playlist_detail.back_requested.connect(lambda: self.main_window._switch_page(2))
        self.main_window.content_stack.addWidget(self.main_window.playlist_detail)

        self.main_window.splitter.addWidget(self.main_window.content_stack)

        # Set Splitter ratios
        self.main_window.splitter.setStretchFactor(0, 0)
        self.main_window.splitter.setStretchFactor(1, 1)

        # Restore splitter position
        last_width = self.main_window.config.get("ui.sidebar_width", 240)
        self.main_window.splitter.setSizes([last_width, 1000])

        main_layout.addWidget(self.main_window.splitter, 1)

        # Bottom playback controls
        from ui.widgets.player_controls import PlayerControls
        self.main_window.player_controls = PlayerControls(self.main_window.player)
        main_layout.addWidget(self.main_window.player_controls)
    
    def _create_sidebar(self) -> QWidget:
        """Create sidebar"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(200)  # Set minimum width

        # Apply sidebar button styles
        from ui.styles.theme_manager import ThemeManager
        sidebar.setStyleSheet(ThemeManager.get_sidebar_button_style())
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(4)
        
        # Apple Music group
        header_am = QLabel("Apple Music")
        header_am.setObjectName("sidebarHeader")
        layout.addWidget(header_am)

        # Navigation buttons
        self.main_window.nav_library = QPushButton("🎵  Now Listening")
        self.main_window.nav_library.setCheckable(True)
        self.main_window.nav_library.setChecked(True)
        self.main_window.nav_library.clicked.connect(lambda: self.main_window._switch_page(0))
        layout.addWidget(self.main_window.nav_library)

        self.main_window.nav_daily_playlist = QPushButton("✨  Daily Playlist")
        self.main_window.nav_daily_playlist.setCheckable(True)
        self.main_window.nav_daily_playlist.clicked.connect(self.main_window._on_daily_playlist_clicked)
        layout.addWidget(self.main_window.nav_daily_playlist)

        self.main_window.nav_discover = QPushButton("🌟  Discover")
        self.main_window.nav_discover.setCheckable(True)
        self.main_window.nav_discover.setEnabled(False) # Not yet implemented
        layout.addWidget(self.main_window.nav_discover)

        self.main_window.nav_radio = QPushButton("📻  Radio")
        self.main_window.nav_radio.setCheckable(True)
        self.main_window.nav_radio.setEnabled(False) # Not yet implemented
        layout.addWidget(self.main_window.nav_radio)
        
        layout.addSpacing(24)
        
        # Library group
        header_lib = QLabel("Library")
        header_lib.setObjectName("sidebarHeader")
        layout.addWidget(header_lib)

        self.main_window.nav_all_music = QPushButton("📚  All Music")  # Originally "Media Library"
        self.main_window.nav_all_music.setCheckable(True)
        self.main_window.nav_all_music.clicked.connect(lambda: self.main_window._switch_page(0))
        layout.addWidget(self.main_window.nav_all_music)

        self.main_window.nav_favorites = QPushButton("❤️  My Favorites")
        self.main_window.nav_favorites.setCheckable(True)
        self.main_window.nav_favorites.clicked.connect(self.main_window._open_favorites_playlist)
        layout.addWidget(self.main_window.nav_favorites)

        self.main_window.nav_queue = QPushButton("📋  Play Queue")
        self.main_window.nav_queue.setCheckable(True)
        self.main_window.nav_queue.clicked.connect(lambda: self.main_window._switch_page(1))
        layout.addWidget(self.main_window.nav_queue)
        
        layout.addSpacing(24)
        
        # My Playlists group
        header_playlist = QLabel("My Playlists")
        header_playlist.setObjectName("sidebarHeader")
        layout.addWidget(header_playlist)

        self.main_window.nav_playlists = QPushButton("📁  All Playlists")
        self.main_window.nav_playlists.setCheckable(True)
        self.main_window.nav_playlists.clicked.connect(lambda: self.main_window._switch_page(2))
        layout.addWidget(self.main_window.nav_playlists)

        self.main_window.add_playlist_btn = QPushButton("＋  New Playlist")
        self.main_window.add_playlist_btn.clicked.connect(self.main_window._on_create_playlist)
        layout.addWidget(self.main_window.add_playlist_btn)

        layout.addStretch()

        # Bottom toolbar
        self.main_window.scan_btn = QPushButton("🔄  Update Library")
        self.main_window.scan_btn.clicked.connect(self.main_window._on_scan_clicked)
        layout.addWidget(self.main_window.scan_btn)

        self.main_window.add_folder_btn = QPushButton("📁  Add Music...")
        self.main_window.add_folder_btn.clicked.connect(self.main_window._on_add_folder_clicked)
        layout.addWidget(self.main_window.add_folder_btn)

        layout.addSpacing(16)

        # Bottom info
        self.main_window.status_label = QLabel()
        from ui.resources.design_tokens import tokens
        self.main_window.status_label.setStyleSheet(f"color: {tokens.NEUTRAL_500}; padding: 0 20px; font-size: {tokens.FONT_SIZE_XS}px;")
        self.main_window._update_status()
        layout.addWidget(self.main_window.status_label)
        
        return sidebar