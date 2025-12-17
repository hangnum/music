"""
播放控制组件

包含播放/暂停、上一曲/下一曲、进度条、音量控制等。
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QSlider, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from services.player_service import PlayerService, PlayMode
from core.event_bus import EventBus, EventType


class PlayerControls(QWidget):
    """
    播放控制组件
    
    显示当前曲目信息和播放控制按钮。
    """
    
    # 信号
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    
    def __init__(self, player_service: PlayerService, parent=None):
        super().__init__(parent)
        self.player = player_service
        self.event_bus = EventBus()
        self._subscriptions: list = []  # 跟踪事件订阅ID
        
        self.setObjectName("playerBar")
        self.setFixedHeight(90)
        
        self._setup_ui()
        self._connect_signals()
        self._start_position_timer()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 12)  # 增加边距
        layout.setSpacing(32)  # 增加组件间距
        
        # 左侧：曲目信息
        self.track_info = self._create_track_info()
        layout.addWidget(self.track_info)
        
        # 中间：播放控制
        self.controls = self._create_controls()
        layout.addWidget(self.controls, 1)
        
        # 右侧：音量控制
        self.volume_control = self._create_volume_control()
        layout.addWidget(self.volume_control)
    
    def _create_track_info(self) -> QWidget:
        """创建曲目信息区域"""
        widget = QWidget()
        widget.setFixedWidth(240)  # 第一列稍宽
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 封面图片
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setStyleSheet("""
            background-color: #2C2C2E;
            border-radius: 6px;
            border: 1px solid #3A3A3C;
        """)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.cover_label)
        
        # 曲目文字信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)  # 减小行间距
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.title_label = QLabel("未在播放")
        self.title_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #FFFFFF;")
        self.title_label.setWordWrap(False)
        
        self.artist_label = QLabel("Apple Music")
        self.artist_label.setObjectName("secondaryLabel")
        self.artist_label.setStyleSheet("color: #8E8E93; font-size: 13px; font-weight: 400;")
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        layout.addLayout(info_layout)
        
        return widget
    
    def _create_controls(self) -> QWidget:
        """创建播放控制区域"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # 控制按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(24)  # 按钮间距
        
        # 随机播放按钮
        self.shuffle_btn = QPushButton("🔀")
        self.shuffle_btn.setObjectName("controlButton")
        self.shuffle_btn.setToolTip("随机播放")
        self.shuffle_btn.setFixedSize(32, 32)
        self.shuffle_btn.clicked.connect(self._on_shuffle_clicked)
        btn_layout.addWidget(self.shuffle_btn)
        
        # 上一曲按钮
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("controlButton")
        self.prev_btn.setToolTip("上一曲")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        btn_layout.addWidget(self.prev_btn)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("playButton")
        self.play_btn.setToolTip("播放")
        self.play_btn.setFixedSize(48, 48)  # 加大播放按钮
        self.play_btn.clicked.connect(self._on_play_clicked)
        btn_layout.addWidget(self.play_btn)
        
        # 下一曲按钮
        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("controlButton")
        self.next_btn.setToolTip("下一曲")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.clicked.connect(self._on_next_clicked)
        btn_layout.addWidget(self.next_btn)
        
        # 循环播放按钮
        self.repeat_btn = QPushButton("🔁")
        self.repeat_btn.setObjectName("controlButton")
        self.repeat_btn.setToolTip("循环播放")
        self.repeat_btn.setFixedSize(32, 32)
        self.repeat_btn.clicked.connect(self._on_repeat_clicked)
        btn_layout.addWidget(self.repeat_btn)
        
        main_layout.addLayout(btn_layout)
        
        # 进度条行
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(12)
        
        self.current_time = QLabel("0:00")
        self.current_time.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: 500;")
        self.current_time.setFixedWidth(40)
        self.current_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_layout.addWidget(self.current_time)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        progress_layout.addWidget(self.progress_slider, 1)
        
        self.total_time = QLabel("0:00")
        self.total_time.setStyleSheet("color: #8E8E93; font-size: 11px; font-weight: 500;")
        self.total_time.setFixedWidth(40)
        progress_layout.addWidget(self.total_time)
        
        main_layout.addLayout(progress_layout)
        
        return widget
    
    def _create_volume_control(self) -> QWidget:
        """创建音量控制区域"""
        widget = QWidget()
        widget.setFixedWidth(150)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 音量图标
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setObjectName("controlButton")
        self.volume_btn.setFixedSize(32, 32)
        self.volume_btn.clicked.connect(self._on_mute_clicked)
        layout.addWidget(self.volume_btn)
        
        # 音量滑块
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.volume_slider)
        
        return widget
    
    def _connect_signals(self):
        """连接事件信号"""
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_STARTED, self._on_track_started)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_PAUSED, self._on_track_paused)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_RESUMED, self._on_track_resumed)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.TRACK_ENDED, self._on_track_ended)
        )
    
    def cleanup(self):
        """清理事件订阅（应在组件销毁前调用）"""
        for sub_id in self._subscriptions:
            self.event_bus.unsubscribe(sub_id)
        self._subscriptions.clear()
    
    def _start_position_timer(self):
        """启动位置更新定时器"""
        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(500)  # 每500ms更新一次
        self._slider_dragging = False
    
    def _update_position(self):
        """更新播放位置并检测播放结束"""
        if self._slider_dragging:
            return
        
        # 检测播放是否结束（主线程安全）
        if self.player.check_playback_ended():
            self._update_play_button()
            return
        
        if self.player.is_playing:
            state = self.player.state
            if state.duration_ms > 0:
                progress = int((state.position_ms / state.duration_ms) * 1000)
                self.progress_slider.setValue(progress)
                self.current_time.setText(self._format_time(state.position_ms))
    
    def _format_time(self, ms: int) -> str:
        """格式化时间"""
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _on_play_clicked(self):
        """播放按钮点击"""
        self.player.toggle_play()
        self._update_play_button()
    
    def _on_prev_clicked(self):
        """上一曲按钮点击"""
        self.player.previous_track()
        self.previous_clicked.emit()
    
    def _on_next_clicked(self):
        """下一曲按钮点击"""
        self.player.next_track()
        self.next_clicked.emit()
    
    def _on_shuffle_clicked(self):
        """随机播放按钮点击"""
        mode = self.player.get_play_mode()
        if mode == PlayMode.SHUFFLE:
            self.player.set_play_mode(PlayMode.SEQUENTIAL)
            self.shuffle_btn.setStyleSheet("")
        else:
            self.player.set_play_mode(PlayMode.SHUFFLE)
            self.shuffle_btn.setStyleSheet("color: #1DB954;")
    
    def _on_repeat_clicked(self):
        """循环按钮点击"""
        mode = self.player.get_play_mode()
        if mode == PlayMode.REPEAT_ONE:
            self.player.set_play_mode(PlayMode.SEQUENTIAL)
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setStyleSheet("")
        elif mode == PlayMode.REPEAT_ALL:
            self.player.set_play_mode(PlayMode.REPEAT_ONE)
            self.repeat_btn.setText("🔂")
            self.repeat_btn.setStyleSheet("color: #1DB954;")
        else:
            self.player.set_play_mode(PlayMode.REPEAT_ALL)
            self.repeat_btn.setStyleSheet("color: #1DB954;")
    
    def _on_slider_pressed(self):
        """进度条按下"""
        self._slider_dragging = True
    
    def _on_slider_released(self):
        """进度条释放"""
        self._slider_dragging = False
        state = self.player.state
        if state.duration_ms > 0:
            position = int((self.progress_slider.value() / 1000) * state.duration_ms)
            self.player.seek(position)
    
    def _on_volume_changed(self, value):
        """音量改变"""
        volume = value / 100
        self.player.set_volume(volume)
        
        # 更新音量图标
        if value == 0:
            self.volume_btn.setText("🔇")
        elif value < 50:
            self.volume_btn.setText("🔉")
        else:
            self.volume_btn.setText("🔊")
    
    def _on_mute_clicked(self):
        """静音按钮点击"""
        if self.volume_slider.value() > 0:
            self._saved_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
        else:
            self.volume_slider.setValue(getattr(self, '_saved_volume', 80))
    
    def _on_track_started(self, track):
        """曲目开始播放"""
        if track:
            self.title_label.setText(track.title)
            self.artist_label.setText(track.artist_name)
            self.total_time.setText(self._format_time(track.duration_ms))
        self._update_play_button()
    
    def _on_track_paused(self, _=None):
        """曲目暂停"""
        self._update_play_button()
    
    def _on_track_resumed(self, _=None):
        """曲目恢复"""
        self._update_play_button()
    
    def _on_track_ended(self, _=None):
        """曲目结束"""
        self._update_play_button()
    
    def _update_play_button(self):
        """更新播放按钮状态"""
        if self.player.is_playing:
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("暂停")
        else:
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("播放")
