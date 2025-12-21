"""
UI Components Unit Tests

Test core logic of PlayerControls, SystemTray and other components.
"""

import pytest
from unittest.mock import MagicMock


    @pytest.fixture
    def player_controls(self, qapp):
        """Create PlayerControls instance"""
        from ui.widgets.player_controls import PlayerControls
        from services.player_service import PlayerService
        
        # Create mock engine
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 1.0
        
        # Create PlayerService
        player_service = PlayerService(audio_engine=mock_engine)
        
        return PlayerControls(player_service)
    
    def test_format_time_zero(self, player_controls):
        """Format 0 milliseconds"""
        result = player_controls._format_time(0)
        assert result == "0:00"
    
    def test_format_time_one_minute(self, player_controls):
        """Format 1 minute."""
        result = player_controls._format_time(60000)
        assert result == "1:00"
    
    def test_format_time_with_seconds(self, player_controls):
        """Format minutes and seconds."""
        result = player_controls._format_time(90000)
        assert result == "1:30"
    
    def test_format_time_single_digit_seconds(self, player_controls):
        """Pad single-digit seconds with zero."""
        result = player_controls._format_time(65000)
        assert result == "1:05"
    
    def test_format_time_ten_minutes(self, player_controls):
        """Format 10 minutes."""
        result = player_controls._format_time(600000)
        assert result == "10:00"
    
    def test_format_time_long_duration(self, player_controls):
        """Format longer duration."""
        result = player_controls._format_time(3661000)  # 61 minutes 1 second
        assert result == "61:01"


class TestPlayerControlsInitialState:
    """Tests for the initial state of PlayerControls."""

    @pytest.fixture
    def player_controls(self, qapp):
        """Create a PlayerControls instance."""
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
        """The initial track label should be empty or a default string."""
        # No track playing initially
        text = player_controls.title_label.text()
        assert text in ("", "Not Playing", "-", "No track playing")
    
    def test_initial_artist_label_empty(self, player_controls):
        """The initial artist label should be empty or a default string."""
        text = player_controls.artist_label.text()
        assert text in ("", "-", " ", "Apple Music")
    
    def test_progress_slider_exists(self, player_controls):
        """The progress bar should exist."""
        assert player_controls.progress_slider is not None
    
    def test_volume_slider_exists(self, player_controls):
        """The volume slider should exist."""
        assert player_controls.volume_slider is not None
    
    def test_play_button_exists(self, player_controls):
        """The play button should exist."""
        assert player_controls.play_btn is not None


class TestPlayerControlsButtons:
    """Tests for button interactions in PlayerControls."""

    @pytest.fixture
    def player_controls(self, qapp):
        """Create a PlayerControls instance."""
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
        """The previous track button should exist."""
        assert player_controls.prev_btn is not None
    
    def test_next_button_exists(self, player_controls):
        """The next track button should exist."""
        assert player_controls.next_btn is not None
    
    def test_shuffle_button_exists(self, player_controls):
        """The shuffle button should exist."""
        assert player_controls.shuffle_btn is not None
    
    def test_repeat_button_exists(self, player_controls):
        """The repeat button should exist."""
        assert player_controls.repeat_btn is not None


class TestSystemTray:
    """SystemTray Unit Tests"""

    @pytest.fixture
    def system_tray_class(self, qapp):
        """Get the SystemTray class."""
        from ui.widgets.system_tray import SystemTray
        return SystemTray
    
    def test_can_import(self, system_tray_class):
        """SystemTray should be importable."""
        assert system_tray_class is not None


class TestLibraryWidget:
    """LibraryWidget Unit Tests"""

    @pytest.fixture
    def container(self, qapp):
        """Create a test container."""
        import tempfile
        import shutil
        from app.container_factory import AppContainerFactory
        
        tmpdir = tempfile.mkdtemp(prefix="music-library-widget-")
        db_path = f"{tmpdir}/test.db"
        config_path = f"{tmpdir}/config.yaml"
        
        container = AppContainerFactory.create_for_testing(
            config_path=config_path,
            db_path=db_path,
        )
        
        yield container, tmpdir
        
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def widget(self, container):
        """Create a LibraryWidget instance."""
        from ui.widgets.library_widget import LibraryWidget
        
        cont, _ = container
        widget = LibraryWidget(facade=cont.facade)
        yield widget
    
    def test_table_view_exists(self, widget):
        """The table view should exist."""
        assert widget.table is not None
    
    def test_search_input_exists(self, widget):
        """The search input box should exist."""
        assert widget.search_input is not None
    
    def test_stats_label_exists(self, widget):
        """The statistics label should exist."""
        assert widget.stats_label is not None
    
    def test_search_placeholder(self, widget):
        """The search box should have a placeholder."""
        placeholder = widget.search_input.placeholderText()
        assert len(placeholder) > 0
    
    def test_update_stats_empty(self, widget):
        """Test updating statistics for an empty library."""
        widget._update_stats([])
        assert "0" in widget.stats_label.text()


