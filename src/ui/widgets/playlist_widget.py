"""
Playlist Widget

Displays current play queue, supports double-click to play, right-click menu, drag-and-drop reordering, etc.
Uses Model-View architecture to implement virtualized rendering.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListView, QPushButton, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from models.track import Track
from services.player_service import PlayerService
from app.events import EventType
from ui.models.track_list_model import TrackListModel
from ui.styles.theme_manager import ThemeManager


class PlaylistWidget(QWidget):
    """
    Playlist Widget

    Displays current play queue, supports playback, management, and drag-and-drop reordering.
    Uses Model-View architecture to implement virtualized rendering.
    """
    
    track_double_clicked = pyqtSignal(Track)
    llm_chat_requested = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, event_bus, parent=None):
        super().__init__(parent)
        self.player = player_service
        self.event_bus = event_bus
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Play Queue")
        title.setStyleSheet(ThemeManager.get_section_title_style())
        header.addWidget(title)
        
        header.addStretch()

        self.llm_btn = QPushButton("Queue Assistant...")
        self.llm_btn.setFixedWidth(90)
        self.llm_btn.clicked.connect(self.llm_chat_requested.emit)
        header.addWidget(self.llm_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        header.addWidget(self.clear_btn)
        
        layout.addLayout(header)
        
        # List - Model-View architecture
        self._model = TrackListModel(enable_drag_drop=True)
        self._model.setShowIndex(False)  # Play queue does not show index
        
        self.list_view = QListView()
        self.list_view.setModel(self._model)
        
        # Enable drag-and-drop reordering
        self.list_view.setDragEnabled(True)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDropIndicatorShown(True)
        self.list_view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # Performance optimization: uniform item height
        self.list_view.setUniformItemSizes(True)
        
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        self.list_view.doubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.list_view)
        
        # Bottom info
        self.info_label = QLabel("0  tracks")
        self.info_label.setStyleSheet(ThemeManager.get_info_label_style())
        layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """Connect signals"""
        self.event_bus.subscribe(EventType.QUEUE_CHANGED, self._on_queue_changed)
        self.event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
    
    def update_list(self):
        """Update list display"""
        queue = self.player.queue
        current = self.player.current_track
        
        self._model.setTracks(queue)
        
        # Highlight current playing track
        if current:
            self._model.highlightTrack(current.id)
        else:
            self._model.highlightTrack(None)
        
        self.info_label.setText(f"{len(queue)} tracks")
    
    def _on_queue_changed(self, queue):
        """Queue changed"""
        self.update_list()
    
    def _on_track_started(self, track):
        """Track started playing"""
        # Only update highlight, dont reset entire list
        if track:
            self._model.highlightTrack(track.id)
        else:
            self._model.highlightTrack(None)
    
    def _on_item_double_clicked(self, index):
        """Double-click track"""
        track = self._model.getTrack(index.row())
        if track:
            self.player.play(track)
            self.track_double_clicked.emit(track)
    
    def _show_context_menu(self, pos):
        """Show context menu"""
        index = self.list_view.indexAt(pos)
        if not index.isValid():
            return
        
        track = self._model.getTrack(index.row())
        if not track:
            return
        
        menu = QMenu(self)
        
        play_action = QAction("Play", self)
        play_action.triggered.connect(lambda: self.player.play(track))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        remove_action = QAction("Remove from Queue", self)
        remove_action.triggered.connect(lambda: self._remove_track(index.row()))
        menu.addAction(remove_action)
        
        menu.exec(self.list_view.mapToGlobal(pos))
    
    def _remove_track(self, row: int):
        """Remove track from queue"""
        if row >= 0:
            self.player.remove_from_queue(row)
    
    def _on_clear_clicked(self):
        """Clear queue"""
        self.player.clear_queue()
