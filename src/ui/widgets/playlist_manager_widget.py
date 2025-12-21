"""
Playlist Manager Component

Displays the list of playlists created by the user, supporting creation, renaming, and deletion.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QMenu,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import Optional

from models.playlist import Playlist
from services.playlist_service import PlaylistService
from core.event_bus import EventBus
from app.events import EventType
from ui.styles.theme_manager import ThemeManager


class PlaylistManagerWidget(QWidget):
    """
    Playlist Manager Component
    
    Displays and manages user playlists, decoupled from the main window implementation.
    
    Signals:
        playlist_selected: Emitted when a playlist is selected
        create_requested: Emitted when a request to create a new playlist is made
    """
    
    playlist_selected = pyqtSignal(Playlist)
    create_requested = pyqtSignal()
    
    def __init__(self, playlist_service: PlaylistService, parent=None):
        """
        Initialize the component.
        
        Args:
            playlist_service: Playlist service instance
            parent: Parent component
        """
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._event_bus = EventBus()
        
        self._setup_ui()
        self._connect_signals()
        self.refresh()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header bar
        header = QHBoxLayout()
        
        title = QLabel("My Playlists")
        title.setStyleSheet(ThemeManager.get_section_title_style())
        header.addWidget(title)
        
        header.addStretch()
        
        self.add_btn = QPushButton("＋")
        self.add_btn.setFixedSize(32, 32)
        self.add_btn.setToolTip("Create Playlist")
        self.add_btn.clicked.connect(self.create_requested.emit)
        header.addWidget(self.add_btn)
        
        layout.addLayout(header)
        
        # Playlist list
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Bottom info
        self.info_label = QLabel("0 playlists")
        self.info_label.setStyleSheet(ThemeManager.get_info_label_style())
        layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """Connect events."""
        self._event_bus.subscribe(EventType.PLAYLIST_CREATED, self._on_playlist_changed)
        self._event_bus.subscribe(EventType.PLAYLIST_UPDATED, self._on_playlist_changed)
        self._event_bus.subscribe(EventType.PLAYLIST_DELETED, self._on_playlist_changed)
    
    def _on_playlist_changed(self, data=None):
        """Refresh when playlists change."""
        self.refresh()
    
    def refresh(self):
        """Refresh the playlist list."""
        self.list_widget.clear()
        
        playlists = self._playlist_service.get_all()
        
        for playlist in playlists:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, playlist)
            
            # Display text: name + track count
            text = f"🎵 {playlist.name}"
            if playlist.track_count > 0:
                text += f"  ({playlist.track_count})"
            
            item.setText(text)
            self.list_widget.addItem(item)
        
        self.info_label.setText(f"{len(playlists)} playlists")
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on a playlist."""
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if playlist:
            self.playlist_selected.emit(playlist)
    
    def _show_context_menu(self, pos):
        """Display the context menu."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if not playlist:
            return
        
        menu = QMenu(self)
        
        # Open
        open_action = QAction("Open", self)
        open_action.triggered.connect(lambda: self.playlist_selected.emit(playlist))
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        # Rename
        rename_action = QAction("Rename...", self)
        rename_action.triggered.connect(lambda: self._rename_playlist(playlist))
        menu.addAction(rename_action)
        
        # Delete
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_playlist(playlist))
        menu.addAction(delete_action)
        
        menu.exec(self.list_widget.mapToGlobal(pos))
    
    def _rename_playlist(self, playlist: Playlist):
        """Rename a playlist."""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        
        dialog = CreatePlaylistDialog(
            self, 
            edit_mode=True,
            initial_name=playlist.name,
            initial_description=playlist.description
        )
        
        if dialog.exec() == CreatePlaylistDialog.DialogCode.Accepted:
            self._playlist_service.update(
                playlist.id, 
                name=dialog.get_name(),
                description=dialog.get_description()
            )
            self.refresh()
    
    def _delete_playlist(self, playlist: Playlist):
        """Delete a playlist."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the playlist \"{playlist.name}\"?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._playlist_service.delete(playlist.id)
            self.refresh()
    
    def get_selected_playlist(self) -> Optional[Playlist]:
        """Get the currently selected playlist."""
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
