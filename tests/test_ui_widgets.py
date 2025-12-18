"""
UI 组件单元测试

测试 PlayerControls, SystemTray 等组件的核心逻辑。
"""

import pytest
from unittest.mock import MagicMock


class TestPlayerControlsFormatTime:
    """PlayerControls._format_time 单元测试"""

    @pytest.fixture
    def player_controls(self, qapp):
        """创建 PlayerControls 实例"""
        from ui.widgets.player_controls import PlayerControls
        from services.player_service import PlayerService
        
        # 创建模拟引擎
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 1.0
        
        # 创建 PlayerService
        player_service = PlayerService(audio_engine=mock_engine)
        
        return PlayerControls(player_service)
    
    def test_format_time_zero(self, player_controls):
        """格式化 0 毫秒"""
        result = player_controls._format_time(0)
        assert result == "0:00"
    
    def test_format_time_one_minute(self, player_controls):
        """格式化 1 分钟"""
        result = player_controls._format_time(60000)
        assert result == "1:00"
    
    def test_format_time_with_seconds(self, player_controls):
        """格式化分秒"""
        result = player_controls._format_time(90000)
        assert result == "1:30"
    
    def test_format_time_single_digit_seconds(self, player_controls):
        """单位数秒补零"""
        result = player_controls._format_time(65000)
        assert result == "1:05"
    
    def test_format_time_ten_minutes(self, player_controls):
        """格式化 10 分钟"""
        result = player_controls._format_time(600000)
        assert result == "10:00"
    
    def test_format_time_long_duration(self, player_controls):
        """格式化较长时间"""
        result = player_controls._format_time(3661000)  # 61 分 1 秒
        assert result == "61:01"


class TestPlayerControlsInitialState:
    """PlayerControls 初始状态测试"""

    @pytest.fixture
    def player_controls(self, qapp):
        """创建 PlayerControls 实例"""
        from ui.widgets.player_controls import PlayerControls
        from services.player_service import PlayerService
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        player_service = PlayerService(audio_engine=mock_engine)
        
        controls = PlayerControls(player_service)
        yield controls
        
        controls.cleanup()
        EventBus.reset_instance()
    
    def test_initial_track_label_empty(self, player_controls):
        """初始曲目标签为空或默认"""
        # 初始没有播放曲目
        text = player_controls.title_label.text()
        assert text in ("", "未播放", "-", "未在播放")
    
    def test_initial_artist_label_empty(self, player_controls):
        """初始艺术家标签为空或默认"""
        text = player_controls.artist_label.text()
        assert text in ("", "-", " ", "Apple Music")
    
    def test_progress_slider_exists(self, player_controls):
        """进度条存在"""
        assert player_controls.progress_slider is not None
    
    def test_volume_slider_exists(self, player_controls):
        """音量滑块存在"""
        assert player_controls.volume_slider is not None
    
    def test_play_button_exists(self, player_controls):
        """播放按钮存在"""
        assert player_controls.play_btn is not None


class TestPlayerControlsButtons:
    """PlayerControls 按钮交互测试"""

    @pytest.fixture
    def player_controls(self, qapp):
        """创建 PlayerControls 实例"""
        from ui.widgets.player_controls import PlayerControls
        from services.player_service import PlayerService
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        player_service = PlayerService(audio_engine=mock_engine)
        
        controls = PlayerControls(player_service)
        yield controls
        
        controls.cleanup()
        EventBus.reset_instance()
    
    def test_prev_button_exists(self, player_controls):
        """上一曲按钮存在"""
        assert player_controls.prev_btn is not None
    
    def test_next_button_exists(self, player_controls):
        """下一曲按钮存在"""
        assert player_controls.next_btn is not None
    
    def test_shuffle_button_exists(self, player_controls):
        """随机按钮存在"""
        assert player_controls.shuffle_btn is not None
    
    def test_repeat_button_exists(self, player_controls):
        """循环按钮存在"""
        assert player_controls.repeat_btn is not None


class TestSystemTray:
    """SystemTray 单元测试"""

    @pytest.fixture
    def system_tray_class(self, qapp):
        """获取 SystemTray 类"""
        from ui.widgets.system_tray import SystemTray
        return SystemTray
    
    def test_can_import(self, system_tray_class):
        """能够导入 SystemTray"""
        assert system_tray_class is not None


