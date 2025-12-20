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
from ui.styles.theme_manager import ThemeManager


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
        self.setFixedHeight(100)
        
        self._setup_ui()
        self._connect_signals()
        self._start_position_timer()
    
    def _setup_ui(self):
        """设置UI"""
        # 主布局：垂直两行
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 第一行：进度条（横跨整个宽度）
        self.progress_container = QWidget()
        self.progress_container.setFixedHeight(20) # 预留一点高度给handle
        prog_layout = QHBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(0)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        
        prog_layout.addWidget(self.progress_slider)
        main_layout.addWidget(self.progress_container)
        
        # 第二行：控制面板
        self.control_panel = QWidget()
        control_layout = QHBoxLayout(self.control_panel)
        control_layout.setContentsMargins(24, 4, 24, 12)
        control_layout.setSpacing(24)
        
        # 左侧：曲目信息
        self.track_info = self._create_track_info()
        control_layout.addWidget(self.track_info)
        
        # 中间：播放控制按钮
        control_layout.addStretch(1)
        self.controls = self._create_button_controls()
        control_layout.addWidget(self.controls)
        control_layout.addStretch(1)
        
        # 右侧：音量与工具
        self.volume_control = self._create_volume_control()
        control_layout.addWidget(self.volume_control)
        
        main_layout.addWidget(self.control_panel)
    
    def _create_track_info(self) -> QWidget:
        """创建曲目信息区域"""
        widget = QWidget()
        widget.setFixedWidth(240)
        widget.setObjectName("trackInfo")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 封面图片
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setStyleSheet(ThemeManager.get_cover_style())
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.cover_label)
        
        # 曲目文字信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.title_label = QLabel("未在播放")
        self.title_label.setStyleSheet(ThemeManager.get_track_title_style())
        # 限制文字长度，简单截断
        self.title_label.setFixedWidth(160)
        
        self.artist_label = QLabel("Apple Music")
        self.artist_label.setObjectName("secondaryLabel")
        self.artist_label.setStyleSheet(ThemeManager.get_track_artist_style())
        self.artist_label.setFixedWidth(160)
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        layout.addLayout(info_layout)
        
        return widget
    
    def _create_button_controls(self) -> QWidget:
        """创建播放控制按钮组（不含进度条）"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 上一曲按钮
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("controlButton")
        self.prev_btn.setToolTip("上一曲")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.prev_btn)
        
        # 播放/暂停按钮 (Hero Button)
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PlayPauseButton")
        self.play_btn.setToolTip("播放")
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setStyleSheet(ThemeManager.get_primary_button_style())
        self.play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.play_btn)
        
        # 下一曲按钮
        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("controlButton")
        self.next_btn.setToolTip("下一曲")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.next_btn.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.next_btn)
        
        return widget
    
    def _create_volume_control(self) -> QWidget:
        """创建音量和辅助功能区域"""
        widget = QWidget()
        widget.setFixedWidth(200) # 稍微加宽以容纳时间信息
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # 当前时间/总时间 (移动到右侧显示)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(ThemeManager.get_time_label_style())
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.time_label)

        # 随机播放按钮
        self.shuffle_btn = QPushButton("🔀")
        self.shuffle_btn.setObjectName("controlButton")
        self.shuffle_btn.setToolTip("随机播放")
        self.shuffle_btn.setFixedSize(28, 28)
        self.shuffle_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.clicked.connect(self._on_shuffle_clicked)
        layout.addWidget(self.shuffle_btn)
        
        # 循环播放按钮
        self.repeat_btn = QPushButton("🔁")
        self.repeat_btn.setObjectName("controlButton")
        self.repeat_btn.setToolTip("循环播放")
        self.repeat_btn.setFixedSize(28, 28)
        self.repeat_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.repeat_btn.setCheckable(True)
        self.repeat_btn.clicked.connect(self._on_repeat_clicked)
        layout.addWidget(self.repeat_btn)
        
        # 音量按钮
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setObjectName("controlButton")
        self.volume_btn.setFixedSize(28, 28)
        self.volume_btn.setStyleSheet(ThemeManager.get_control_button_style())
        self.volume_btn.clicked.connect(self._on_mute_clicked)
        layout.addWidget(self.volume_btn)
        
        # 音量滑块 (可选：可以做一个弹出式或者这种迷你式，这里保持迷你式)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(60)
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
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.PLAYBACK_STOPPED, self._on_playback_stopped)
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
                
                # 更新时间标签 "0:00 / 3:45"
                current_str = self._format_time(state.position_ms)
                total_str = self._format_time(state.duration_ms)
                self.time_label.setText(f"{current_str} / {total_str}")
    
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
            self.shuffle_btn.setChecked(False)
        else:
            self.player.set_play_mode(PlayMode.SHUFFLE)
            self.shuffle_btn.setChecked(True)
    
    def _on_repeat_clicked(self):
        """循环按钮点击"""
        mode = self.player.get_play_mode()
        if mode == PlayMode.REPEAT_ONE:
            self.player.set_play_mode(PlayMode.SEQUENTIAL)
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setChecked(False)
        elif mode == PlayMode.REPEAT_ALL:
            self.player.set_play_mode(PlayMode.REPEAT_ONE)
            self.repeat_btn.setText("🔂")
            self.repeat_btn.setChecked(True)
        else:
            self.player.set_play_mode(PlayMode.REPEAT_ALL)
            self.repeat_btn.setChecked(True)
    
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
            # Update time label initial state
            total_str = self._format_time(track.duration_ms)
            self.time_label.setText(f"0:00 / {total_str}")
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

    def _on_playback_stopped(self, _=None):
        """Playback stopped."""
        self._update_play_button()
    
    def _update_play_button(self):
        """更新播放按钮状态"""
        if self.player.is_playing:
            self.play_btn.setText("⏸")
            self.play_btn.setToolTip("暂停")
        else:
            self.play_btn.setText("▶")
            self.play_btn.setToolTip("播放")
