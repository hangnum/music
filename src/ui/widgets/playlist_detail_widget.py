"""
歌单详情组件

显示歌单内的曲目列表，支持播放、移除曲目、拖放排序等操作。
使用 Model-View 架构实现虚拟化渲染。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListView, QPushButton, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import List, Optional

from models.playlist import Playlist
from models.track import Track
from services.playlist_service import PlaylistService
from services.player_service import PlayerService
from ui.models.track_list_model import TrackListModel
from ui.styles.theme_manager import ThemeManager


class PlaylistDetailWidget(QWidget):
    """
    歌单详情组件
    
    显示某个歌单的曲目列表，支持播放、移除、拖放排序等操作。
    使用 Model-View 架构实现虚拟化渲染。
    
    Signals:
        back_requested: 请求返回歌单列表
        track_double_clicked: 曲目双击事件
    """
    
    back_requested = pyqtSignal()
    track_double_clicked = pyqtSignal(Track)
    
    def __init__(self, playlist_service: PlaylistService, 
                 player_service: PlayerService, parent=None):
        """
        初始化组件
        
        Args:
            playlist_service: 歌单服务
            player_service: 播放器服务
            parent: 父组件
        """
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._player_service = player_service
        self._current_playlist: Optional[Playlist] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题栏
        header = QHBoxLayout()
        
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.setToolTip("返回歌单列表")
        self.back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_btn)
        
        self.title_label = QLabel("歌单详情")
        self.title_label.setStyleSheet(ThemeManager.get_section_title_style())
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        self.play_all_btn = QPushButton("▶ 播放全部")
        self.play_all_btn.clicked.connect(self._play_all)
        header.addWidget(self.play_all_btn)
        
        layout.addLayout(header)
        
        # 描述
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(ThemeManager.get_secondary_label_style())
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # 曲目列表 - Model-View 架构
        self._model = TrackListModel(enable_drag_drop=True)
        
        self.list_view = QListView()
        self.list_view.setModel(self._model)
        
        # 启用拖放排序
        self.list_view.setDragEnabled(True)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDropIndicatorShown(True)
        self.list_view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # 性能优化：统一项高
        self.list_view.setUniformItemSizes(True)
        
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        self.list_view.doubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.list_view)
        
        # 底部信息
        self.info_label = QLabel("0 首曲目")
        self.info_label.setStyleSheet(ThemeManager.get_info_label_style())
        layout.addWidget(self.info_label)
    
    @property
    def playlist(self) -> Optional[Playlist]:
        """获取当前显示的歌单"""
        return self._current_playlist
    
    def set_playlist(self, playlist: Playlist):
        """
        设置当前显示的歌单
        
        Args:
            playlist: 歌单对象
        """
        self._current_playlist = playlist
        self._refresh()
    
    def _refresh(self):
        """刷新曲目列表"""
        if not self._current_playlist:
            self._model.setTracks([])
            return
        
        self.title_label.setText(self._current_playlist.name)
        self.desc_label.setText(self._current_playlist.description or "")
        self.desc_label.setVisible(bool(self._current_playlist.description))
        
        # 获取曲目并设置到模型
        tracks = self._playlist_service.get_tracks(self._current_playlist.id)
        self._model.setTracks(tracks)
        
        # 更新统计信息
        count = len(tracks)
        duration = self._current_playlist.duration_str if self._current_playlist.total_duration_ms > 0 else ""
        info = f"{count} 首曲目"
        if duration:
            info += f" · {duration}"
        self.info_label.setText(info)
    
    def _on_item_double_clicked(self, index):
        """双击播放曲目"""
        track = self._model.getTrack(index.row())
        if track:
            # 将整个歌单添加到播放队列
            tracks = self._model.getTracks()
            self._player_service.clear_queue()
            for t in tracks:
                self._player_service.add_to_queue(t)
            
            # 播放选中的曲目
            self._player_service.play(track)
            self.track_double_clicked.emit(track)
    
    def _play_all(self):
        """播放全部"""
        tracks = self._model.getTracks()
        if not tracks:
            return
        
        self._player_service.clear_queue()
        for track in tracks:
            self._player_service.add_to_queue(track)
        
        self._player_service.play(tracks[0])
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        index = self.list_view.indexAt(pos)
        if not index.isValid():
            return
        
        track = self._model.getTrack(index.row())
        if not track:
            return
        
        menu = QMenu(self)
        
        # 播放
        play_action = QAction("播放", self)
        play_action.triggered.connect(lambda: self._player_service.play(track))
        menu.addAction(play_action)
        
        # 添加到播放队列
        add_queue_action = QAction("添加到播放队列", self)
        add_queue_action.triggered.connect(lambda: self._player_service.add_to_queue(track))
        menu.addAction(add_queue_action)
        
        menu.addSeparator()
        
        # 从歌单移除
        remove_action = QAction("从歌单移除", self)
        remove_action.triggered.connect(lambda: self._remove_track(track))
        menu.addAction(remove_action)
        
        menu.exec(self.list_view.mapToGlobal(pos))
    
    def _remove_track(self, track: Track):
        """从歌单移除曲目"""
        if self._current_playlist:
            self._playlist_service.remove_track(self._current_playlist.id, track.id)
            # 重新获取歌单以更新 track_count
            self._current_playlist = self._playlist_service.get(self._current_playlist.id)
            self._refresh()
