"""
UI Model Layer Unit Tests

Tests core logic for TrackTableModel, TrackFilterProxyModel, and TrackListModel.
"""

import pytest
from PyQt6.QtCore import Qt, QModelIndex


class TestTrackTableModel:
    """TrackTableModel Unit Tests"""

    @pytest.fixture
    def model(self, qapp):
        """Create a TrackTableModel instance."""
        from ui.models.track_table_model import TrackTableModel
        return TrackTableModel()
    
    @pytest.fixture
    def sample_tracks(self):
        """Create a sample track list."""
        from models.track import Track
        return [
            Track(id="1", title="Alpha Song", artist_name="Artist A", 
                  album_name="Album X", duration_ms=180000, format="mp3"),
            Track(id="2", title="Beta Song", artist_name="Artist B", 
                  album_name="Album Y", duration_ms=240000, format="flac"),
            Track(id="3", title="Gamma Song", artist_name="Artist C", 
                  album_name="Album Z", duration_ms=300000, format="wav"),
        ]
    
    def test_row_count_empty(self, model):
        """Empty model should have 0 rows."""
        assert model.rowCount() == 0
    
    def test_row_count_with_tracks(self, model, sample_tracks):
        """Row count should be correct after setting tracks."""
        model.setTracks(sample_tracks)
        assert model.rowCount() == 3
    
    def test_column_count(self, model):
        """Column count should be fixed at 6."""
        assert model.columnCount() == 6
    
    def test_data_display_role_title(self, model, sample_tracks):
        """DisplayRole should return the title."""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Alpha Song"
    
    def test_data_display_role_artist(self, model, sample_tracks):
        """DisplayRole should return the artist name."""
        model.setTracks(sample_tracks)
        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Artist A"
    
    def test_data_display_role_album(self, model, sample_tracks):
        """DisplayRole should return the album name."""
        model.setTracks(sample_tracks)
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Album X"
    
    def test_data_display_role_format(self, model, sample_tracks):
        """DisplayRole should return the format."""
        model.setTracks(sample_tracks)
        index = model.index(0, 4)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "mp3"
    
    def test_data_user_role(self, model, sample_tracks):
        """UserRole should return the Track object."""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        track = model.data(index, Qt.ItemDataRole.UserRole)
        assert track.id == "1"
        assert track.title == "Alpha Song"
    
    def test_data_invalid_index(self, model, sample_tracks):
        """Invalid index should return None."""
        model.setTracks(sample_tracks)
        index = model.index(100, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) is None
    
    def test_header_data(self, model):
        """Header data should be correct."""
        assert model.headerData(0, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "Title"
        assert model.headerData(1, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "Artist"
        assert model.headerData(2, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "Album"
        assert model.headerData(3, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "Duration"
        assert model.headerData(4, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "Format"
    
    def test_header_data_invalid_section(self, model):
        """Invalid column index should return None."""
        assert model.headerData(10, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) is None
    
    def test_set_tracks(self, model, sample_tracks):
        """setTracks should update the model."""
        model.setTracks(sample_tracks)
        assert model.rowCount() == 3
        assert model.getTracks() == sample_tracks
    
    def test_get_tracks(self, model, sample_tracks):
        """getTracks should return the track list."""
        model.setTracks(sample_tracks)
        tracks = model.getTracks()
        assert len(tracks) == 3
        assert tracks[0].title == "Alpha Song"
    
    def test_get_track_valid(self, model, sample_tracks):
        """getTrack should return the track at the specified row."""
        model.setTracks(sample_tracks)
        track = model.getTrack(1)
        assert track.title == "Beta Song"
    
    def test_get_track_invalid_negative(self, model, sample_tracks):
        """Negative index should return None."""
        model.setTracks(sample_tracks)
        assert model.getTrack(-1) is None
    
    def test_get_track_invalid_out_of_range(self, model, sample_tracks):
        """Index out of range should return None."""
        model.setTracks(sample_tracks)
        assert model.getTrack(100) is None
    
    def test_sort_by_title_ascending(self, model, sample_tracks):
        """Sort by title in ascending order."""
        model.setTracks(sample_tracks)
        model.sort(0, Qt.SortOrder.AscendingOrder)
        assert model.getTrack(0).title == "Alpha Song"
        assert model.getTrack(2).title == "Gamma Song"
    
    def test_sort_by_title_descending(self, model, sample_tracks):
        """Sort by title in descending order."""
        model.setTracks(sample_tracks)
        model.sort(0, Qt.SortOrder.DescendingOrder)
        assert model.getTrack(0).title == "Gamma Song"
        assert model.getTrack(2).title == "Alpha Song"
    
    def test_sort_by_artist(self, model, sample_tracks):
        """Sort by artist."""
        model.setTracks(sample_tracks)
        model.sort(1, Qt.SortOrder.AscendingOrder)
        assert model.getTrack(0).artist_name == "Artist A"
    
    def test_sort_by_duration(self, model, sample_tracks):
        """Sort by duration."""
        model.setTracks(sample_tracks)
        model.sort(3, Qt.SortOrder.AscendingOrder)
        assert model.getTrack(0).duration_ms == 180000
        assert model.getTrack(2).duration_ms == 300000


class TestTrackFilterProxyModel:
    """TrackFilterProxyModel Unit Tests"""

    @pytest.fixture
    def source_model(self, qapp):
        """Create a source model."""
        from ui.models.track_table_model import TrackTableModel
        from models.track import Track
        
        model = TrackTableModel()
        tracks = [
            Track(id="1", title="Rock Song", artist_name="Rock Band", 
                  album_name="Rock Album"),
            Track(id="2", title="Pop Music", artist_name="Pop Star", 
                  album_name="Pop Album"),
            Track(id="3", title="Jazz Tune", artist_name="Jazz Master", 
                  album_name="Jazz Collection"),
        ]
        model.setTracks(tracks)
        return model
    
    @pytest.fixture
    def proxy_model(self, qapp, source_model):
        """Create a proxy model."""
        from ui.models.track_table_model import TrackFilterProxyModel
        
        proxy = TrackFilterProxyModel()
        proxy.setSourceModel(source_model)
        return proxy
    
    def test_filter_empty_text(self, proxy_model):
        """Empty filter text should accept all rows."""
        proxy_model.setFilterText("")
        assert proxy_model.rowCount() == 3
    
    def test_filter_by_title(self, proxy_model):
        """Filter by title."""
        proxy_model.setFilterText("rock")
        assert proxy_model.rowCount() == 1
    
    def test_filter_by_artist(self, proxy_model):
        """Filter by artist."""
        proxy_model.setFilterText("pop star")
        assert proxy_model.rowCount() == 1
    
    def test_filter_by_album(self, proxy_model):
        """Filter by album."""
        proxy_model.setFilterText("jazz collection")
        assert proxy_model.rowCount() == 1
    
    def test_filter_case_insensitive(self, proxy_model):
        """Filtering should be case-insensitive."""
        proxy_model.setFilterText("ROCK")
        assert proxy_model.rowCount() == 1
    
    def test_filter_no_match(self, proxy_model):
        """No matching results."""
        proxy_model.setFilterText("nonexistent")
        assert proxy_model.rowCount() == 0
    
    def test_filter_partial_match(self, proxy_model):
        """Partial match."""
        proxy_model.setFilterText("song")
        assert proxy_model.rowCount() == 1  # Only "Rock Song" matches


class TestTrackListModel:
    """TrackListModel Unit Tests"""

    @pytest.fixture
    def model(self, qapp):
        """Create a TrackListModel instance."""
        from ui.models.track_list_model import TrackListModel
        return TrackListModel()
    
    @pytest.fixture
    def sample_tracks(self):
        """Create a sample track list."""
        from models.track import Track
        return [
            Track(id="1", title="First Song", artist_name="Artist A", 
                  duration_ms=180000),
            Track(id="2", title="Second Song", artist_name="Artist B", 
                  duration_ms=240000),
            Track(id="3", title="Third Song", artist_name="Artist C", 
                  duration_ms=300000),
        ]
    
    def test_row_count_empty(self, model):
        """Empty model should have 0 rows."""
        assert model.rowCount() == 0
    
    def test_row_count_with_tracks(self, model, sample_tracks):
        """Row count should be correct after setting tracks."""
        model.setTracks(sample_tracks)
        assert model.rowCount() == 3
    
    def test_data_display_format(self, model, sample_tracks):
        """DisplayRole should return a formatted string."""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "1." in text
        assert "First Song" in text
        assert "Artist A" in text
    
    def test_data_user_role(self, model, sample_tracks):
        """UserRole should return the Track object."""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        track = model.data(index, Qt.ItemDataRole.UserRole)
        assert track.id == "1"
    
    def test_highlight_track(self, model, sample_tracks):
        """Highlighted track should have a prefix."""
        model.setTracks(sample_tracks)
        model.highlightTrack("2")
        
        index = model.index(1, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "▶" in text
        
        # Other tracks should not be highlighted
        index0 = model.index(0, 0)
        text0 = model.data(index0, Qt.ItemDataRole.DisplayRole)
        assert "▶" not in text0
    
    def test_highlight_track_none(self, model, sample_tracks):
        """Highlight can be cleared."""
        model.setTracks(sample_tracks)
        model.highlightTrack("1")
        model.highlightTrack(None)
        
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "▶" not in text
    
    def test_set_show_index_true(self, model, sample_tracks):
        """Show sequence numbers."""
        model.setTracks(sample_tracks)
        model.setShowIndex(True)
        
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "1." in text
    
    def test_set_show_index_false(self, model, sample_tracks):
        """Hide sequence numbers."""
        model.setTracks(sample_tracks)
        model.setShowIndex(False)
        
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert text.startswith("First Song")
    
    def test_get_track_valid(self, model, sample_tracks):
        """getTrack should return the track at the specified row."""
        model.setTracks(sample_tracks)
        track = model.getTrack(1)
        assert track.title == "Second Song"
    
    def test_get_track_invalid(self, model, sample_tracks):
        """Invalid index should return None."""
        model.setTracks(sample_tracks)
        assert model.getTrack(-1) is None
        assert model.getTrack(100) is None
    
    def test_get_tracks_returns_copy(self, model, sample_tracks):
        """getTracks should return a copy of the list."""
        model.setTracks(sample_tracks)
        tracks = model.getTracks()
        original_len = len(tracks)
        
        # Modifying the returned list should not affect the model
        tracks.clear()
        assert model.rowCount() == original_len
    
    def test_flags_with_drag_drop(self, model, sample_tracks):
        """Should return correct flags when drag-and-drop is enabled."""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        flags = model.flags(index)
        
        assert flags & Qt.ItemFlag.ItemIsDragEnabled
        assert flags & Qt.ItemFlag.ItemIsDropEnabled
    
    def test_flags_without_drag_drop(self, qapp, sample_tracks):
        """Should not return drag-and-drop flags when disabled."""
        from ui.models.track_list_model import TrackListModel
        
        model = TrackListModel(enable_drag_drop=False)
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        flags = model.flags(index)
        
        assert not (flags & Qt.ItemFlag.ItemIsDragEnabled)
    
    def test_supported_drop_actions(self, model):
        """Should support move action."""
        assert model.supportedDropActions() == Qt.DropAction.MoveAction
    
    def test_mime_types(self, model):
        """MIME type should be correct."""
        types = model.mimeTypes()
        assert "application/x-track-indices" in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
