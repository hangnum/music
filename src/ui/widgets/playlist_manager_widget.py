"""
歌单管理组件

显示用户创建的歌单列表，支持新建、重命名、删除歌单。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QMenu,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.playlist import Playlist
from services.playlist_service import PlaylistService
from core.event_bus import EventBus, EventType


class PlaylistManagerWidget(QWidget):
    """
    歌单管理组件
    
    显示和管理用户的播放列表，解耦于主窗口实现。
    
    Signals:
        playlist_selected: 歌单被选中时发出
        create_requested: 请求创建新歌单
    """
    
    playlist_selected = pyqtSignal(Playlist)
    create_requested = pyqtSignal()
    
    def __init__(self, playlist_service: PlaylistService, parent=None):
        """
        初始化组件
        
        Args:
            playlist_service: 歌单服务实例
            parent: 父组件
        """
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._event_bus = EventBus()
        
        self._setup_ui()
        self._connect_signals()
        self.refresh()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题栏
        header = QHBoxLayout()
        
        title = QLabel("我的歌单")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.add_btn = QPushButton("＋")
        self.add_btn.setFixedSize(32, 32)
        self.add_btn.setToolTip("新建歌单")
        self.add_btn.clicked.connect(self.create_requested.emit)
        header.addWidget(self.add_btn)
        
        layout.addLayout(header)
        
        # 歌单列表
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # 底部信息
        self.info_label = QLabel("0 个歌单")
        self.info_label.setStyleSheet("color: #B3B3B3; font-size: 12px;")
        layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """连接事件"""
        self._event_bus.subscribe(EventType.PLAYLIST_CREATED, self._on_playlist_changed)
        self._event_bus.subscribe(EventType.PLAYLIST_UPDATED, self._on_playlist_changed)
        self._event_bus.subscribe(EventType.PLAYLIST_DELETED, self._on_playlist_changed)
    
    def _on_playlist_changed(self, data=None):
        """歌单变化时刷新"""
        self.refresh()
    
    def refresh(self):
        """刷新歌单列表"""
        self.list_widget.clear()
        
        playlists = self._playlist_service.get_all()
        
        for playlist in playlists:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, playlist)
            
            # 显示文本：名称 + 曲目数
            text = f"🎵 {playlist.name}"
            if playlist.track_count > 0:
                text += f"  ({playlist.track_count})"
            
            item.setText(text)
            self.list_widget.addItem(item)
        
        self.info_label.setText(f"{len(playlists)} 个歌单")
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击歌单"""
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if playlist:
            self.playlist_selected.emit(playlist)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        playlist = item.data(Qt.ItemDataRole.UserRole)
        if not playlist:
            return
        
        menu = QMenu(self)
        
        # 打开
        open_action = QAction("打开", self)
        open_action.triggered.connect(lambda: self.playlist_selected.emit(playlist))
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        # 重命名
        rename_action = QAction("重命名...", self)
        rename_action.triggered.connect(lambda: self._rename_playlist(playlist))
        menu.addAction(rename_action)
        
        # 删除
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_playlist(playlist))
        menu.addAction(delete_action)
        
        menu.exec(self.list_widget.mapToGlobal(pos))
    
    def _rename_playlist(self, playlist: Playlist):
        """重命名歌单"""
        from ui.dialogs.create_playlist_dialog import CreatePlaylistDialog
        
        dialog = CreatePlaylistDialog(
            self, 
            edit_mode=True,
            initial_name=playlist.name,
            initial_description=playlist.description
        )
        
        if dialog.exec() == CreatePlaylistDialog.DialogCode.Accepted:
            self._playlist_service.update(
                playlist.id, 
                name=dialog.get_name(),
                description=dialog.get_description()
            )
            self.refresh()
    
    def _delete_playlist(self, playlist: Playlist):
        """删除歌单"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除歌单 \"{playlist.name}\" 吗？\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._playlist_service.delete(playlist.id)
            self.refresh()
    
    def get_selected_playlist(self) -> Optional[Playlist]:
        """获取当前选中的歌单"""
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
