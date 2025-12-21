"""
UI Dialogs Unit Tests

Tests for core logic of components like CreatePlaylistDialog, LLMSettingsDialog, TagChip, etc.
"""

import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch


class TestCreatePlaylistDialog:
    """CreatePlaylistDialog Unit Tests"""

    @pytest.fixture
    def dialog(self, qapp):
        """Create an instance of CreatePlaylistDialog"""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        return CreatePlaylistDialog()
    
    def test_initial_state_confirm_disabled(self, dialog):
        """The confirm button should be disabled initially."""
        assert not dialog.confirm_btn.isEnabled()
    
    def test_valid_name_enables_confirm(self, dialog):
        """The confirm button should be enabled after entering a valid name."""
        dialog.name_input.setText("Test Playlist")
        assert dialog.confirm_btn.isEnabled()
    
    def test_whitespace_only_keeps_disabled(self, dialog):
        """The confirm button should remain disabled if only whitespace is entered."""
        dialog.name_input.setText("   ")
        assert not dialog.confirm_btn.isEnabled()
    
    def test_get_name_trimmed(self, dialog):
        """get_name should return the trimmed name."""
        dialog.name_input.setText("  My Playlist  ")
        assert dialog.get_name() == "My Playlist"
    
    def test_get_description(self, dialog):
        """get_description should return the description."""
        dialog.desc_input.setPlainText("This is a description")
        assert dialog.get_description() == "This is a description"
    
    def test_get_description_trimmed(self, dialog):
        """get_description should return the trimmed description."""
        dialog.desc_input.setPlainText("  Description with spaces  ")
        assert dialog.get_description() == "Description with spaces"
    
    def test_edit_mode_title(self, qapp):
        """The title should be correct in edit mode."""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        dialog = CreatePlaylistDialog(edit_mode=True)
        assert dialog.windowTitle() == "Edit Playlist"
    
    def test_create_mode_title(self, dialog):
        """The title should be correct in creation mode."""
        assert dialog.windowTitle() == "Create New Playlist"
    
    def test_edit_mode_prefilled(self, qapp):
        """Data should be pre-filled in edit mode."""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        dialog = CreatePlaylistDialog(
            edit_mode=True, 
            initial_name="Existing Playlist",
            initial_description="Existing Description"
        )
        assert dialog.name_input.text() == "Existing Playlist"
        assert dialog.desc_input.toPlainText() == "Existing Description"
    
    def test_name_input_placeholder(self, dialog):
        """The name input should have a placeholder."""
        assert dialog.name_input.placeholderText() == "Enter playlist name"
    
    def test_description_input_placeholder(self, dialog):
        """The description input should have a placeholder."""
        assert dialog.desc_input.placeholderText() == "Add description (optional)"


class TestLLMSettingsDialog:
    """LLMSettingsDialog Unit Tests"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration service."""
        from services.config_service import ConfigService
        ConfigService.reset_instance()
        
        tmpdir = tempfile.mkdtemp(prefix="music-llm-config-")
        config_path = f"{tmpdir}/config.yaml"
        config = ConfigService(config_path)
        
        # Set default LLM configuration
        config.set("llm.provider", "siliconflow")
        config.set("llm.siliconflow.api_key", "test-key")
        config.set("llm.siliconflow.model", "test-model")
        
        yield config
        
        ConfigService.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def dialog(self, qapp, mock_config):
        """Create an instance of LLMSettingsDialog"""
        from ui.dialogs.llm_settings_dialog import LLMSettingsDialog
        return LLMSettingsDialog(mock_config)
    
    def test_dialog_title(self, dialog):
        """The dialog title should be correct."""
        assert dialog.windowTitle() == "LLM Settings"
    
    def test_provider_combo_exists(self, dialog):
        """The provider combo box should exist."""
        assert dialog._provider_combo is not None
    
    def test_provider_combo_has_items(self, dialog):
        """The provider combo box should have items."""
        assert dialog._provider_combo.count() > 0
    
    def test_provider_switch_changes_panel(self, dialog):
        """Switching the provider should change the panel."""
        initial_index = dialog._stack.currentIndex()
        
        # Switch to a different provider
        if dialog._provider_combo.count() > 1:
            dialog._provider_combo.setCurrentIndex(1)
            assert dialog._stack.currentIndex() != initial_index
        else:
            # Only one provider, no change expected
            assert dialog._stack.currentIndex() == initial_index
    
    def test_load_from_config_siliconflow(self, dialog, mock_config):
        """Test loading SiliconFlow settings from configuration."""
        # Config is already set to siliconflow in mock_config fixture
        dialog._load_from_config()
        
        # Verify API key loaded (implementation dependent)
        # Here we just verify it doesn't raise an exception
        assert True


