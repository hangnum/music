"""
媒体库浏览组件

显示媒体库中的所有曲目，支持搜索和排序。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QHeaderView, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.track import Track
from services.library_service import LibraryService
from services.player_service import PlayerService
from core.event_bus import EventBus, EventType


class LibraryWidget(QWidget):
    """
    媒体库浏览组件
    
    显示所有曲目，支持搜索、排序和播放操作。
    """
    
    track_double_clicked = pyqtSignal(Track)
    add_to_queue = pyqtSignal(Track)
    
    def __init__(self, library_service: LibraryService,
                 player_service: PlayerService, parent=None):
        super().__init__(parent)
        self.library = library_service
        self.player = player_service
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
        
        # 曲目表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["标题", "艺术家", "专辑", "时长", "格式"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 60)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #1A1A1A;
            }
            QTableWidget::item {
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
        """显示曲目列表"""
        self.table.setRowCount(len(tracks))
        
        for row, track in enumerate(tracks):
            # 标题
            title_item = QTableWidgetItem(track.title)
            title_item.setData(Qt.ItemDataRole.UserRole, track)
            self.table.setItem(row, 0, title_item)
            
            # 艺术家
            self.table.setItem(row, 1, QTableWidgetItem(track.artist_name or "-"))
            
            # 专辑
            self.table.setItem(row, 2, QTableWidgetItem(track.album_name or "-"))
            
            # 时长
            self.table.setItem(row, 3, QTableWidgetItem(track.duration_str))
            
            # 格式
            self.table.setItem(row, 4, QTableWidgetItem(track.format))
        
        # 更新统计
        total_duration = sum(t.duration_ms for t in tracks)
        hours = total_duration // 3600000
        minutes = (total_duration % 3600000) // 60000
        self.stats_label.setText(
            f"{len(tracks)} 首曲目 · {hours}小时{minutes}分钟"
        )
    
    def _on_search(self, text: str):
        """搜索曲目"""
        if not text:
            self._display_tracks(self.all_tracks)
            return
        
        text = text.lower()
        filtered = [t for t in self.all_tracks if 
                    text in t.title.lower() or
                    text in t.artist_name.lower() or
                    text in t.album_name.lower()]
        self._display_tracks(filtered)
    
    def _on_row_double_clicked(self, index):
        """双击行"""
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            track = item.data(Qt.ItemDataRole.UserRole)
            if track:
                # 将当前视图中的所有曲目添加到队列
                visible_tracks = self._get_visible_tracks()
                track_index = next((i for i, t in enumerate(visible_tracks) 
                                   if t.id == track.id), 0)
                self.player.set_queue(visible_tracks, track_index)
                self.player.play()
                self.track_double_clicked.emit(track)
    
    def _get_visible_tracks(self) -> List[Track]:
        """获取当前显示的所有曲目"""
        tracks = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                track = item.data(Qt.ItemDataRole.UserRole)
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
            item = self.table.item(row, 0)
            if item:
                track = item.data(Qt.ItemDataRole.UserRole)
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
    
    def _on_scan_completed(self, data):
        """扫描完成"""
        self._load_tracks()
    
    def _on_track_added(self, track):
        """新曲目添加"""
        pass  # 可以增量更新
