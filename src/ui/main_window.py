"""
主窗口

应用程序的主窗口，包含所有UI组件的布局。
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QSplitter, QFrame,
    QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui.widgets.player_controls import PlayerControls
from ui.widgets.playlist_widget import PlaylistWidget
from ui.widgets.library_widget import LibraryWidget
from services.player_service import PlayerService
from services.playlist_service import PlaylistService
from services.library_service import LibraryService
from services.config_service import ConfigService
from core.database import DatabaseManager
from core.event_bus import EventBus, EventType


class MainWindow(QMainWindow):
    """
    主窗口
    
    应用程序的入口界面。
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Python Music Player")
        self.setMinimumSize(1000, 700)
        
        # 初始化服务
        self._init_services()
        
        # 加载样式
        self._load_styles()
        
        # 设置UI
        self._setup_ui()
        
        # 设置菜单
        self._setup_menu()
        
        # 连接事件
        self._connect_events()
        
        # 恢复窗口状态
        self._restore_state()
    
    def _init_services(self):
        """初始化服务"""
        self.config = ConfigService("config/default_config.yaml")
        self.db = DatabaseManager("music_library.db")
        self.player = PlayerService()
        self.playlist_service = PlaylistService(self.db)
        self.library = LibraryService(self.db)
        self.event_bus = EventBus()
    
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
        
        # 主要内容区域（侧边栏 + 内容）
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 侧边栏
        sidebar = self._create_sidebar()
        content_layout.addWidget(sidebar)
        
        # 主内容区
        self.content_stack = QStackedWidget()
        
        # 媒体库页面
        self.library_widget = LibraryWidget(self.library, self.player)
        self.content_stack.addWidget(self.library_widget)
        
        # 播放队列页面
        self.playlist_widget = PlaylistWidget(self.player)
        self.content_stack.addWidget(self.playlist_widget)
        
        content_layout.addWidget(self.content_stack, 1)
        
        main_layout.addWidget(content_widget, 1)
        
        # 底部播放控制栏
        self.player_controls = PlayerControls(self.player)
        main_layout.addWidget(self.player_controls)
    
    def _create_sidebar(self) -> QWidget:
        """创建侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)
        
        # Logo
        logo = QLabel("🎵 Music Player")
        logo.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            padding: 16px;
            color: #FFFFFF;
        """)
        layout.addWidget(logo)
        
        # 分隔线
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #282828;")
        layout.addWidget(separator)
        
        layout.addSpacing(16)
        
        # 导航按钮
        self.nav_library = QPushButton("📚  媒体库")
        self.nav_library.setCheckable(True)
        self.nav_library.setChecked(True)
        self.nav_library.clicked.connect(lambda: self._switch_page(0))
        layout.addWidget(self.nav_library)
        
        self.nav_queue = QPushButton("📋  播放队列")
        self.nav_queue.setCheckable(True)
        self.nav_queue.clicked.connect(lambda: self._switch_page(1))
        layout.addWidget(self.nav_queue)
        
        layout.addSpacing(16)
        
        # 分隔线
        separator2 = QFrame()
        separator2.setObjectName("separator")
        separator2.setFixedHeight(1)
        separator2.setStyleSheet("background-color: #282828;")
        layout.addWidget(separator2)
        
        layout.addSpacing(16)
        
        # 扫描按钮
        self.scan_btn = QPushButton("🔍  扫描媒体库")
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self.scan_btn)
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("📁  添加文件夹")
        self.add_folder_btn.clicked.connect(self._on_add_folder_clicked)
        layout.addWidget(self.add_folder_btn)
        
        layout.addStretch()
        
        # 底部信息
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666666; padding: 16px; font-size: 11px;")
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
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about = QAction("关于", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)
    
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
        
        # 更新播放列表
        if index == 1:
            self.playlist_widget.update_list()
    
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
        """关闭事件"""
        # 保存窗口大小
        self.config.set("ui.window_width", self.width())
        self.config.set("ui.window_height", self.height())
        self.config.save()
        
        # 清理资源
        self.player.cleanup()
        self.event_bus.shutdown()
        self.db.close()
        
        event.accept()
