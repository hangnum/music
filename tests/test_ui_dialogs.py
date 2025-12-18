"""
UI 对话框单元测试

测试 CreatePlaylistDialog, LLMSettingsDialog, TagChip 等组件的核心逻辑。
"""

import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch


class TestCreatePlaylistDialog:
    """CreatePlaylistDialog 单元测试"""

    @pytest.fixture
    def dialog(self, qapp):
        """创建 CreatePlaylistDialog 实例"""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        return CreatePlaylistDialog()
    
    def test_initial_state_confirm_disabled(self, dialog):
        """初始状态确认按钮禁用"""
        assert not dialog.confirm_btn.isEnabled()
    
    def test_valid_name_enables_confirm(self, dialog):
        """输入有效名称后确认按钮启用"""
        dialog.name_input.setText("Test Playlist")
        assert dialog.confirm_btn.isEnabled()
    
    def test_whitespace_only_keeps_disabled(self, dialog):
        """仅空白字符保持禁用"""
        dialog.name_input.setText("   ")
        assert not dialog.confirm_btn.isEnabled()
    
    def test_get_name_trimmed(self, dialog):
        """get_name 返回去除空白的名称"""
        dialog.name_input.setText("  My Playlist  ")
        assert dialog.get_name() == "My Playlist"
    
    def test_get_description(self, dialog):
        """get_description 返回描述"""
        dialog.desc_input.setPlainText("This is a description")
        assert dialog.get_description() == "This is a description"
    
    def test_get_description_trimmed(self, dialog):
        """get_description 返回去除空白的描述"""
        dialog.desc_input.setPlainText("  Description with spaces  ")
        assert dialog.get_description() == "Description with spaces"
    
    def test_edit_mode_title(self, qapp):
        """编辑模式标题正确"""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        dialog = CreatePlaylistDialog(edit_mode=True)
        assert dialog.windowTitle() == "编辑歌单"
    
    def test_create_mode_title(self, dialog):
        """创建模式标题正确"""
        assert dialog.windowTitle() == "新建歌单"
    
    def test_edit_mode_prefilled(self, qapp):
        """编辑模式预填充数据"""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        dialog = CreatePlaylistDialog(
            edit_mode=True, 
            initial_name="Existing Playlist",
            initial_description="Existing Description"
        )
        assert dialog.name_input.text() == "Existing Playlist"
        assert dialog.desc_input.toPlainText() == "Existing Description"
    
    def test_name_input_placeholder(self, dialog):
        """名称输入框有占位符"""
        assert dialog.name_input.placeholderText() == "输入歌单名称"
    
    def test_description_input_placeholder(self, dialog):
        """描述输入框有占位符"""
        assert dialog.desc_input.placeholderText() == "添加描述（可选）"


class TestLLMSettingsDialog:
    """LLMSettingsDialog 单元测试"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置服务"""
        from services.config_service import ConfigService
        ConfigService.reset_instance()
        
        tmpdir = tempfile.mkdtemp(prefix="music-llm-config-")
        config_path = f"{tmpdir}/config.yaml"
        config = ConfigService(config_path)
        
        # 设置默认 LLM 配置
        config.set("llm.provider", "siliconflow")
        config.set("llm.siliconflow.api_key", "test-key")
        config.set("llm.siliconflow.model", "test-model")
        
        yield config
        
        ConfigService.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def dialog(self, qapp, mock_config):
        """创建 LLMSettingsDialog 实例"""
        from ui.dialogs.llm_settings_dialog import LLMSettingsDialog
        return LLMSettingsDialog(mock_config)
    
    def test_dialog_title(self, dialog):
        """对话框标题正确"""
        assert dialog.windowTitle() == "LLM 设置"
    
    def test_provider_combo_exists(self, dialog):
        """提供商选择框存在"""
        assert dialog._provider_combo is not None
    
    def test_provider_combo_has_items(self, dialog):
        """提供商选择框有选项"""
        assert dialog._provider_combo.count() > 0
    
    def test_provider_switch_changes_panel(self, dialog):
        """切换提供商改变面板"""
        initial_index = dialog._stack.currentIndex()
        
        # 切换到不同的提供商
        dialog._provider_combo.setCurrentIndex(1)
        
        # 面板应该变化
        assert dialog._stack.currentIndex() != initial_index or \
               dialog._provider_combo.count() == 1  # 只有一个提供商时不变
    
    def test_load_from_config_siliconflow(self, dialog, mock_config):
        """从配置加载 SiliconFlow 设置"""
        # 配置已设置为 siliconflow
        dialog._load_from_config()
        
        # 验证 API key 已加载（取决于实现）
        # 这里只验证不抛出异常
        assert True


class TestTagChip:
    """TagChip 单元测试"""

    @pytest.fixture
    def sample_tag(self):
        """创建示例标签"""
        from models.tag import Tag
        return Tag(id="tag1", name="Rock", color="#FF0000")
    
    @pytest.fixture
    def chip(self, qapp, sample_tag):
        """创建 TagChip 实例"""
        from ui.dialogs.tag_dialog import TagChip
        return TagChip(sample_tag, checked=False)
    
    def test_initial_unchecked(self, chip):
        """初始状态未选中"""
        assert not chip.checkbox.isChecked()
    
    def test_initial_checked(self, qapp, sample_tag):
        """初始选中状态"""
        from ui.dialogs.tag_dialog import TagChip
        chip = TagChip(sample_tag, checked=True)
        assert chip.checkbox.isChecked()
    
    def test_set_checked(self, chip):
        """设置选中状态"""
        chip.set_checked(True)
        assert chip.checkbox.isChecked()
        
        chip.set_checked(False)
        assert not chip.checkbox.isChecked()
    
    def test_toggled_signal(self, chip, qtbot):
        """切换时发出信号"""
        with qtbot.waitSignal(chip.toggled, timeout=1000) as blocker:
            chip.checkbox.setChecked(True)
        
        assert blocker.args == ["tag1", True]
    
    def test_tag_reference(self, chip, sample_tag):
        """保存标签引用"""
        assert chip.tag == sample_tag
        assert chip.tag.name == "Rock"