class TestPlaylistManagerWidget:

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
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
        """Create a playlist service."""
        from services.playlist_service import PlaylistService
        return PlaylistService(mock_db)
    
    @pytest.fixture
    def widget(self, qapp, playlist_service):
        """Create a PlaylistManagerWidget instance."""
        from ui.widgets.playlist_manager_widget import PlaylistManagerWidget
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        widget = PlaylistManagerWidget(playlist_service)
        yield widget
        EventBus.reset_instance()
    
    def test_initial_empty_list(self, widget):
        """The list should be empty initially."""
        assert widget.list_widget.count() == 0
    
    def test_info_label_shows_count(self, widget):
        """The info label should display the correct count."""
        assert "0 playlists" in widget.info_label.text()
    
    def test_add_button_exists(self, widget):
        """The add button should exist."""
        assert widget.add_btn is not None
    
    def test_list_widget_exists(self, widget):
        """The list control should exist."""
        assert widget.list_widget is not None
    
    def test_refresh_with_playlists(self, widget, playlist_service):
        """New playlists should be displayed after refresh."""
        # Create playlist
        playlist_service.create("Test Playlist", "Description")
        
        # Refresh
        widget.refresh()
        
        assert widget.list_widget.count() == 1
        assert "1 playlists" in widget.info_label.text()
    
    def test_get_selected_playlist_none(self, widget):
        """Should return None when nothing is selected."""
        assert widget.get_selected_playlist() is None
    
    def test_playlist_selected_signal(self, widget, playlist_service, qtbot):
        """Double-clicking a playlist should emit a signal."""
        # Create playlist
        playlist = playlist_service.create("Test Playlist")
        widget.refresh()
        
        # Simulate double-click
        with qtbot.waitSignal(widget.playlist_selected, timeout=1000) as blocker:
            item = widget.list_widget.item(0)
            widget.list_widget.itemDoubleClicked.emit(item)
        
        assert blocker.args[0].id == playlist.id


class TestPlaylistDetailWidget:
    """PlaylistDetailWidget Unit Tests"""

    @pytest.fixture  
    def mock_db(self):
        """Create a mock database."""
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
        """Create services."""
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
        """Create a PlaylistDetailWidget instance."""
        from ui.widgets.playlist_detail_widget import PlaylistDetailWidget
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        playlist_service, player_service = services
        widget = PlaylistDetailWidget(playlist_service, player_service)
        yield widget
        EventBus.reset_instance()
    
    def test_initial_state(self, widget):
        """Initial state should be correct."""
        assert widget.title_label.text() == "Playlist Details"
        assert widget.info_label.text() == "0 tracks"
    
    def test_back_button_exists(self, widget):
        """The back button should exist."""
        assert widget.back_btn is not None
    
    def test_play_all_button_exists(self, widget):
        """The play all button should exist."""
        assert widget.play_all_btn is not None
    
    def test_list_view_exists(self, widget):
        """The list view should exist."""
        assert widget.list_view is not None
    
    def test_set_playlist_updates_title(self, widget, services):
        """Setting a playlist should update the title."""
        playlist_service, _ = services
        playlist = playlist_service.create("My Awesome Playlist", "A great playlist")
        
        widget.set_playlist(playlist)
        
        assert widget.title_label.text() == "My Awesome Playlist"
    
    def test_back_requested_signal(self, widget, qtbot):
        """Clicking the back button should emit a signal."""
        with qtbot.waitSignal(widget.back_requested, timeout=1000):
            widget.back_btn.click()


class TestPlaylistWidget:
    """PlaylistWidget Unit Tests"""

    @pytest.fixture
    def widget(self, qapp):
        """Create a PlaylistWidget instance."""
        from ui.widgets.playlist_widget import PlaylistWidget
        from services.player_service import PlayerService
        from core.event_bus import EventBus
        
        EventBus.reset_instance()
        event_bus = EventBus()
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        player_service = PlayerService(audio_engine=mock_engine)
        widget = PlaylistWidget(player_service, event_bus)
        yield widget
        EventBus.reset_instance()
    
    def test_initial_empty_queue(self, widget):
        """The queue should be empty initially."""
        widget.update_list()
        assert "0 tracks" in widget.info_label.text()
    
    def test_list_view_exists(self, widget):
        """The list view should exist."""
        assert widget.list_view is not None
    
    def test_clear_button_exists(self, widget):
        """The clear button should exist."""
        assert widget.clear_btn is not None
    
    def test_llm_button_exists(self, widget):
        """The LLM button should exist."""
        assert widget.llm_btn is not None
    
    def test_llm_chat_requested_signal(self, widget, qtbot):
        """Clicking the LLM button should emit a signal."""
        with qtbot.waitSignal(widget.llm_chat_requested, timeout=1000):
            widget.llm_btn.click()


class TestMiniPlayer:
    """MiniPlayer Unit Tests"""

    @pytest.fixture
    def mini_player(self, qapp):
        """Create a MiniPlayer instance."""
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
        """The window title should be correct."""
        assert mini_player.windowTitle() == "Mini Player"
    
    def test_play_button_exists(self, mini_player):
        """The play button should exist."""
        assert mini_player.play_btn is not None
    
    def test_prev_button_exists(self, mini_player):
        """The previous track button should exist."""
        assert mini_player.prev_btn is not None
    
    def test_next_button_exists(self, mini_player):
        """The next track button should exist."""
        assert mini_player.next_btn is not None
    
    def test_progress_slider_exists(self, mini_player):
        """The progress slider should exist."""
        assert mini_player.progress_slider is not None
    
    def test_title_label_exists(self, mini_player):
        """The title label should exist."""
        assert mini_player.title_label is not None
    
    def test_expand_requested_signal(self, mini_player, qtbot):
        """Clicking the expand button should emit a signal."""
        with qtbot.waitSignal(mini_player.expand_requested, timeout=1000):
            mini_player.expand_btn.click()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
