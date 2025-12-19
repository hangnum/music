"""
主窗口

应用程序的主窗口，包含所有UI组件的布局。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QSplitter, QFrame,
    QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from pathlib import Path

logger = logging.getLogger(__name__)

from ui.widgets.player_controls import PlayerControls
from ui.widgets.playlist_widget import PlaylistWidget
from ui.widgets.library_widget import LibraryWidget
from ui.widgets.playlist_manager_widget import PlaylistManagerWidget
from ui.widgets.playlist_detail_widget import PlaylistDetailWidget
from ui.widgets.system_tray import SystemTray
from ui.mini_player import MiniPlayer
from ui.dialogs.llm_settings_dialog import LLMSettingsDialog
from ui.dialogs.llm_queue_chat_dialog import LLMQueueChatDialog
from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
from ui.dialogs.audio_settings_dialog import AudioSettingsDialog
from core.event_bus import EventType

if TYPE_CHECKING:
    from app.container import AppContainer


class MainWindow(QMainWindow):
    """
    主窗口
    
    应用程序的入口界面。
    
    设计原则：
    - MainWindow 持有 AppContainer，但子组件只接收 facade
    - 禁止将 container 传递给子组件
    """
    
    def __init__(self, container: "AppContainer"):
        """初始化主窗口
        
        Args:
            container: 应用依赖容器
        """
        super().__init__()
        
        self.setWindowTitle("Python Music Player")
        self.setMinimumSize(1000, 700)
        
        # === 从容器获取服务引用 ===
        self._container = container
        self.config = container.config
        self.db = container.db
        self.event_bus = container.event_bus
        self.facade = container.facade
        
        # 内部服务引用（用于需要直接访问的场景）
        self.player = container._player
        self.library = container._library
        self.playlist_service = container._playlist_service
        self.queue_persistence = container._queue_persistence
        
        # 加载样式
        self._load_styles()
        
        # 设置UI
        self._setup_ui()

        # 恢复上一次播放队列（需在 UI 创建后触发 QUEUE_CHANGED 刷新界面）
        try:
            self.queue_persistence.restore_last_queue(self.player, self.library)
        except Exception as e:
            logger.warning("恢复播放队列失败: %s", e)
        
        # 设置菜单
        self._setup_menu()
        
        # 连接事件
        self._connect_events()
        
        # 初始化系统托盘
        self._setup_system_tray()
        
        # 恢复窗口状态
        self._restore_state()

    
    def _load_styles(self):
        """加载样式表"""
        style_path = Path(__file__).parent / "styles" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
    
    def _setup_ui(self):
        """设置UI布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 使用 QSplitter 代替固定的 QHBoxLayout
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1) # 细分割线
        self.splitter.setChildrenCollapsible(False)
        
        # 侧边栏
        sidebar = self._create_sidebar()
        self.splitter.addWidget(sidebar)
        
        # 主内容区
        self.content_stack = QStackedWidget()
        
        # 页面索引：0=媒体库, 1=播放队列, 2=歌单管理, 3=歌单详情
        
        # 媒体库页面
        self.library_widget = LibraryWidget(
            self.library, self.player, self.playlist_service
        )
        self.content_stack.addWidget(self.library_widget)
        
        # 播放队列页面
        self.playlist_widget = PlaylistWidget(self.player)
        self.playlist_widget.llm_chat_requested.connect(self._open_llm_queue_assistant)
        self.content_stack.addWidget(self.playlist_widget)
        
        # 歌单管理页面
        self.playlist_manager = PlaylistManagerWidget(self.playlist_service)
        self.playlist_manager.create_requested.connect(self._on_create_playlist)
        self.playlist_manager.playlist_selected.connect(self._on_playlist_selected)
        self.content_stack.addWidget(self.playlist_manager)
        
        # 歌单详情页面
        self.playlist_detail = PlaylistDetailWidget(
            self.playlist_service, self.player
        )
        self.playlist_detail.back_requested.connect(lambda: self._switch_page(2))
        self.content_stack.addWidget(self.playlist_detail)
        
        self.splitter.addWidget(self.content_stack)
        
        # 设置 Splitter 比例
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        
        # 恢复分割条位置
        last_width = self.config.get("ui.sidebar_width", 240)
        self.splitter.setSizes([last_width, 1000])

        main_layout.addWidget(self.splitter, 1)
        
        # 底部播放控制栏
        self.player_controls = PlayerControls(self.player)
        main_layout.addWidget(self.player_controls)
    
    def _create_sidebar(self) -> QWidget:
        """创建侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(200)  # 设置最小宽度
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(4)
        
        # Apple Music 分组
        header_am = QLabel("Apple Music")
        header_am.setObjectName("sidebarHeader")
        layout.addWidget(header_am)
        
        # 导航按钮
        self.nav_library = QPushButton("🎵  现在收听")
        self.nav_library.setCheckable(True)
        self.nav_library.setChecked(True)
        self.nav_library.clicked.connect(lambda: self._switch_page(0))
        layout.addWidget(self.nav_library)
        
        self.nav_discover = QPushButton("🌟  浏览")
        self.nav_discover.setCheckable(True)
        self.nav_discover.setEnabled(False) # 暂未实现
        layout.addWidget(self.nav_discover)
        
        self.nav_radio = QPushButton("📻  广播")
        self.nav_radio.setCheckable(True)
        self.nav_radio.setEnabled(False) # 暂未实现
        layout.addWidget(self.nav_radio)
        
        layout.addSpacing(24)
        
        # 资料库分组
        header_lib = QLabel("资料库")
        header_lib.setObjectName("sidebarHeader")
        layout.addWidget(header_lib)

        self.nav_all_music = QPushButton("📚  所有音乐")  # 原“媒体库”
        self.nav_all_music.setCheckable(True)
        self.nav_all_music.clicked.connect(lambda: self._switch_page(0))
        layout.addWidget(self.nav_all_music)
        
        self.nav_queue = QPushButton("📋  播放队列")
        self.nav_queue.setCheckable(True)
        self.nav_queue.clicked.connect(lambda: self._switch_page(1))
        layout.addWidget(self.nav_queue)
        
        layout.addSpacing(24)
        
        # 我的歌单分组
        header_playlist = QLabel("我的歌单")
        header_playlist.setObjectName("sidebarHeader")
        layout.addWidget(header_playlist)
        
        self.nav_playlists = QPushButton("📁  全部歌单")
        self.nav_playlists.setCheckable(True)
        self.nav_playlists.clicked.connect(lambda: self._switch_page(2))
        layout.addWidget(self.nav_playlists)
        
        self.add_playlist_btn = QPushButton("＋  新建歌单")
        self.add_playlist_btn.clicked.connect(self._on_create_playlist)
        layout.addWidget(self.add_playlist_btn)
        
        layout.addStretch()
        
        # 底部工具栏
        self.scan_btn = QPushButton("🔄  更新资料库")
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self.scan_btn)
        
        self.add_folder_btn = QPushButton("📁  添加音乐...")
        self.add_folder_btn.clicked.connect(self._on_add_folder_clicked)
        layout.addWidget(self.add_folder_btn)
        
        layout.addSpacing(16)
        
        # 底部信息
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #8E8E93; padding: 0 20px; font-size: 11px;")
        self._update_status()
        layout.addWidget(self.status_label)
        
        return sidebar
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        add_folder = QAction("添加文件夹", self)
        add_folder.triggered.connect(self._on_add_folder_clicked)
        file_menu.addAction(add_folder)
        
        scan_action = QAction("扫描媒体库", self)
        scan_action.triggered.connect(self._on_scan_clicked)
        file_menu.addAction(scan_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 播放菜单
        play_menu = menubar.addMenu("播放")
        
        play_pause = QAction("播放/暂停", self)
        play_pause.setShortcut("Space")
        play_pause.triggered.connect(self.player.toggle_play)
        play_menu.addAction(play_pause)
        
        next_track = QAction("下一曲", self)
        next_track.setShortcut("Ctrl+Right")
        next_track.triggered.connect(self.player.next_track)
        play_menu.addAction(next_track)
        
        prev_track = QAction("上一曲", self)
        prev_track.setShortcut("Ctrl+Left")
        prev_track.triggered.connect(self.player.previous_track)
        play_menu.addAction(prev_track)

        # AI 菜单
        ai_menu = menubar.addMenu("AI")

        llm_settings = QAction("LLM 设置…", self)
        llm_settings.triggered.connect(self._open_llm_settings)
        ai_menu.addAction(llm_settings)

        queue_assistant = QAction("队列助手…", self)
        queue_assistant.setShortcut("Ctrl+L")
        queue_assistant.triggered.connect(self._open_llm_queue_assistant)
        ai_menu.addAction(queue_assistant)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        audio_settings = QAction("音频设置…", self)
        audio_settings.triggered.connect(self._open_audio_settings)
        settings_menu.addAction(audio_settings)
        
        llm_settings = QAction("LLM 设置…", self)
        llm_settings.triggered.connect(self._open_llm_settings)
        settings_menu.addAction(llm_settings)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        mini_mode = QAction("迷你模式", self)
        mini_mode.setShortcut("Ctrl+M")
        mini_mode.triggered.connect(self._switch_to_mini_mode)
        view_menu.addAction(mini_mode)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about = QAction("关于", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _open_llm_settings(self):
        dlg = LLMSettingsDialog(self.config, self)
        dlg.exec()

    def _open_audio_settings(self):
        dlg = AudioSettingsDialog(self.config, self)
        dlg.exec()

    def _open_llm_queue_assistant(self):
        dlg = LLMQueueChatDialog(self.player, self.library, self.config, self)
        dlg.exec()
    
    def _on_create_playlist(self):
        """新建歌单"""
        dialog = CreatePlaylistDialog(self)
        if dialog.exec() == CreatePlaylistDialog.DialogCode.Accepted:
            name = dialog.get_name()
            description = dialog.get_description()
            self.playlist_service.create(name, description)
            self.playlist_manager.refresh()
    
    def _on_playlist_selected(self, playlist):
        """歌单被选中"""
        self.playlist_detail.set_playlist(playlist)
        self._switch_page(3)
    
    def _switch_to_mini_mode(self):
        """切换到迷你模式"""
        if not hasattr(self, '_mini_player') or self._mini_player is None:
            self._mini_player = MiniPlayer(self.player)
            self._mini_player.expand_requested.connect(self._switch_from_mini_mode)
        
        # 保存主窗口位置
        self._main_window_geometry = self.geometry()
        
        # 隐藏主窗口，显示迷你播放器
        self.hide()
        self._mini_player.show()
        
        # 将迷你播放器放在屏幕右下角
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self._mini_player.move(
            screen.width() - self._mini_player.width() - 20,
            screen.height() - self._mini_player.height() - 100
        )
    
    def _switch_from_mini_mode(self):
        """从迷你模式返回主窗口"""
        if hasattr(self, '_mini_player') and self._mini_player:
            self._mini_player.hide()
        
        # 恢复主窗口
        self.show()
        if hasattr(self, '_main_window_geometry'):
            self.setGeometry(self._main_window_geometry)
        self.activateWindow()
        self.raise_()
    
    def _connect_events(self):
        """连接事件"""
        self.event_bus.subscribe(EventType.LIBRARY_SCAN_COMPLETED, 
                                  self._on_scan_completed)
        self.event_bus.subscribe(EventType.LIBRARY_SCAN_PROGRESS,
                                  self._on_scan_progress)
        self.event_bus.subscribe(EventType.TRACK_STARTED,
                                  self._on_track_started)
    
    def _switch_page(self, index: int):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
        
        # 更新导航按钮状态
        self.nav_library.setChecked(index == 0)
        self.nav_queue.setChecked(index == 1)
        self.nav_playlists.setChecked(index in (2, 3))
        
        # 根据页面刷新内容
        if index == 1:
            self.playlist_widget.update_list()
        elif index == 2:
            self.playlist_manager.refresh()
    
    def _on_scan_clicked(self):
        """扫描媒体库"""
        dirs = self.config.get("library.directories", [])
        if dirs:
            self.scan_btn.setText("🔄  扫描中...")
            self.scan_btn.setEnabled(False)
            self.library.scan_async(dirs)
        else:
            QMessageBox.information(
                self, "提示", 
                "请先添加音乐文件夹到配置中"
            )
    
    def _on_add_folder_clicked(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择音乐文件夹", ""
        )
        
        if folder:
            dirs = self.config.get("library.directories", [])
            if folder not in dirs:
                dirs.append(folder)
                self.config.set("library.directories", dirs)
                self.config.save()
                
                # 自动扫描
                self.scan_btn.setText("🔄  扫描中...")
                self.scan_btn.setEnabled(False)
                self.library.scan_async([folder])
    
    def _on_scan_completed(self, data):
        """扫描完成"""
        self.scan_btn.setText("🔍  扫描媒体库")
        self.scan_btn.setEnabled(True)
        self._update_status()
        
        QMessageBox.information(
            self, "扫描完成",
            f"扫描完成！\n添加了 {data.get('total_added', 0)} 首曲目"
        )
    
    def _on_scan_progress(self, data):
        """扫描进度更新"""
        current = data.get('current', 0)
        total = data.get('total', 0)
        self.scan_btn.setText(f"🔄  {current}/{total}")
    
    def _on_track_started(self, track):
        """曲目开始播放"""
        if track:
            self.setWindowTitle(f"{track.title} - Python Music Player")
    
    def _update_status(self):
        """更新状态信息"""
        count = self.library.get_track_count()
        self.status_label.setText(f"媒体库: {count} 首曲目")
    
    def _restore_state(self):
        """恢复窗口状态"""
        width = self.config.get("ui.window_width", 1200)
        height = self.config.get("ui.window_height", 800)
        self.resize(width, height)
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 Python Music Player",
            "Python Music Player v1.0\n\n"
            "一个高质量的本地音乐播放器\n\n"
            "技术栈: PyQt6 + pygame + mutagen"
        )
    
    def closeEvent(self, event):
        """关闭事件 - 隐藏到托盘而非退出"""
        # 检查是否应该隐藏到托盘
        minimize_to_tray = self.config.get("ui.minimize_to_tray", True)
        
        if minimize_to_tray and self._system_tray.is_visible():
            # 隐藏到托盘
            event.ignore()
            self.hide()
        else:
            # 真正退出
            self._do_cleanup_and_exit(event)
    
    def _do_cleanup_and_exit(self, event=None):
        """清理资源并退出"""
        # 保存窗口大小
        self.config.set("ui.window_width", self.width())
        self.config.set("ui.window_height", self.height())
        if hasattr(self, 'splitter'):
             self.config.set("ui.sidebar_width", self.splitter.sizes()[0])
        self.config.save()

        try:
            self.queue_persistence.persist_from_player()
            self.queue_persistence.shutdown()
        except Exception as e:
            logger.warning("保存播放队列失败: %s", e)
        
        # 隐藏托盘
        self._system_tray.hide()
        
        # 等待扫描线程完成
        self.library.join_scan_thread()
        
        # 清理资源
        self.player.cleanup()
        self.event_bus.shutdown()
        self.db.close()
        
        if event:
            event.accept()
    
    def _setup_system_tray(self):
        """初始化系统托盘"""
        self._system_tray = SystemTray(self.player, self)
        self._system_tray.show_window_requested.connect(self._show_from_tray)
        self._system_tray.exit_requested.connect(self._exit_application)
        
        # 显示托盘图标
        self._system_tray.show()
        
        # 读取通知设置
        show_notifications = self.config.get("ui.show_tray_notifications", True)
        self._system_tray.set_show_notifications(show_notifications)
    
    def _show_from_tray(self):
        """从托盘显示窗口"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def _exit_application(self):
        """从托盘菜单退出应用"""
        self._do_cleanup_and_exit()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
