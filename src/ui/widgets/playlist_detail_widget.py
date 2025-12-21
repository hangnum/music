"""
Playlist Detail Component

Displays the track list within a playlist, supporting playback, track removal, drag-and-drop sorting, etc.
Uses the Model-View architecture for virtualized rendering.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListView, QPushButton, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import List, Optional

from models.playlist import Playlist
from models.track import Track
from services.playlist_service import PlaylistService
from services.player_service import PlayerService
from ui.models.track_list_model import TrackListModel
from ui.styles.theme_manager import ThemeManager


class PlaylistDetailWidget(QWidget):
    """
    Playlist Detail Component
    
    Displays the track list of a specific playlist, supporting playback, removal, and drag-and-drop sorting.
    Uses Model-View architecture for virtualized rendering.
    
    Signals:
        back_requested: Emitted when back to playlist list is requested
        track_double_clicked: Emitted when a track is double-clicked
    """
    
    back_requested = pyqtSignal()
    track_double_clicked = pyqtSignal(Track)
    
    def __init__(self, playlist_service: PlaylistService, 
                 player_service: PlayerService, parent=None):
        """
        Initialize the component.
        
        Args:
            playlist_service: Playlist service instance
            player_service: Player service instance
            parent: Parent component
        """
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._player_service = player_service
        self._current_playlist: Optional[Playlist] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header bar
        header = QHBoxLayout()
        
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.setToolTip("Back to Playlist List")
        self.back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_btn)
        
        self.title_label = QLabel("Playlist Details")
        self.title_label.setStyleSheet(ThemeManager.get_section_title_style())
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        self.play_all_btn = QPushButton("▶ Play All")
        self.play_all_btn.clicked.connect(self._play_all)
        header.addWidget(self.play_all_btn)
        
        layout.addLayout(header)
        
        # Description
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(ThemeManager.get_secondary_label_style())
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # Track List - Model-View architecture
        self._model = TrackListModel(enable_drag_drop=True)
        
        self.list_view = QListView()
        self.list_view.setModel(self._model)
        
        # Enable drag-and-drop sorting
        self.list_view.setDragEnabled(True)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDropIndicatorShown(True)
        self.list_view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # Performance optimization: uniform item sizes
        self.list_view.setUniformItemSizes(True)
        
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        self.list_view.doubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.list_view)
        
        # Bottom info
        self.info_label = QLabel("0 tracks")
        self.info_label.setStyleSheet(ThemeManager.get_info_label_style())
        layout.addWidget(self.info_label)
    
    @property
    def playlist(self) -> Optional[Playlist]:
        """Get the currently displayed playlist."""
        return self._current_playlist
    
    def set_playlist(self, playlist: Playlist):
        """
        Set the currently displayed playlist.
        
        Args:
            playlist: Playlist object
        """
        self._current_playlist = playlist
        self._refresh()
    
    def _refresh(self):
        """Refresh the track list."""
        if not self._current_playlist:
            self._model.setTracks([])
            return
        
        self.title_label.setText(self._current_playlist.name)
        self.desc_label.setText(self._current_playlist.description or "")
        self.desc_label.setVisible(bool(self._current_playlist.description))
        
        # Get tracks and set to model
        tracks = self._playlist_service.get_tracks(self._current_playlist.id)
        self._model.setTracks(tracks)
        
        # Update statistics
        count = len(tracks)
        duration = self._current_playlist.duration_str if self._current_playlist.total_duration_ms > 0 else ""
        info = f"{count} tracks"
        if duration:
            info += f" · {duration}"
        self.info_label.setText(info)
    
    def _on_item_double_clicked(self, index):
        """Double-click to play a track."""
        track = self._model.getTrack(index.row())
        if track:
            # Add entire playlist to playback queue
            tracks = self._model.getTracks()
            self._player_service.clear_queue()
            for t in tracks:
                self._player_service.add_to_queue(t)
            
            # Play the selected track
            self._player_service.play(track)
            self.track_double_clicked.emit(track)
    
    def _play_all(self):
        """Play all tracks."""
        tracks = self._model.getTracks()
        if not tracks:
            return
        
        self._player_service.clear_queue()
        for track in tracks:
            self._player_service.add_to_queue(track)
        
        self._player_service.play(tracks[0])
    
    def _show_context_menu(self, pos):
        """Display context menu."""
        index = self.list_view.indexAt(pos)
        if not index.isValid():
            return
        
        track = self._model.getTrack(index.row())
        if not track:
            return
        
        menu = QMenu(self)
        
        # Play
        play_action = QAction("Play", self)
        play_action.triggered.connect(lambda: self._player_service.play(track))
        menu.addAction(play_action)
        
        # Add to queue
        add_queue_action = QAction("Add to Queue", self)
        add_queue_action.triggered.connect(lambda: self._player_service.add_to_queue(track))
        menu.addAction(add_queue_action)
        
        menu.addSeparator()
        
        # Remove from playlist
        remove_action = QAction("Remove from Playlist", self)
        remove_action.triggered.connect(lambda: self._remove_track(track))
        menu.addAction(remove_action)
        
        menu.exec(self.list_view.mapToGlobal(pos))
    
    def _remove_track(self, track: Track):
        """Remove a track from the playlist."""
        if self._current_playlist:
            self._playlist_service.remove_track(self._current_playlist.id, track.id)
            # Re-fetch the playlist to update track_count
            self._current_playlist = self._playlist_service.get(self._current_playlist.id)
            self._refresh()
