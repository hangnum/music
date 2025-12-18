"""
UI 模型层单元测试

测试 TrackTableModel, TrackFilterProxyModel, TrackListModel 的核心逻辑。
"""

import pytest
from PyQt6.QtCore import Qt, QModelIndex


class TestTrackTableModel:
    """TrackTableModel 单元测试"""

    @pytest.fixture
    def model(self, qapp):
        """创建 TrackTableModel 实例"""
        from ui.models.track_table_model import TrackTableModel
        return TrackTableModel()
    
    @pytest.fixture
    def sample_tracks(self):
        """创建示例曲目列表"""
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
        """空模型行数为0"""
        assert model.rowCount() == 0
    
    def test_row_count_with_tracks(self, model, sample_tracks):
        """设置曲目后行数正确"""
        model.setTracks(sample_tracks)
        assert model.rowCount() == 3
    
    def test_column_count(self, model):
        """列数固定为5"""
        assert model.columnCount() == 5
    
    def test_data_display_role_title(self, model, sample_tracks):
        """DisplayRole 返回标题"""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Alpha Song"
    
    def test_data_display_role_artist(self, model, sample_tracks):
        """DisplayRole 返回艺术家"""
        model.setTracks(sample_tracks)
        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Artist A"
    
    def test_data_display_role_album(self, model, sample_tracks):
        """DisplayRole 返回专辑"""
        model.setTracks(sample_tracks)
        index = model.index(0, 2)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Album X"
    
    def test_data_display_role_format(self, model, sample_tracks):
        """DisplayRole 返回格式"""
        model.setTracks(sample_tracks)
        index = model.index(0, 4)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "mp3"
    
    def test_data_user_role(self, model, sample_tracks):
        """UserRole 返回 Track 对象"""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        track = model.data(index, Qt.ItemDataRole.UserRole)
        assert track.id == "1"
        assert track.title == "Alpha Song"
    
    def test_data_invalid_index(self, model, sample_tracks):
        """无效索引返回 None"""
        model.setTracks(sample_tracks)
        index = model.index(100, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) is None
    
    def test_header_data(self, model):
        """表头数据正确"""
        assert model.headerData(0, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "标题"
        assert model.headerData(1, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "艺术家"
        assert model.headerData(2, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "专辑"
        assert model.headerData(3, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "时长"
        assert model.headerData(4, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) == "格式"
    
    def test_header_data_invalid_section(self, model):
        """无效列索引返回 None"""
        assert model.headerData(10, Qt.Orientation.Horizontal, 
                                Qt.ItemDataRole.DisplayRole) is None
    
    def test_set_tracks(self, model, sample_tracks):
        """setTracks 更新模型"""
        model.setTracks(sample_tracks)
        assert model.rowCount() == 3
        assert model.getTracks() == sample_tracks
    
    def test_get_tracks(self, model, sample_tracks):
        """getTracks 返回曲目列表"""
        model.setTracks(sample_tracks)
        tracks = model.getTracks()
        assert len(tracks) == 3
        assert tracks[0].title == "Alpha Song"
    
    def test_get_track_valid(self, model, sample_tracks):
        """getTrack 返回指定行的曲目"""
        model.setTracks(sample_tracks)
        track = model.getTrack(1)
        assert track.title == "Beta Song"
    
    def test_get_track_invalid_negative(self, model, sample_tracks):
        """负索引返回 None"""
        model.setTracks(sample_tracks)
        assert model.getTrack(-1) is None
    
    def test_get_track_invalid_out_of_range(self, model, sample_tracks):
        """超出范围返回 None"""
        model.setTracks(sample_tracks)
        assert model.getTrack(100) is None
    
    def test_sort_by_title_ascending(self, model, sample_tracks):
        """按标题升序排序"""
        model.setTracks(sample_tracks)
        model.sort(0, Qt.SortOrder.AscendingOrder)
        assert model.getTrack(0).title == "Alpha Song"
        assert model.getTrack(2).title == "Gamma Song"
    
    def test_sort_by_title_descending(self, model, sample_tracks):
        """按标题降序排序"""
        model.setTracks(sample_tracks)
        model.sort(0, Qt.SortOrder.DescendingOrder)
        assert model.getTrack(0).title == "Gamma Song"
        assert model.getTrack(2).title == "Alpha Song"
    
    def test_sort_by_artist(self, model, sample_tracks):
        """按艺术家排序"""
        model.setTracks(sample_tracks)
        model.sort(1, Qt.SortOrder.AscendingOrder)
        assert model.getTrack(0).artist_name == "Artist A"
    
    def test_sort_by_duration(self, model, sample_tracks):
        """按时长排序"""
        model.setTracks(sample_tracks)
        model.sort(3, Qt.SortOrder.AscendingOrder)
        assert model.getTrack(0).duration_ms == 180000
        assert model.getTrack(2).duration_ms == 300000


class TestTrackFilterProxyModel:
    """TrackFilterProxyModel 单元测试"""

    @pytest.fixture
    def source_model(self, qapp):
        """创建源模型"""
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
        """创建代理模型"""
        from ui.models.track_table_model import TrackFilterProxyModel
        
        proxy = TrackFilterProxyModel()
        proxy.setSourceModel(source_model)
        return proxy
    
    def test_filter_empty_text(self, proxy_model):
        """空过滤文本接受所有行"""
        proxy_model.setFilterText("")
        assert proxy_model.rowCount() == 3
    
    def test_filter_by_title(self, proxy_model):
        """按标题过滤"""
        proxy_model.setFilterText("rock")
        assert proxy_model.rowCount() == 1
    
    def test_filter_by_artist(self, proxy_model):
        """按艺术家过滤"""
        proxy_model.setFilterText("pop star")
        assert proxy_model.rowCount() == 1
    
    def test_filter_by_album(self, proxy_model):
        """按专辑过滤"""
        proxy_model.setFilterText("jazz collection")
        assert proxy_model.rowCount() == 1
    
    def test_filter_case_insensitive(self, proxy_model):
        """过滤不区分大小写"""
        proxy_model.setFilterText("ROCK")
        assert proxy_model.rowCount() == 1
    
    def test_filter_no_match(self, proxy_model):
        """无匹配结果"""
        proxy_model.setFilterText("nonexistent")
        assert proxy_model.rowCount() == 0
    
    def test_filter_partial_match(self, proxy_model):
        """部分匹配"""
        proxy_model.setFilterText("song")
        assert proxy_model.rowCount() == 1  # Only "Rock Song" matches


class TestTrackListModel:
    """TrackListModel 单元测试"""

    @pytest.fixture
    def model(self, qapp):
        """创建 TrackListModel 实例"""
        from ui.models.track_list_model import TrackListModel
        return TrackListModel()
    
    @pytest.fixture
    def sample_tracks(self):
        """创建示例曲目列表"""
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
        """空模型行数为0"""
        assert model.rowCount() == 0
    
    def test_row_count_with_tracks(self, model, sample_tracks):
        """设置曲目后行数正确"""
        model.setTracks(sample_tracks)
        assert model.rowCount() == 3
    
    def test_data_display_format(self, model, sample_tracks):
        """DisplayRole 返回格式化字符串"""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "1." in text
        assert "First Song" in text
        assert "Artist A" in text
    
    def test_data_user_role(self, model, sample_tracks):
        """UserRole 返回 Track 对象"""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        track = model.data(index, Qt.ItemDataRole.UserRole)
        assert track.id == "1"
    
    def test_highlight_track(self, model, sample_tracks):
        """高亮曲目添加前缀"""
        model.setTracks(sample_tracks)
        model.highlightTrack("2")
        
        index = model.index(1, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "▶" in text
        
        # 其他曲目不高亮
        index0 = model.index(0, 0)
        text0 = model.data(index0, Qt.ItemDataRole.DisplayRole)
        assert "▶" not in text0
    
    def test_highlight_track_none(self, model, sample_tracks):
        """取消高亮"""
        model.setTracks(sample_tracks)
        model.highlightTrack("1")
        model.highlightTrack(None)
        
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "▶" not in text
    
    def test_set_show_index_true(self, model, sample_tracks):
        """显示序号"""
        model.setTracks(sample_tracks)
        model.setShowIndex(True)
        
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "1." in text
    
    def test_set_show_index_false(self, model, sample_tracks):
        """不显示序号"""
        model.setTracks(sample_tracks)
        model.setShowIndex(False)
        
        index = model.index(0, 0)
        text = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert text.startswith("First Song")
    
    def test_get_track_valid(self, model, sample_tracks):
        """getTrack 返回指定行的曲目"""
        model.setTracks(sample_tracks)
        track = model.getTrack(1)
        assert track.title == "Second Song"
    
    def test_get_track_invalid(self, model, sample_tracks):
        """无效索引返回 None"""
        model.setTracks(sample_tracks)
        assert model.getTrack(-1) is None
        assert model.getTrack(100) is None
    
    def test_get_tracks_returns_copy(self, model, sample_tracks):
        """getTracks 返回列表副本"""
        model.setTracks(sample_tracks)
        tracks = model.getTracks()
        original_len = len(tracks)
        
        # 修改返回的列表不影响模型
        tracks.clear()
        assert model.rowCount() == original_len
    
    def test_flags_with_drag_drop(self, model, sample_tracks):
        """启用拖放时返回正确标志"""
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        flags = model.flags(index)
        
        assert flags & Qt.ItemFlag.ItemIsDragEnabled
        assert flags & Qt.ItemFlag.ItemIsDropEnabled
    
    def test_flags_without_drag_drop(self, qapp, sample_tracks):
        """禁用拖放时不返回拖放标志"""
        from ui.models.track_list_model import TrackListModel
        
        model = TrackListModel(enable_drag_drop=False)
        model.setTracks(sample_tracks)
        index = model.index(0, 0)
        flags = model.flags(index)
        
        assert not (flags & Qt.ItemFlag.ItemIsDragEnabled)
    
    def test_supported_drop_actions(self, model):
        """支持移动操作"""
        assert model.supportedDropActions() == Qt.DropAction.MoveAction
    
    def test_mime_types(self, model):
        """MIME 类型正确"""
        types = model.mimeTypes()
        assert "application/x-track-indices" in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
