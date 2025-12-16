"""
迷你播放器窗口

紧凑型无边框播放控制窗口，可拖拽移动。
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QMouseEvent
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.player_service import PlayerService
from models.track import Track
from core.event_bus import EventBus, EventType


class MiniPlayer(QWidget):
    """
    迷你播放器窗口
    
    紧凑型播放控制界面，可拖拽移动。
    
    Signals:
        expand_requested: 请求返回主窗口
    """
    
    expand_requested = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, parent=None):
        """
        初始化迷你播放器
        
        Args:
            player_service: 播放器服务
            parent: 父窗口
        """
        super().__init__(parent)
        self._player = player_service
        self._event_bus = EventBus()
        self._drag_position: QPoint = None
        
        self._setup_window()
        self._setup_ui()
        self._connect_events()
        self._update_display()
    
    def _setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("Mini Player")
        self.setFixedSize(320, 80)
        
        # 无边框、置顶
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # 圆角样式
        self.setStyleSheet("""
            MiniPlayer {
                background-color: #1C1C1E;
                border-radius: 12px;
                border: 1px solid #3A3A3C;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 16px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #3A3A3C;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #2C2C2E;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #3A3A3C;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 8px;
                height: 8px;
                margin: -2px 0;
                background: #FFFFFF;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #FA2D48;
                border-radius: 2px;
            }
        """)
    
    def _setup_ui(self):
        """设置 UI 布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # 专辑封面
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(60, 60)
        self.cover_label.setStyleSheet("""
            background-color: #2C2C2E;
            border-radius: 6px;
        """)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setText("🎵")
        layout.addWidget(self.cover_label)
        
        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.title_label = QLabel("未播放")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.title_label.setMaximumWidth(140)
        info_layout.addWidget(self.title_label)
        
        self.artist_label = QLabel("-")
        self.artist_label.setStyleSheet("font-size: 11px; color: #8E8E93;")
        self.artist_label.setMaximumWidth(140)
        info_layout.addWidget(self.artist_label)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setFixedWidth(140)
        self.progress_slider.sliderReleased.connect(self._on_seek)
        info_layout.addWidget(self.progress_slider)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(4)
        
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.clicked.connect(self._player.previous_track)
        controls_layout.addWidget(self.prev_btn)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.clicked.connect(self._player.toggle_play)
        controls_layout.addWidget(self.play_btn)
        
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.clicked.connect(self._player.next_track)
        controls_layout.addWidget(self.next_btn)
        
        # 展开按钮
        self.expand_btn = QPushButton("⬜")
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setToolTip("返回主窗口")
        self.expand_btn.clicked.connect(self.expand_requested.emit)
        controls_layout.addWidget(self.expand_btn)
        
        layout.addLayout(controls_layout)
    
    def _connect_events(self):
        """连接事件"""
        self._event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
        self._event_bus.subscribe(EventType.TRACK_PAUSED, self._on_playback_paused)
        self._event_bus.subscribe(EventType.TRACK_RESUMED, self._on_playback_resumed)
        self._event_bus.subscribe(EventType.POSITION_CHANGED, self._on_position_changed)
    
    def _update_display(self):
        """更新显示"""
        track = self._player.current_track
        if track:
            self.title_label.setText(track.title or "未知曲目")
            self.artist_label.setText(track.artist_name or "未知艺术家")
            self._update_play_button(self._player.is_playing)
        else:
            self.title_label.setText("未播放")
            self.artist_label.setText("-")
            self.play_btn.setText("▶")
    
    def _on_track_started(self, track: Track):
        """曲目开始播放"""
        if track:
            self.title_label.setText(track.title or "未知曲目")
            self.artist_label.setText(track.artist_name or "未知艺术家")
        self._update_play_button(True)
    
    def _on_playback_paused(self, data=None):
        """播放暂停"""
        self._update_play_button(False)
    
    def _on_playback_resumed(self, data=None):
        """播放恢复"""
        self._update_play_button(True)
    
    def _on_position_changed(self, data):
        """播放位置变化"""
        if data and 'position' in data and 'duration' in data:
            duration = data['duration']
            if duration > 0:
                position = data['position']
                self.progress_slider.blockSignals(True)
                self.progress_slider.setValue(int(position / duration * 1000))
                self.progress_slider.blockSignals(False)
    
    def _on_seek(self):
        """进度条拖动"""
        if self._player.current_track:
            duration = self._player.current_track.duration_ms
            position = int(self.progress_slider.value() / 1000 * duration)
            self._player.seek(position)
    
    def _update_play_button(self, is_playing: bool):
        """更新播放按钮状态"""
        self.play_btn.setText("⏸" if is_playing else "▶")
    
    # 拖拽移动支持
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        self._drag_position = None
