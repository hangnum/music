"""
歌单详情组件

显示歌单内的曲目列表，支持播放、移除曲目等操作。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.playlist import Playlist
from models.track import Track
from services.playlist_service import PlaylistService
from services.player_service import PlayerService
from core.event_bus import EventBus, EventType


class PlaylistDetailWidget(QWidget):
    """
    歌单详情组件
    
    显示某个歌单的曲目列表，支持播放、移除等操作。
    
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
        self._current_playlist: Playlist = None
        self._tracks: List[Track] = []
        
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
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        self.play_all_btn = QPushButton("▶ 播放全部")
        self.play_all_btn.clicked.connect(self._play_all)
        header.addWidget(self.play_all_btn)
        
        layout.addLayout(header)
        
        # 描述
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("color: #B3B3B3; font-size: 13px;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # 曲目列表
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # 底部信息
        self.info_label = QLabel("0 首曲目")
        self.info_label.setStyleSheet("color: #B3B3B3; font-size: 12px;")
        layout.addWidget(self.info_label)
    
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
        self.list_widget.clear()
        
        if not self._current_playlist:
            return
        
        self.title_label.setText(self._current_playlist.name)
        self.desc_label.setText(self._current_playlist.description or "")
        self.desc_label.setVisible(bool(self._current_playlist.description))
        
        # 获取曲目
        self._tracks = self._playlist_service.get_tracks(self._current_playlist.id)
        
        for i, track in enumerate(self._tracks):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, track)
            
            # 显示文本
            text = f"{i + 1}. {track.title}"
            if track.artist_name:
                text += f" - {track.artist_name}"
            text += f"  [{track.duration_str}]"
            
            item.setText(text)
            self.list_widget.addItem(item)
        
        count = len(self._tracks)
        duration = self._current_playlist.duration_str if self._current_playlist.total_duration_ms > 0 else ""
        info = f"{count} 首曲目"
        if duration:
            info += f" · {duration}"
        self.info_label.setText(info)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击播放曲目"""
        track = item.data(Qt.ItemDataRole.UserRole)
        if track:
            # 将整个歌单添加到播放队列
            self._player_service.clear_queue()
            for t in self._tracks:
                self._player_service.add_to_queue(t)
            
            # 播放选中的曲目
            self._player_service.play(track)
            self.track_double_clicked.emit(track)
    
    def _play_all(self):
        """播放全部"""
        if not self._tracks:
            return
        
        self._player_service.clear_queue()
        for track in self._tracks:
            self._player_service.add_to_queue(track)
        
        self._player_service.play(self._tracks[0])
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        track = item.data(Qt.ItemDataRole.UserRole)
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
        
        menu.exec(self.list_widget.mapToGlobal(pos))
    
    def _remove_track(self, track: Track):
        """从歌单移除曲目"""
        if self._current_playlist:
            self._playlist_service.remove_track(self._current_playlist.id, track.id)
            # 重新获取歌单以更新 track_count
            self._current_playlist = self._playlist_service.get(self._current_playlist.id)
            self._refresh()