class TestLibraryWidget:
    """LibraryWidget 单元测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库"""
        import tempfile
        import shutil
        from core.database import DatabaseManager
        
        DatabaseManager.reset_instance()
        tmpdir = tempfile.mkdtemp(prefix="music-library-widget-")
        db_path = f"{tmpdir}/test.db"
        db = DatabaseManager(db_path)
        
        yield db, tmpdir
        
        DatabaseManager.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def services(self, mock_db):
        """创建服务"""
        from services.library_service import LibraryService
        from services.player_service import PlayerService
        from services.playlist_service import PlaylistService
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        db, _ = mock_db
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        library = LibraryService(db)
        player = PlayerService(audio_engine=mock_engine)
        playlist = PlaylistService(db)
        
        return library, player, playlist
    
    @pytest.fixture
    def widget(self, qapp, services):
        """创建 LibraryWidget 实例"""
        from ui.widgets.library_widget import LibraryWidget
        from core.event_bus import EventBus
        
        library, player, playlist = services
        widget = LibraryWidget(library, player, playlist)
        yield widget
        EventBus.reset_instance()
    
    def test_table_view_exists(self, widget):
        """表格视图存在"""
        assert widget.table is not None
    
    def test_search_input_exists(self, widget):
        """搜索框存在"""
        assert widget.search_input is not None
    
    def test_stats_label_exists(self, widget):
        """统计标签存在"""
        assert widget.stats_label is not None
    
    def test_search_placeholder(self, widget):
        """搜索框有占位符"""
        placeholder = widget.search_input.placeholderText()
        assert len(placeholder) > 0
    
    def test_update_stats_empty(self, widget):
        """更新空库统计"""
        widget._update_stats([])
        assert "0" in widget.stats_label.text()