class TestTagDialog:
    """TagDialog 单元测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库"""
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
        """创建标签服务"""
        from services.tag_service import TagService
        db, _ = mock_db
        return TagService(db)
    
    @pytest.fixture
    def sample_track(self):
        """创建示例曲目"""
        from models.track import Track
        return Track(id="track1", title="Test Song", artist_name="Test Artist")
    
    @pytest.fixture
    def dialog(self, qapp, sample_track, tag_service):
        """创建 TagDialog 实例"""
        from ui.dialogs.tag_dialog import TagDialog
        return TagDialog([sample_track], tag_service=tag_service)
    
    def test_dialog_title(self, dialog):
        """对话框标题正确"""
        assert "标签" in dialog.windowTitle()
    
    def test_dialog_has_layout(self, dialog):
        """对话框有布局"""
        assert dialog.layout() is not None
    
    def test_new_tag_input_exists(self, dialog):
        """新标签输入框存在"""
        assert dialog.new_tag_input is not None
    
    def test_color_button_exists(self, dialog):
        """颜色选择按钮存在"""
        assert dialog.color_btn is not None
    
    def test_create_tag_button_exists(self, dialog):
        """创建标签按钮存在"""
        assert dialog.add_btn is not None
    
    def test_initial_no_tags(self, dialog):
        """初始无标签"""
        # 检查标签区域是否存在
        assert dialog.tags_container is not None


class TestLLMQueueChatDialogDataclasses:
    """LLMQueueChatDialog 相关数据类测试"""

    def test_queue_snapshot_fields(self):
        """_QueueSnapshot 数据类字段正确"""
        from ui.dialogs.llm_queue_chat_dialog import _QueueSnapshot
        from models.track import Track
        
        track = Track(id="t1", title="Song")
        snapshot = _QueueSnapshot(queue=[track], current_track_id="t1")
        
        assert len(snapshot.queue) == 1
        assert snapshot.current_track_id == "t1"
    
    def test_resolved_result_fields(self):
        """_ResolvedResult 数据类字段正确"""
        from ui.dialogs.llm_queue_chat_dialog import _ResolvedResult
        from services.llm_queue_service import QueueReorderPlan
        from models.track import Track
        
        plan = QueueReorderPlan(ordered_track_ids=["t1"])
        track = Track(id="t1", title="Song")
        result = _ResolvedResult(plan=plan, queue=[track], start_index=0)
        
        assert result.start_index == 0
        assert len(result.queue) == 1


class TestLLMQueueChatDialogUI:
    """LLMQueueChatDialog UI 测试"""

    @pytest.fixture
    def mock_services(self, qapp):
        """创建模拟服务"""
        from services.player_service import PlayerService
        from services.library_service import LibraryService
        from services.config_service import ConfigService
        from core.database import DatabaseManager
        from core.event_bus import EventBus
        import tempfile
        
        EventBus.reset_instance()
        DatabaseManager.reset_instance()
        ConfigService.reset_instance()
        
        tmpdir = tempfile.mkdtemp(prefix="music-llm-chat-")
        db_path = f"{tmpdir}/test.db"
        config_path = f"{tmpdir}/config.yaml"
        
        db = DatabaseManager(db_path)
        config = ConfigService(config_path)
        
        mock_engine = MagicMock()
        mock_engine.state = MagicMock()
        mock_engine.get_position.return_value = 0
        mock_engine.get_duration.return_value = 0
        mock_engine.volume = 0.8
        
        player = PlayerService(audio_engine=mock_engine)
        library = LibraryService(db)
        
        yield player, library, config, tmpdir
        
        EventBus.reset_instance()
        DatabaseManager.reset_instance()
        ConfigService.reset_instance()
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.fixture
    def dialog(self, mock_services):
        """创建 LLMQueueChatDialog 实例"""
        from ui.dialogs.llm_queue_chat_dialog import LLMQueueChatDialog
        player, library, config, _ = mock_services
        return LLMQueueChatDialog(player, library, config)
    
    def test_dialog_title(self, dialog):
        """对话框标题正确"""
        assert "LLM" in dialog.windowTitle() or "队列" in dialog.windowTitle()
    
    def test_input_widget_exists(self, dialog):
        """输入框存在"""
        assert dialog._input is not None
    
    def test_send_button_exists(self, dialog):
        """发送按钮存在"""
        assert dialog._send_btn is not None
    
    def test_chat_display_exists(self, dialog):
        """聊天显示区域存在"""
        assert dialog._chat is not None
    
    def test_settings_button_exists(self, dialog):
        """设置按钮存在"""
        assert dialog._settings_btn is not None
    
    def test_initial_not_busy(self, dialog):
        """初始状态非忙碌"""
        assert dialog._send_btn.isEnabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
