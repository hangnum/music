"""
Track List Model

Uses QAbstractListModel to implement virtualized rendering, supporting drag-and-drop sorting.
"""

from typing import List, Optional, Any

from PyQt6.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QMimeData, QByteArray
)

from models.track import Track


class TrackListModel(QAbstractListModel):
    """
    Track List Model
    
    Implements virtualized rendering through the Model-View architecture, 
    supporting drag-and-drop reordering.
    
    Features:
        - Virtualized rendering, only visible items are rendered.
        - Drag-and-drop sorting support.
        - Highlighting of the currently playing track.
    """
    
    MIME_TYPE = "application/x-track-indices"
    
    def __init__(self, parent=None, enable_drag_drop: bool = True):
        """
        Initialize the model.
        
        Args:
            parent: Parent object.
            enable_drag_drop: Whether to enable drag-and-drop sorting.
        """
        super().__init__(parent)
        self._tracks: List[Track] = []
        self._highlighted_id: Optional[str] = None
        self._enable_drag_drop = enable_drag_drop
        self._show_index = True  # Whether to show sequence numbers
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows."""
        if parent.isValid():
            return 0
        return len(self._tracks)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for a specified index."""
        if not index.isValid():
            return None
        
        row = index.row()
        if row < 0 or row >= len(self._tracks):
            return None
        
        track = self._tracks[row]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # Format: #. Title - Artist [Duration]
            if self._show_index:
                text = f"{row + 1}. {track.title}"
            else:
                text = track.title
            
            if track.artist_name:
                text += f" - {track.artist_name}"
            text += f"  [{track.duration_str}]"
            
            # Highlight current playback
            if self._highlighted_id and track.id == self._highlighted_id:
                text = f"▶ {text}"
            
            return text
        
        elif role == Qt.ItemDataRole.UserRole:
            return track
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            if self._highlighted_id and track.id == self._highlighted_id:
                from PyQt6.QtGui import QColor
                return QColor(Qt.GlobalColor.green)
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags."""
        default_flags = super().flags(index)
        
        if not index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled
        
        if self._enable_drag_drop:
            return (default_flags | Qt.ItemFlag.ItemIsDragEnabled | 
                    Qt.ItemFlag.ItemIsDropEnabled)
        
        return default_flags
    
    def supportedDropActions(self) -> Qt.DropAction:
        """Return supported drop actions."""
        return Qt.DropAction.MoveAction
    
    def mimeTypes(self) -> List[str]:
        """Return supported MIME types."""
        return [self.MIME_TYPE]
    
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        """Generate drag-and-drop data."""
        mime_data = QMimeData()
        
        rows = sorted(set(index.row() for index in indexes if index.isValid()))
        data = ",".join(str(row) for row in rows)
        mime_data.setData(self.MIME_TYPE, QByteArray(data.encode()))
        
        return mime_data
    
    def dropMimeData(self, data: QMimeData, action: Qt.DropAction,
                     row: int, column: int, parent: QModelIndex) -> bool:
        """Handle drop MIME data."""
        if action == Qt.DropAction.IgnoreAction:
            return True
        
        if not data.hasFormat(self.MIME_TYPE):
            return False
        
        # Parse source row numbers
        raw_data = bytes(data.data(self.MIME_TYPE)).decode()
        source_rows = [int(r) for r in raw_data.split(",") if r]
        
        if not source_rows:
            return False
        
        # Determine target position
        if row < 0:
            if parent.isValid():
                row = parent.row()
            else:
                row = len(self._tracks)
        
        # Move items
        self._move_rows(source_rows, row)
        return True
    
    def _move_rows(self, source_rows: List[int], target_row: int) -> None:
        """Move rows to target position."""
        # Extract tracks to move
        tracks_to_move = [self._tracks[r] for r in sorted(source_rows, reverse=True)]
        
        # Delete from original position
        for row in sorted(source_rows, reverse=True):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._tracks[row]
            self.endRemoveRows()
        
        # Adjust target position
        for row in sorted(source_rows):
            if row < target_row:
                target_row -= 1
        
        # Insert into new position
        for i, track in enumerate(reversed(tracks_to_move)):
            insert_row = target_row
            self.beginInsertRows(QModelIndex(), insert_row, insert_row)
            self._tracks.insert(insert_row, track)
            self.endInsertRows()
    
    def setTracks(self, tracks: List[Track]) -> None:
        """Set track list."""
        self.beginResetModel()
        self._tracks = list(tracks)  # Copy list to avoid external modification
        self.endResetModel()
    
    def getTracks(self) -> List[Track]:
        """Get all tracks."""
        return list(self._tracks)
    
    def getTrack(self, row: int) -> Optional[Track]:
        """Get track at specified row."""
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None
    
    def highlightTrack(self, track_id: Optional[str]) -> None:
        """
        Highlight a specified track.
        
        Args:
            track_id: Track ID, or None to clear highlight.
        """
        self._highlighted_id = track_id
        # Notify view to refresh
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ForegroundRole]
        )
    
    def setShowIndex(self, show: bool) -> None:
        """Set whether to show sequence numbers."""
        self._show_index = show
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.DisplayRole]
        )