class TestPlaylistManagerWidget:

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库"""
        import tempfile
        import shutil
        from core.database import DatabaseManager
        
        DatabaseManager.reset_instance()
        tmpdir = tempfile.mkdtemp(prefix="music-playlist-widget-")
        db_path = f"{tmpdir}/test.db"
        db = DatabaseManager(db_path)
        
        yield db
        
        DatabaseManager.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def playlist_service(self, mock_db):
        """创建歌单服务"""
        from services.playlist_service import PlaylistService
        return PlaylistService(mock_db)
    
    @pytest.fixture
    def widget(self, qapp, playlist_service):
        """创建 PlaylistManagerWidget 实例"""
        from ui.widgets.playlist_manager_widget import PlaylistManagerWidget
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        widget = PlaylistManagerWidget(playlist_service)
        yield widget
        EventBus.reset_instance()
    
    def test_initial_empty_list(self, widget):
        """初始化时列表为空"""
        assert widget.list_widget.count() == 0
    
    def test_info_label_shows_count(self, widget):
        """信息标签显示正确数量"""
        assert "0 个歌单" in widget.info_label.text()
    
    def test_add_button_exists(self, widget):
        """添加按钮存在"""
        assert widget.add_btn is not None
    
    def test_list_widget_exists(self, widget):
        """列表控件存在"""
        assert widget.list_widget is not None
    
    def test_refresh_with_playlists(self, widget, playlist_service):
        """刷新后显示新建的歌单"""
        # 创建歌单
        playlist_service.create("Test Playlist", "Description")
        
        # 刷新
        widget.refresh()
        
        assert widget.list_widget.count() == 1
        assert "1 个歌单" in widget.info_label.text()
    
    def test_get_selected_playlist_none(self, widget):
        """无选中时返回 None"""
        assert widget.get_selected_playlist() is None
    
    def test_playlist_selected_signal(self, widget, playlist_service, qtbot):
        """双击歌单时发出信号"""
        # 创建歌单
        playlist = playlist_service.create("Test Playlist")
        widget.refresh()
        
        # 模拟双击
        with qtbot.waitSignal(widget.playlist_selected, timeout=1000) as blocker:
            item = widget.list_widget.item(0)
            widget.list_widget.itemDoubleClicked.emit(item)
        
        assert blocker.args[0].id == playlist.id


class TestPlaylistDetailWidget:
    """PlaylistDetailWidget 单元测试"""

    @pytest.fixture  
    def mock_db(self):
        """创建模拟数据库"""
        import tempfile
        import shutil
        from core.database import DatabaseManager
        
        DatabaseManager.reset_instance()
        tmpdir = tempfile.mkdtemp(prefix="music-detail-widget-")
        db_path = f"{tmpdir}/test.db"
        db = DatabaseManager(db_path)
        
        yield db
        
        DatabaseManager.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def services(self, mock_db):
        """创建服务"""
        from services.playlist_service import PlaylistService
        from services.player_service import PlayerService
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        playlist_service = PlaylistService(mock_db)
        player_service = PlayerService(audio_engine=mock_engine)
        
        return playlist_service, player_service
    
    @pytest.fixture
    def widget(self, qapp, services):
        """创建 PlaylistDetailWidget 实例"""
        from ui.widgets.playlist_detail_widget import PlaylistDetailWidget
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        playlist_service, player_service = services
        widget = PlaylistDetailWidget(playlist_service, player_service)
        yield widget
        EventBus.reset_instance()
    
    def test_initial_state(self, widget):
        """初始状态正确"""
        assert widget.title_label.text() == "歌单详情"
        assert widget.info_label.text() == "0 首曲目"
    
    def test_back_button_exists(self, widget):
        """返回按钮存在"""
        assert widget.back_btn is not None
    
    def test_play_all_button_exists(self, widget):
        """播放全部按钮存在"""
        assert widget.play_all_btn is not None
    
    def test_list_view_exists(self, widget):
        """列表视图存在"""
        assert widget.list_view is not None
    
    def test_set_playlist_updates_title(self, widget, services):
        """设置歌单更新标题"""
        playlist_service, _ = services
        playlist = playlist_service.create("My Awesome Playlist", "A great playlist")
        
        widget.set_playlist(playlist)
        
        assert widget.title_label.text() == "My Awesome Playlist"
    
    def test_back_requested_signal(self, widget, qtbot):
        """点击返回按钮发出信号"""
        with qtbot.waitSignal(widget.back_requested, timeout=1000):
            widget.back_btn.click()


class TestPlaylistWidget:
    """PlaylistWidget 单元测试"""

    @pytest.fixture
    def widget(self, qapp):
        """创建 PlaylistWidget 实例"""
        from ui.widgets.playlist_widget import PlaylistWidget
        from services.player_service import PlayerService
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        player_service = PlayerService(audio_engine=mock_engine)
        widget = PlaylistWidget(player_service)
        yield widget
        EventBus.reset_instance()
    
    def test_initial_empty_queue(self, widget):
        """初始队列为空"""
        widget.update_list()
        assert "0 首曲目" in widget.info_label.text()
    
    def test_list_view_exists(self, widget):
        """列表视图存在"""
        assert widget.list_view is not None
    
    def test_clear_button_exists(self, widget):
        """清空按钮存在"""
        assert widget.clear_btn is not None
    
    def test_llm_button_exists(self, widget):
        """LLM 按钮存在"""
        assert widget.llm_btn is not None
    
    def test_llm_chat_requested_signal(self, widget, qtbot):
        """点击 LLM 按钮发出信号"""
        with qtbot.waitSignal(widget.llm_chat_requested, timeout=1000):
            widget.llm_btn.click()


class TestMiniPlayer:
    """MiniPlayer 单元测试"""

    @pytest.fixture
    def mini_player(self, qapp):
        """创建 MiniPlayer 实例"""
        from ui.mini_player import MiniPlayer
        from services.player_service import PlayerService
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        player_service = PlayerService(audio_engine=mock_engine)
        player = MiniPlayer(player_service)
        yield player
        EventBus.reset_instance()
    
    def test_window_title(self, mini_player):
        """窗口标题正确"""
        assert mini_player.windowTitle() == "Mini Player"
    
    def test_play_button_exists(self, mini_player):
        """播放按钮存在"""
        assert mini_player.play_btn is not None
    
    def test_prev_button_exists(self, mini_player):
        """上一曲按钮存在"""
        assert mini_player.prev_btn is not None
    
    def test_next_button_exists(self, mini_player):
        """下一曲按钮存在"""
        assert mini_player.next_btn is not None
    
    def test_progress_slider_exists(self, mini_player):
        """进度条存在"""
        assert mini_player.progress_slider is not None
    
    def test_title_label_exists(self, mini_player):
        """标题标签存在"""
        assert mini_player.title_label is not None
    
    def test_expand_requested_signal(self, mini_player, qtbot):
        """点击展开按钮发出信号"""
        with qtbot.waitSignal(mini_player.expand_requested, timeout=1000):
            mini_player.expand_btn.click()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
