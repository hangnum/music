"""
播放列表组件

显示当前播放队列，支持双击播放、右键菜单等。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.track import Track
from services.player_service import PlayerService
from core.event_bus import EventBus, EventType


class PlaylistWidget(QWidget):
    """
    播放列表组件
    
    显示当前播放队列，支持播放和管理操作。
    """
    
    track_double_clicked = pyqtSignal(Track)
    llm_chat_requested = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, parent=None):
        super().__init__(parent)
        self.player = player_service
        self.event_bus = EventBus()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题栏
        header = QHBoxLayout()
        
        title = QLabel("播放队列")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()

        self.llm_btn = QPushButton("队列助手…")
        self.llm_btn.setFixedWidth(90)
        self.llm_btn.clicked.connect(self.llm_chat_requested.emit)
        header.addWidget(self.llm_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        header.addWidget(self.clear_btn)
        
        layout.addLayout(header)
        
        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # 底部信息
        self.info_label = QLabel("0 首曲目")
        self.info_label.setStyleSheet("color: #B3B3B3; font-size: 12px;")
        layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """连接信号"""
        self.event_bus.subscribe(EventType.QUEUE_CHANGED, self._on_queue_changed)
        self.event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
    
    def update_list(self):
        """更新列表显示"""
        self.list_widget.clear()
        
        queue = self.player.queue
        current = self.player.current_track
        
        for i, track in enumerate(queue):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, track)
            
            # 显示文本
            text = f"{track.title}"
            if track.artist_name:
                text += f" - {track.artist_name}"
            text += f"  [{track.duration_str}]"
            
            item.setText(text)
            
            # 高亮当前曲目
            if current and track.id == current.id:
                item.setForeground(Qt.GlobalColor.green)
                text = f"▶ {text}"
                item.setText(text)
            
            self.list_widget.addItem(item)
        
        self.info_label.setText(f"{len(queue)} 首曲目")
    
    def _on_queue_changed(self, queue):
        """队列改变"""
        self.update_list()
    
    def _on_track_started(self, track):
        """曲目开始播放"""
        self.update_list()
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击曲目"""
        track = item.data(Qt.ItemDataRole.UserRole)
        if track:
            self.player.play(track)
            self.track_double_clicked.emit(track)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        track = item.data(Qt.ItemDataRole.UserRole)
        if not track:
            return
        
        menu = QMenu(self)
        
        play_action = QAction("播放", self)
        play_action.triggered.connect(lambda: self.player.play(track))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        remove_action = QAction("从队列移除", self)
        remove_action.triggered.connect(lambda: self._remove_track(item))
        menu.addAction(remove_action)
        
        menu.exec(self.list_widget.mapToGlobal(pos))
    
    def _remove_track(self, item: QListWidgetItem):
        """从队列移除曲目"""
        row = self.list_widget.row(item)
        if row >= 0:
            self.player.remove_from_queue(row)
    
    def _on_clear_clicked(self):
        """清空队列"""
        self.player.clear_queue()
