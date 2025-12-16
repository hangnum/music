"""
系统托盘组件

实现系统托盘图标、菜单和通知功能，彻底解耦于主窗口。
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.player_service import PlayerService
from core.event_bus import EventBus, EventType


class SystemTray(QObject):
    """
    系统托盘组件
    
    提供托盘图标、菜单和通知功能，与主窗口解耦。
    
    Signals:
        show_window_requested: 请求显示主窗口
        exit_requested: 请求退出应用
    """
    
    show_window_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, parent=None):
        """
        初始化系统托盘
        
        Args:
            player_service: 播放器服务
            parent: 父对象
        """
        super().__init__(parent)
        self._player = player_service
        self._event_bus = EventBus()
        self._show_notifications = True
        
        self._setup_tray()
        self._connect_events()
    
    def _setup_tray(self):
        """设置托盘图标和菜单"""
        self._tray = QSystemTrayIcon(self.parent())
        
        # 设置图标
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "app_icon.svg"
        if icon_path.exists():
            self._tray.setIcon(QIcon(str(icon_path)))
        else:
            # 使用默认应用图标
            from PyQt6.QtWidgets import QApplication
            self._tray.setIcon(QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_MediaPlay
            ))
        
        self._tray.setToolTip("Python Music Player")
        
        # 创建菜单
        self._menu = QMenu()
        self._create_menu()
        self._tray.setContextMenu(self._menu)
        
        # 双击事件
        self._tray.activated.connect(self._on_tray_activated)
    
    def _create_menu(self):
        """创建托盘菜单"""
        # 显示主窗口
        self._show_action = QAction("显示主窗口", self._menu)
        self._show_action.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(self._show_action)
        
        self._menu.addSeparator()
        
        # 播放控制
        self._play_action = QAction("▶ 播放", self._menu)
        self._play_action.triggered.connect(self._on_play_clicked)
        self._menu.addAction(self._play_action)
        
        self._prev_action = QAction("⏮ 上一曲", self._menu)
        self._prev_action.triggered.connect(self._player.previous_track)
        self._menu.addAction(self._prev_action)
        
        self._next_action = QAction("⏭ 下一曲", self._menu)
        self._next_action.triggered.connect(self._player.next_track)
        self._menu.addAction(self._next_action)
        
        self._menu.addSeparator()
        
        # 退出
        self._exit_action = QAction("退出", self._menu)
        self._exit_action.triggered.connect(self.exit_requested.emit)
        self._menu.addAction(self._exit_action)
    
    def _connect_events(self):
        """连接事件"""
        self._event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
        self._event_bus.subscribe(EventType.TRACK_PAUSED, self._on_playback_paused)
        self._event_bus.subscribe(EventType.TRACK_RESUMED, self._on_playback_resumed)
    
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()
    
    def _on_play_clicked(self):
        """播放按钮点击"""
        self._player.toggle_play()
    
    def _on_track_started(self, track):
        """曲目开始播放"""
        self._update_play_action(is_playing=True)
        
        if self._show_notifications and track:
            title = track.title or "未知曲目"
            artist = track.artist_name or "未知艺术家"
            self._tray.showMessage(
                "正在播放",
                f"{title}\n{artist}",
                QSystemTrayIcon.MessageIcon.Information,
                2000  # 2秒
            )
    
    def _on_playback_paused(self, data=None):
        """播放暂停"""
        self._update_play_action(is_playing=False)
    
    def _on_playback_resumed(self, data=None):
        """播放恢复"""
        self._update_play_action(is_playing=True)
    
    def _update_play_action(self, is_playing: bool):
        """更新播放按钮状态"""
        if is_playing:
            self._play_action.setText("⏸ 暂停")
        else:
            self._play_action.setText("▶ 播放")
    
    def show(self):
        """显示托盘图标"""
        self._tray.show()
    
    def hide(self):
        """隐藏托盘图标"""
        self._tray.hide()
    
    def is_visible(self) -> bool:
        """托盘是否可见"""
        return self._tray.isVisible()
    
    def set_show_notifications(self, enabled: bool):
        """设置是否显示通知"""
        self._show_notifications = enabled
    
    @property
    def tray_icon(self) -> QSystemTrayIcon:
        """获取托盘图标对象"""
        return self._tray
