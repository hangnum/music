"""
Track Table Model

Uses QAbstractTableModel to implement virtualized rendering, optimizing performance for large lists.
"""

from typing import List, Optional, Any, Set

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt6.QtGui import QColor

from models.track import Track


class TrackTableModel(QAbstractTableModel):
    """
    Track Table Model
    
    Implements virtualized rendering through the Model-View architecture, 
    rendering only the visible area to significantly improve large list performance.
    
    Attributes:
        COLUMNS: Column definitions (Title, Artist, Album, Duration, Format, Liked)
    """
    
    COLUMNS = ["Title", "Artist", "Album", "Duration", "Format", "Liked"]
    
    def __init__(self, parent=None):
        """Initialize the model."""
        super().__init__(parent)
        self._tracks: List[Track] = []
        self._favorite_ids: Set[str] = set()
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows."""
        if parent.isValid():
            return 0
        return len(self._tracks)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        Return data for a specified index.
        
        Args:
            index: Model index
            role: Data role
            
        Returns:
            Data corresponding to the role
        """
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._tracks):
            return None
        
        track = self._tracks[row]
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return track.title
            elif col == 1:
                return track.artist_name or "-"
            elif col == 2:
                return track.album_name or "-"
            elif col == 3:
                return track.duration_str
            elif col == 4:
                return track.format
            elif col == 5:
                return "Yes" if track.id in self._favorite_ids else ""
        
        elif role == Qt.ItemDataRole.UserRole:
            # Return complete Track object
            return track
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (3, 4):  # Center align duration and format
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None
    
    def setTracks(self, tracks: List[Track]) -> None:
        """
        Set the track list.
        
        Uses beginResetModel/endResetModel to notify the view of updates.
        
        Args:
            tracks: List of tracks
        """
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()
    
    def setFavoriteIds(self, favorite_ids: Set[str]) -> None:
        """Set the set of favorite track IDs."""
        self._favorite_ids = set(favorite_ids)
        if self._tracks:
            top_left = self.index(0, len(self.COLUMNS) - 1)
            bottom_right = self.index(len(self._tracks) - 1, len(self.COLUMNS) - 1)
            self.dataChanged.emit(top_left, bottom_right)

    def getTracks(self) -> List[Track]:
        """Get all tracks."""
        return self._tracks
    
    def getTrack(self, row: int) -> Optional[Track]:
        """
        Get track at specified row.
        
        Args:
            row: Row index
            
        Returns:
            Track object, or None if invalid row
        """
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """
        Sort by column.
        
        Args:
            column: Column index
            order: Sort order
        """
        self.beginResetModel()
        
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        key_funcs = {
            0: lambda t: t.title.lower(),
            1: lambda t: (t.artist_name or "").lower(),
            2: lambda t: (t.album_name or "").lower(),
            3: lambda t: t.duration_ms,
            4: lambda t: t.format.lower(),
            5: lambda t: t.id in self._favorite_ids,
        }
        
        key_func = key_funcs.get(column, lambda t: t.title.lower())
        self._tracks.sort(key=key_func, reverse=reverse)
        
        self.endResetModel()


class TrackFilterProxyModel(QSortFilterProxyModel):
    """
    Track Filter Proxy Model
    
    Supports fuzzy search filtering by title, artist, or album.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_text = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    
    def setFilterText(self, text: str) -> None:
        """Set the filter text."""
        self._filter_text = text.lower()
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Determine if a row should be accepted by the filter."""
        if not self._filter_text:
            return True
        
        source_model = self.sourceModel()
        if not source_model:
            return True
        
        track = source_model.getTrack(source_row)
        if not track:
            return True
        
        # Search title, artist, and album
        return (self._filter_text in track.title.lower() or
                self._filter_text in (track.artist_name or "").lower() or
                self._filter_text in (track.album_name or "").lower())
