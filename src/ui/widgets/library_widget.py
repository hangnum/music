"""
Media Library Browser Component

Displays all tracks in the media library with support for search and sorting.
Uses Model-View architecture to implement virtualized rendering for optimal performance with large lists.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableView, QPushButton,
    QLineEdit, QHeaderView, QAbstractItemView, QMenu,
    QStyledItemDelegate
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QAction, QPainter, QColor, QBrush, QPen

from models.track import Track
from app.events import EventType
from ui.models.track_table_model import TrackTableModel, TrackFilterProxyModel
from ui.resources.design_tokens import tokens
from ui.styles.theme_manager import ThemeManager

if TYPE_CHECKING:
    from services.music_app_facade import MusicAppFacade


class TagDelegate(QStyledItemDelegate):
    """
    Renders tags as visual chips (rounded rectangles).
    """
    def paint(self, painter: QPainter, option, index):
        if not index.isValid():
            return
            
        tags_str = index.data()
        if not tags_str:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Setup area
        rect = option.rect
        
        # Split tags
        tags = [t.strip() for t in str(tags_str).split(',')]
        
        x_offset = rect.x()
        y_offset = rect.y() + (rect.height() - 22) / 2 # Center vertically (22px chip height)
        
        for tag in tags:
            if not tag: continue
            
            # Calculate width text
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(tag)
            chip_width = text_width + 16 # Padding
            chip_height = 22
            
            # Stop if overflowing cell width
            if x_offset + chip_width > rect.right():
                # Draw a small "..." indicator if possible or just stop
                break 
            
            # Draw Chip Background
            chip_rect = QRectF(x_offset, y_offset, chip_width, chip_height)
            
            # Deep purple chip color
            bg_color = QColor(63, 183, 166, 40) # #3FB7A6 with alpha
            text_color = QColor(223, 246, 243) # #DFF6F3
            
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(chip_rect, 6, 6)
            
            # Draw Text
            painter.setPen(text_color)
            painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, tag)
            
            x_offset += chip_width + 6 # Gap between chips
            
        painter.restore()


class LibraryWidget(QWidget):
    """
    Media library browser component

    Displays all tracks with support for search, sorting, and playback operations.
    """
    
    track_double_clicked = pyqtSignal(Track)
    add_to_queue = pyqtSignal(Track)
    
    def __init__(
        self,
        facade: "MusicAppFacade",
        llm_tagging_service=None,
        parent=None
    ):
        """Initialize media library component

        Args:
            facade: Application facade providing access to all services
            llm_tagging_service: LLM tagging service (optional)
            parent: Parent component
        """
        super().__init__(parent)
        self._facade = facade
        self._llm_tagging_service = llm_tagging_service
        self._favorite_ids: set = set()
        
        self.all_tracks: List[Track] = []
        
        self._setup_ui()
        self._connect_signals()
        self._load_tracks()
    
    def _setup_ui(self):
        """Set up UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)

        # Title and search bar
        header = QHBoxLayout()

        title = QLabel("Media Library")
        title.setObjectName("titleLabel")
        title.setStyleSheet(ThemeManager.get_title_label_style())
        header.addWidget(title)

        header.addStretch()

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks...")
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(self._on_search)
        header.addWidget(self.search_input)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedWidth(60)
        self.refresh_btn.clicked.connect(self._load_tracks)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)

        # Statistics
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(ThemeManager.get_info_label_style())
        layout.addWidget(self.stats_label)

        # Track table - using Model-View architecture
        self._source_model = TrackTableModel()
        self._proxy_model = TrackFilterProxyModel()
        self._proxy_model.setSourceModel(self._source_model)
        
        self.table = QTableView()
        self.table.setModel(self._proxy_model)
        
        # Header settings
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 80)

        # View properties
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        # Performance optimization: uniform row height
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(50) # Increase row height to accommodate Tag Chips

        # Set Tag column Delegate (assuming column 3 is Genre/Tags)
        # Note: Need to confirm TrackTableModel column definition, usually Genre is column 3
        self.table.setItemDelegateForColumn(3, TagDelegate(self.table))
        
        self.table.setStyleSheet(f"""
            QTableView {{
                alternate-background-color: {tokens.NEUTRAL_850};
            }}
            QTableView::item {{
                padding: 8px;
            }}
        """)
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
    
    def _connect_signals(self):
        """Connect signals"""
        self._facade.subscribe(EventType.LIBRARY_SCAN_COMPLETED, 
                               self._on_scan_completed)
        self._facade.subscribe(EventType.TRACK_ADDED, self._on_track_added)
        self._facade.subscribe(EventType.PLAYLIST_UPDATED, self._on_playlist_updated)
        self._facade.subscribe(EventType.PLAYLIST_DELETED, self._on_playlist_deleted)
    
    def _load_tracks(self):
        """Load all tracks"""
        self.all_tracks = self._facade.get_all_tracks()
        self._display_tracks(self.all_tracks)
        self._refresh_favorites()

    def _display_tracks(self, tracks: List[Track]):
        """Display track list - using Model for O(1) updates"""
        self._source_model.setTracks(tracks)
        self._update_stats(tracks)

    def _update_stats(self, tracks: List[Track]):
        """Update statistics"""
        total_duration = sum(t.duration_ms for t in tracks)
        hours = total_duration // 3600000
        minutes = (total_duration % 3600000) // 60000
        self.stats_label.setText(
            f"{len(tracks)} tracks · {hours}h {minutes}m"
        )

    def _on_search(self, text: str):
        """Search tracks - using proxy model for filtering"""
        self._proxy_model.setFilterText(text)
        # Update statistics for filtered count
        filtered_count = self._proxy_model.rowCount()
        if text:
            self.stats_label.setText(f"Found {filtered_count} tracks")
        else:
            self._update_stats(self.all_tracks)

    def _on_row_double_clicked(self, index):
        """Row double-clicked"""
        # Get source model index through proxy model
        source_index = self._proxy_model.mapToSource(index)
        track = self._source_model.getTrack(source_index.row())

        if track:
            # Add all currently visible tracks to queue
            visible_tracks = self._get_visible_tracks()
            track_index = next((i for i, t in enumerate(visible_tracks) 
                               if t.id == track.id), 0)
            self._facade.set_queue(visible_tracks, track_index)
            self._facade.play()
            self.track_double_clicked.emit(track)
    
    def _get_visible_tracks(self) -> List[Track]:
        """Get all currently displayed tracks (filtered)"""
        tracks = []
        for row in range(self._proxy_model.rowCount()):
            source_index = self._proxy_model.mapToSource(
                self._proxy_model.index(row, 0)
            )
            track = self._source_model.getTrack(source_index.row())
            if track:
                tracks.append(track)
        return tracks
    
    def _refresh_favorites(self) -> None:
        """Refresh favorites status"""
        self._favorite_ids = self._facade.get_favorite_ids()
        self._source_model.setFavoriteIds(self._favorite_ids)

    def _set_favorite_for_tracks(self, tracks: List[Track], make_favorite: bool) -> None:
        """Set favorite status for tracks"""
        if make_favorite:
            self._facade.add_to_favorites(tracks)
        else:
            self._facade.remove_from_favorites([t.id for t in tracks])

        self._refresh_favorites()

    def _on_playlist_updated(self, playlist) -> None:
        """Refresh favorites when playlist updated"""
        # Simplified implementation: refresh favorites on any playlist update
        self._refresh_favorites()

    def _on_playlist_deleted(self, playlist_id: str) -> None:
        """Refresh favorites when playlist deleted"""
        self._refresh_favorites()


    def _show_context_menu(self, pos):
        """Show context menu"""
        rows = set(index.row() for index in self.table.selectedIndexes())
        if not rows:
            return

        menu = QMenu(self)

        # Get selected tracks
        selected_tracks = []
        for row in rows:
            source_index = self._proxy_model.mapToSource(
                self._proxy_model.index(row, 0)
            )
            track = self._source_model.getTrack(source_index.row())
            if track:
                selected_tracks.append(track)
        
        if len(selected_tracks) == 1:
            track = selected_tracks[0]

            play_now = QAction("Play Now", self)
            play_now.triggered.connect(lambda: self._play_track(track))
            menu.addAction(play_now)

            play_next = QAction("Play Next", self)
            play_next.triggered.connect(lambda: self._facade._player.insert_next(track))
            menu.addAction(play_next)

        add_to_queue = QAction(f"Add to Queue ({len(selected_tracks)} tracks)", self)
        add_to_queue.triggered.connect(lambda: self._add_tracks_to_queue(selected_tracks))
        menu.addAction(add_to_queue)

        # Favorites feature
        if self._facade.favorites_service:
            all_favorite = all(t.id in self._favorite_ids for t in selected_tracks)
            if all_favorite:
                label = "Remove from Favorites"
                make_favorite = False
            else:
                label = f"Add to Favorites ({len(selected_tracks)} tracks)"
                make_favorite = True
            favorite_action = QAction(label, self)
            favorite_action.triggered.connect(
                lambda: self._set_favorite_for_tracks(selected_tracks, make_favorite)
            )
            menu.addAction(favorite_action)

        # Add to playlist submenu
        playlist_menu = menu.addMenu(f"Add to Playlist ({len(selected_tracks)} tracks)")
        playlists = self._facade.get_playlists()

        if playlists:
            for playlist in playlists:
                action = QAction(f"🎵 {playlist.name}", self)
                # Use closure to capture playlist.id
                action.triggered.connect(
                    lambda checked, pid=playlist.id: self._add_to_playlist(pid, selected_tracks)
                )
                playlist_menu.addAction(action)
        else:
            no_playlist = QAction("(No playlists)", self)
            no_playlist.setEnabled(False)
            playlist_menu.addAction(no_playlist)
        
        menu.addSeparator()
        
        # Manage tags
        manage_tags = QAction(f"Manage Tags ({len(selected_tracks)} tracks)", self)
        manage_tags.triggered.connect(lambda: self._show_tag_dialog(selected_tracks))
        menu.addAction(manage_tags)

        # AI Detailed Tagging (single track only)
        if len(selected_tracks) == 1:
            ai_tagging = QAction("🤖 AI Detailed Tagging", self)
            ai_tagging.triggered.connect(
                lambda: self._show_detailed_tagging_dialog(selected_tracks[0])
            )
            menu.addAction(ai_tagging)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))
    
    def _play_track(self, track: Track):
        """Play track"""
        visible_tracks = self._get_visible_tracks()
        track_index = next((i for i, t in enumerate(visible_tracks)
                           if t.id == track.id), 0)
        self._facade.set_queue(visible_tracks, track_index)
        self._facade.play()

    def _add_tracks_to_queue(self, tracks: List[Track]):
        """Add tracks to queue"""
        for track in tracks:
            self._facade._player.add_to_queue(track)
            self.add_to_queue.emit(track)

    def _add_to_playlist(self, playlist_id: str, tracks: List[Track]):
        """Add tracks to playlist"""
        for track in tracks:
            self._facade.add_track_to_playlist(playlist_id, track.id)

    def _show_tag_dialog(self, tracks: List[Track]):
        """Show tag management dialog"""
        from ui.dialogs.tag_dialog import TagDialog
        from PyQt6.QtWidgets import QMessageBox

        if self._facade.tag_service is None:
            QMessageBox.warning(
                self, "Tag Service Unavailable",
                "Tag service is not initialized."
            )
            return

        dialog = TagDialog(tracks, self._facade.tag_service, self)
        dialog.exec()

    def _on_scan_completed(self, data):
        """Scan completed"""
        self._load_tracks()

    def _on_track_added(self, track):
        """New track added"""
        pass  # Can implement incremental updates

    def _show_detailed_tagging_dialog(self, track: Track):
        """Show AI detailed tagging dialog"""
        from ui.dialogs.detailed_tagging_dialog import DetailedTaggingDialog
        from PyQt6.QtWidgets import QMessageBox

        if self._llm_tagging_service is None:
            QMessageBox.warning(
                self, "AI Tagging Unavailable",
                "LLM tag annotation service is not initialized.\nPlease check LLM API Key configuration."
            )
            return

        dialog = DetailedTaggingDialog(track, self._llm_tagging_service, self)
        dialog.tagging_completed.connect(lambda _: self._load_tracks())
        dialog.exec()
