"""
播放列表组件

显示当前播放队列，支持双击播放、右键菜单、拖放排序等。
使用 Model-View 架构实现虚拟化渲染。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListView, QPushButton, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from models.track import Track
from services.player_service import PlayerService
from core.event_bus import EventBus, EventType
from ui.models.track_list_model import TrackListModel


class PlaylistWidget(QWidget):
    """
    播放列表组件
    
    显示当前播放队列，支持播放、管理和拖放排序操作。
    使用 Model-View 架构实现虚拟化渲染。
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
        
        # 列表 - Model-View 架构
        self._model = TrackListModel(enable_drag_drop=True)
        self._model.setShowIndex(False)  # 播放队列不显示序号
        
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
        self.info_label.setStyleSheet("color: #B3B3B3; font-size: 12px;")
        layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """连接信号"""
        self.event_bus.subscribe(EventType.QUEUE_CHANGED, self._on_queue_changed)
        self.event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
    
    def update_list(self):
        """更新列表显示"""
        queue = self.player.queue
        current = self.player.current_track
        
        self._model.setTracks(queue)
        
        # 高亮当前播放曲目
        if current:
            self._model.highlightTrack(current.id)
        else:
            self._model.highlightTrack(None)
        
        self.info_label.setText(f"{len(queue)} 首曲目")
    
    def _on_queue_changed(self, queue):
        """队列改变"""
        self.update_list()
    
    def _on_track_started(self, track):
        """曲目开始播放"""
        # 仅更新高亮，不重置整个列表
        if track:
            self._model.highlightTrack(track.id)
        else:
            self._model.highlightTrack(None)
    
    def _on_item_double_clicked(self, index):
        """双击曲目"""
        track = self._model.getTrack(index.row())
        if track:
            self.player.play(track)
            self.track_double_clicked.emit(track)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        index = self.list_view.indexAt(pos)
        if not index.isValid():
            return
        
        track = self._model.getTrack(index.row())
        if not track:
            return
        
        menu = QMenu(self)
        
        play_action = QAction("播放", self)
        play_action.triggered.connect(lambda: self.player.play(track))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        remove_action = QAction("从队列移除", self)
        remove_action.triggered.connect(lambda: self._remove_track(index.row()))
        menu.addAction(remove_action)
        
        menu.exec(self.list_view.mapToGlobal(pos))
    
    def _remove_track(self, row: int):
        """从队列移除曲目"""
        if row >= 0:
            self.player.remove_from_queue(row)
    
    def _on_clear_clicked(self):
        """清空队列"""
        self.player.clear_queue()