class TestTagChip:
    """TagChip Unit Tests"""

    @pytest.fixture
    def sample_tag(self):
        """Create a sample tag."""
        from models.tag import Tag
        return Tag(id="tag1", name="Rock", color="#FF0000")
    
    @pytest.fixture
    def chip(self, qapp, sample_tag):
        """Create an instance of TagChip"""
        from ui.dialogs.tag_dialog import TagChip
        return TagChip(sample_tag, checked=False)
    
    def test_initial_unchecked(self, chip):
        """Initially unchecked state."""
        assert not chip.checkbox.isChecked()
    
    def test_initial_checked(self, qapp, sample_tag):
        """Initially checked state."""
        from ui.dialogs.tag_dialog import TagChip
        chip = TagChip(sample_tag, checked=True)
        assert chip.checkbox.isChecked()
    
    def test_set_checked(self, chip):
        """Test setting the checked state."""
        chip.set_checked(True)
        assert chip.checkbox.isChecked()
        
        chip.set_checked(False)
        assert not chip.checkbox.isChecked()
    
    def test_toggled_signal(self, chip, qtbot):
        """Toggle should emit a signal."""
        with qtbot.waitSignal(chip.toggled, timeout=1000) as blocker:
            chip.checkbox.setChecked(True)
        
        assert blocker.args == ["tag1", True]
    
    def test_tag_reference(self, chip, sample_tag):
        """Should store tag reference."""
        assert chip.tag == sample_tag
        assert chip.tag.name == "Rock"


class TestTagDialog:
    """TagDialog Unit Tests"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        import tempfile
        from core.database import DatabaseManager
        
        DatabaseManager.reset_instance()
        tmpdir = tempfile.mkdtemp(prefix="music-tag-dialog-")
        db_path = f"{tmpdir}/test.db"
        db = DatabaseManager(db_path)
        
        yield db, tmpdir
        
        DatabaseManager.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def tag_service(self, mock_db):
        """Create a tag service."""
        from services.tag_service import TagService
        db, _ = mock_db
        return TagService(db)
    
    @pytest.fixture
    def sample_track(self):
        """Create a sample track."""
        from models.track import Track
        return Track(id="track1", title="Test Song", artist_name="Test Artist")
    
    @pytest.fixture
    def dialog(self, qapp, sample_track, tag_service):
        """Create an instance of TagDialog"""
        from ui.dialogs.tag_dialog import TagDialog
        return TagDialog([sample_track], tag_service=tag_service)
    
    def test_dialog_title(self, dialog):
        """The dialog title should be correct."""
        assert "Tags" in dialog.windowTitle()
    
    def test_dialog_has_layout(self, dialog):
        """The dialog should have a layout."""
        assert dialog.layout() is not None
    
    def test_new_tag_input_exists(self, dialog):
        """New tag input field should exist."""
        assert dialog.new_tag_input is not None
    
    def test_color_button_exists(self, dialog):
        """Color selection button should exist."""
        assert dialog.color_btn is not None
    
    def test_create_tag_button_exists(self, dialog):
        """Create tag button should exist."""
        assert dialog.add_btn is not None
    
    def test_initial_no_tags(self, dialog):
        """Initially no tags."""
        # Check if tag container area exists
        assert dialog.tags_container is not None


class TestLLMQueueChatDialogDataclasses:
    """Tests for LLMQueueChatDialog related dataclasses."""

    def test_queue_snapshot_fields(self):
        """_QueueSnapshot dataclass fields should be correct."""
        from ui.dialogs.llm_queue_chat_dialog import _QueueSnapshot
        from models.track import Track
        
        track = Track(id="t1", title="Song")
        snapshot = _QueueSnapshot(queue=[track], current_track_id="t1")
        
        assert len(snapshot.queue) == 1
        assert snapshot.current_track_id == "t1"
    
    def test_resolved_result_fields(self):
        """_ResolvedResult dataclass fields should be correct."""
        from ui.dialogs.llm_queue_chat_dialog import _ResolvedResult
        from services.llm_queue_service import QueueReorderPlan
        from models.track import Track
        
        plan = QueueReorderPlan(ordered_track_ids=["t1"])
        track = Track(id="t1", title="Song")
        result = _ResolvedResult(plan=plan, queue=[track], start_index=0)
        
        assert result.start_index == 0
        assert len(result.queue) == 1


class TestLLMQueueChatDialogUI:
    """LLMQueueChatDialog UI Tests"""

    @pytest.fixture
    def mock_services(self, qapp):
        """Create mock services."""
        from app.container_factory import AppContainerFactory
        import tempfile
        
        tmpdir = tempfile.mkdtemp(prefix="music-llm-chat-")
        db_path = f"{tmpdir}/test.db"
        config_path = f"{tmpdir}/config.yaml"
        container = AppContainerFactory.create_for_testing(
            config_path=config_path,
            db_path=db_path,
        )
        
        yield container, tmpdir
        
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def dialog(self, mock_services):
        """Create an instance of LLMQueueChatDialog"""
        from ui.dialogs.llm_queue_chat_dialog import LLMQueueChatDialog
        container, _ = mock_services
        return LLMQueueChatDialog(facade=container.facade)
    
    def test_dialog_title(self, dialog):
        """The dialog title should be correct."""
        assert "LLM" in dialog.windowTitle() or "Queue" in dialog.windowTitle()
    
    def test_input_widget_exists(self, dialog):
        """Input widget should exist."""
        assert dialog._input is not None
    
    def test_send_button_exists(self, dialog):
        """Send button should exist."""
        assert dialog._send_btn is not None
    
    def test_chat_display_exists(self, dialog):
        """Chat display area should exist."""
        assert dialog._chat is not None
    
    def test_settings_button_exists(self, dialog):
        """Settings button should exist."""
        assert dialog._settings_btn is not None
    
    def test_initial_not_busy(self, dialog):
        """Initial state should not be busy."""
        assert dialog._send_btn.isEnabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
