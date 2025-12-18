"""
媒体库浏览组件

显示媒体库中的所有曲目，支持搜索和排序。
使用 Model-View 架构实现虚拟化渲染，优化大列表性能。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableView, QPushButton,
    QLineEdit, QHeaderView, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import List

from models.track import Track
from services.library_service import LibraryService
from services.player_service import PlayerService
from services.playlist_service import PlaylistService
from services.tag_service import TagService
from core.event_bus import EventBus, EventType
from core.database import DatabaseManager
from ui.models.track_table_model import TrackTableModel, TrackFilterProxyModel


class LibraryWidget(QWidget):
    """
    媒体库浏览组件
    
    显示所有曲目，支持搜索、排序和播放操作。
    """
    
    track_double_clicked = pyqtSignal(Track)
    add_to_queue = pyqtSignal(Track)
    
    def __init__(self, library_service: LibraryService,
                 player_service: PlayerService, 
                 playlist_service: PlaylistService = None,
                 parent=None):
        super().__init__(parent)
        self.library = library_service
        self.player = player_service
        self._playlist_service = playlist_service
        self.event_bus = EventBus()
        
        self.all_tracks: List[Track] = []
        
        self._setup_ui()
        self._connect_signals()
        self._load_tracks()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)
        
        # 标题和搜索栏
        header = QHBoxLayout()
        
        title = QLabel("媒体库")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索曲目...")
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(self._on_search)
        header.addWidget(self.search_input)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(60)
        self.refresh_btn.clicked.connect(self._load_tracks)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #B3B3B3; margin-bottom: 8px;")
        layout.addWidget(self.stats_label)
        
        # 曲目表格 - 使用 Model-View 架构
        self._source_model = TrackTableModel()
        self._proxy_model = TrackFilterProxyModel()
        self._proxy_model.setSourceModel(self._source_model)
        
        self.table = QTableView()
        self.table.setModel(self._proxy_model)
        
        # 表头设置
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 60)
        
        # 视图属性
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        
        # 性能优化：统一行高
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(36)
        
        self.table.setStyleSheet("""
            QTableView {
                alternate-background-color: #1A1A1A;
            }
            QTableView::item {
                padding: 8px;
            }
        """)
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
    
    def _connect_signals(self):
        """连接信号"""
        self.event_bus.subscribe(EventType.LIBRARY_SCAN_COMPLETED, 
                                  self._on_scan_completed)
        self.event_bus.subscribe(EventType.TRACK_ADDED, self._on_track_added)
    
    def _load_tracks(self):
        """加载所有曲目"""
        self.all_tracks = self.library.get_all_tracks()
        self._display_tracks(self.all_tracks)
    
    def _display_tracks(self, tracks: List[Track]):
        """显示曲目列表 - 使用 Model 实现 O(1) 更新"""
        self._source_model.setTracks(tracks)
        self._update_stats(tracks)
    
    def _update_stats(self, tracks: List[Track]):
        """更新统计信息"""
        total_duration = sum(t.duration_ms for t in tracks)
        hours = total_duration // 3600000
        minutes = (total_duration % 3600000) // 60000
        self.stats_label.setText(
            f"{len(tracks)} 首曲目 · {hours}小时{minutes}分钟"
        )
    
    def _on_search(self, text: str):
        """搜索曲目 - 使用代理模型过滤"""
        self._proxy_model.setFilterText(text)
        # 更新统计为过滤后的数量
        filtered_count = self._proxy_model.rowCount()
        if text:
            self.stats_label.setText(f"找到 {filtered_count} 首曲目")
        else:
            self._update_stats(self.all_tracks)
    
    def _on_row_double_clicked(self, index):
        """双击行"""
        # 通过代理模型获取源模型索引
        source_index = self._proxy_model.mapToSource(index)
        track = self._source_model.getTrack(source_index.row())
        
        if track:
            # 将当前视图中的所有曲目添加到队列
            visible_tracks = self._get_visible_tracks()
            track_index = next((i for i, t in enumerate(visible_tracks) 
                               if t.id == track.id), 0)
            self.player.set_queue(visible_tracks, track_index)
            self.player.play()
            self.track_double_clicked.emit(track)
    
    def _get_visible_tracks(self) -> List[Track]:
        """获取当前显示的所有曲目（过滤后）"""
        tracks = []
        for row in range(self._proxy_model.rowCount()):
            source_index = self._proxy_model.mapToSource(
                self._proxy_model.index(row, 0)
            )
            track = self._source_model.getTrack(source_index.row())
            if track:
                tracks.append(track)
        return tracks
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        rows = set(index.row() for index in self.table.selectedIndexes())
        if not rows:
            return
        
        menu = QMenu(self)
        
        # 获取选中的曲目
        selected_tracks = []
        for row in rows:
            source_index = self._proxy_model.mapToSource(
                self._proxy_model.index(row, 0)
            )
            track = self._source_model.getTrack(source_index.row())
            if track:
                selected_tracks.append(track)
        
        if len(selected_tracks) == 1:
            track = selected_tracks[0]
            
            play_now = QAction("立即播放", self)
            play_now.triggered.connect(lambda: self._play_track(track))
            menu.addAction(play_now)
            
            play_next = QAction("下一首播放", self)
            play_next.triggered.connect(lambda: self.player.insert_next(track))
            menu.addAction(play_next)
        
        add_to_queue = QAction(f"添加到队列 ({len(selected_tracks)}首)", self)
        add_to_queue.triggered.connect(lambda: self._add_tracks_to_queue(selected_tracks))
        menu.addAction(add_to_queue)
        
        # 添加到歌单子菜单
        if self._playlist_service:
            playlist_menu = menu.addMenu(f"添加到歌单 ({len(selected_tracks)}首)")
            playlists = self._playlist_service.get_all()
            
            if playlists:
                for playlist in playlists:
                    action = QAction(f"🎵 {playlist.name}", self)
                    # 使用闭包捕获 playlist.id
                    action.triggered.connect(
                        lambda checked, pid=playlist.id: self._add_to_playlist(pid, selected_tracks)
                    )
                    playlist_menu.addAction(action)
            else:
                no_playlist = QAction("(暂无歌单)", self)
                no_playlist.setEnabled(False)
                playlist_menu.addAction(no_playlist)
        
        menu.addSeparator()
        
        # 管理标签
        manage_tags = QAction(f"管理标签 ({len(selected_tracks)}首)", self)
        manage_tags.triggered.connect(lambda: self._show_tag_dialog(selected_tracks))
        menu.addAction(manage_tags)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))
    
    def _play_track(self, track: Track):
        """播放曲目"""
        visible_tracks = self._get_visible_tracks()
        track_index = next((i for i, t in enumerate(visible_tracks) 
                           if t.id == track.id), 0)
        self.player.set_queue(visible_tracks, track_index)
        self.player.play()
    
    def _add_tracks_to_queue(self, tracks: List[Track]):
        """添加曲目到队列"""
        for track in tracks:
            self.player.add_to_queue(track)
            self.add_to_queue.emit(track)
    
    def _add_to_playlist(self, playlist_id: str, tracks: List[Track]):
        """添加曲目到歌单"""
        if not self._playlist_service:
            return
        
        for track in tracks:
            self._playlist_service.add_track(playlist_id, track)
    
    def _show_tag_dialog(self, tracks: List[Track]):
        """显示标签管理对话框"""
        from ui.dialogs.tag_dialog import TagDialog
        
        tag_service = TagService(DatabaseManager())
        dialog = TagDialog(tracks, tag_service, self)
        dialog.exec()
    
    def _on_scan_completed(self, data):
        """扫描完成"""
        self._load_tracks()
    
    def _on_track_added(self, track):
        """新曲目添加"""
        pass  # 可以增量更新

