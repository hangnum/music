"""
VLC 音频引擎实现

基于 python-vlc 库的音频后端，支持:
- ReplayGain (增益调整)
- EQ 均衡器 (libvlc audio equalizer)
- Crossfade (双 MediaPlayer 渐变混合)
- 广泛的格式支持
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional, List, Any, TYPE_CHECKING

from core.audio_engine import AudioEngineBase, PlayerState, PlaybackEndInfo

logger = logging.getLogger(__name__)

# 尝试导入 vlc
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    vlc = None  # type: ignore
    VLC_AVAILABLE = False
    logger.warning("python-vlc 库未安装，VLCEngine 不可用")


class VLCEngine(AudioEngineBase):
    """
    基于 VLC 的音频引擎

    特性:
    - 广泛的格式支持
    - ReplayGain 支持 (通过音量调节)
    - EQ 均衡器 (libvlc AudioEqualizer)
    - Crossfade (双 MediaPlayer 音量渐变)
    """

    @staticmethod
    def probe() -> bool:
        """检测 python-vlc 依赖是否可用"""
        return VLC_AVAILABLE

    def __init__(self):
        if not VLC_AVAILABLE:
            raise ImportError("python-vlc 库未安装")

        super().__init__()

        # VLC 实例
        self._instance: Any = vlc.Instance(
            "--no-video",
            "--audio-filter=scaletempo",
        )
        
        # 主播放器
        self._player: Any = self._instance.media_player_new()
        self._media: Optional[Any] = None

        # 用于 Crossfade 的第二播放器
        self._crossfade_player: Any = self._instance.media_player_new()
        self._crossfade_media: Optional[Any] = None
        self._crossfade_duration_ms: int = 0
        self._crossfade_active: bool = False
        self._crossfade_thread: Optional[threading.Thread] = None
        self._crossfade_stop_event = threading.Event()

        # EQ 相关
        self._eq_enabled: bool = False
        self._eq_bands: List[float] = [0.0] * 10
        self._equalizer: Optional[Any] = None
        self._crossfade_equalizer: Optional[Any] = None

        # ReplayGain
        self._replay_gain_db: float = 0.0

        # 播放状态
        self._duration_ms: int = 0
        self._playback_started: bool = False

        # 下一曲预加载
        self._next_file: Optional[str] = None
        self._next_media: Optional[Any] = None


        # 线程锁
        self._lock = threading.Lock()

        # 设置事件回调
        self._setup_event_callbacks()

    def _setup_event_callbacks(self) -> None:
        """设置 VLC 事件回调"""
        events = self._player.event_manager()

        def on_end_reached(event):
            self._on_playback_finished()

        def on_error(event):
            self._state = PlayerState.ERROR
            if self._on_error_callback:
                self._on_error_callback("VLC 播放错误")

        events.event_attach(vlc.EventType.MediaPlayerEndReached, on_end_reached)
        events.event_attach(vlc.EventType.MediaPlayerEncounteredError, on_error)
        
        # 为 crossfade 播放器也添加事件
        crossfade_events = self._crossfade_player.event_manager()
        crossfade_events.event_attach(vlc.EventType.MediaPlayerEndReached, on_end_reached)

    def _on_playback_finished(self) -> None:
        """播放结束处理"""
        # 如果正在 crossfade，由 crossfade 线程处理
        if self._crossfade_active:
            return
            
        with self._lock:
            self._state = PlayerState.STOPPED
            self._playback_started = False

        if self._on_end_callback:
            self._on_end_callback(
                PlaybackEndInfo(
                    ended_file=self._current_file,
                    next_file=None,
                    reason="ended",
                )
            )

    def load(self, file_path: str) -> bool:
        """加载音频文件"""
        try:
            with self._lock:
                # 停止当前播放和 crossfade
                self._stop_crossfade()
                if self._state == PlayerState.PLAYING:
                    self._player.stop()

                # 创建媒体对象
                self._media = self._instance.media_new(file_path)
                self._player.set_media(self._media)

                # 解析媒体以获取时长
                self._media.parse_with_options(vlc.MediaParseFlag.local, 3000)
                
                # 等待解析完成
                for _ in range(30):
                    if self._media.get_parsed_status() == vlc.MediaParsedStatus.done:
                        break
                    time.sleep(0.1)

                self._current_file = file_path
                self._duration_ms = self._media.get_duration()
                if self._duration_ms < 0:
                    self._duration_ms = 0
                self._state = PlayerState.STOPPED
                self._playback_started = False

                return True

        except Exception as e:
            self._state = PlayerState.ERROR
            logger.error("加载文件失败: %s", e)
            if self._on_error_callback:
                self._on_error_callback(f"加载文件失败: {e}")
            return False

    def play(self) -> bool:
        """开始播放"""
        try:
            with self._lock:
                if self._media is None:
                    return False

                # 应用 EQ
                if self._eq_enabled and self._equalizer:
                    self._player.set_equalizer(self._equalizer)
                else:
                    self._player.set_equalizer(None)

                # 应用音量（包含 ReplayGain）
                self._apply_volume(self._player)

                result = self._player.play()
                if result == 0:
                    self._state = PlayerState.PLAYING
                    self._playback_started = True
                    
                    # 如果有预加载的下一曲且启用了 crossfade，启动监控
                    if self._next_media and self._crossfade_duration_ms > 0:
                        self._start_crossfade_monitor()
                    
                    return True

            return False

        except Exception as e:
            self._state = PlayerState.ERROR
            logger.error("播放失败: %s", e)
            if self._on_error_callback:
                self._on_error_callback(f"播放失败: {e}")
            return False

    def _apply_volume(self, player: Any) -> None:
        """应用音量设置（包含 ReplayGain 调整）"""
        linear_gain = 10 ** (self._replay_gain_db / 20)
        final_volume = int(self._volume * linear_gain * 100)
        final_volume = max(0, min(200, final_volume))
        player.audio_set_volume(final_volume)

    def _start_crossfade_monitor(self) -> None:
        """启动 crossfade 监控线程"""
        if self._crossfade_thread and self._crossfade_thread.is_alive():
            return
        
        self._crossfade_stop_event.clear()
        self._crossfade_thread = threading.Thread(
            target=self._crossfade_monitor_loop,
            daemon=True
        )
        self._crossfade_thread.start()

    def _crossfade_monitor_loop(self) -> None:
        """监控播放位置，在适当时机启动 crossfade"""
        while not self._crossfade_stop_event.is_set():
            try:
                if self._state != PlayerState.PLAYING:
                    time.sleep(0.1)
                    continue
                
                current_pos = self._player.get_time()
                duration = self._duration_ms
                
                if current_pos < 0 or duration <= 0:
                    time.sleep(0.1)
                    continue
                
                remaining = duration - current_pos
                
                # 当剩余时间小于 crossfade 时长时，开始 crossfade
                if remaining <= self._crossfade_duration_ms and self._next_media:
                    self._execute_crossfade()
                    return  # crossfade 完成后退出监控
                
                time.sleep(0.05)  # 50ms 检查间隔
                
            except Exception as e:
                logger.debug("Crossfade 监控错误: %s", e)
                time.sleep(0.1)

    def _execute_crossfade(self) -> None:
        """执行 crossfade 渐变"""
        if self._crossfade_active or not self._next_media:
            return
        
        self._crossfade_active = True
        logger.debug("开始 crossfade 渐变")
        
        try:
            # 设置 crossfade 播放器
            self._crossfade_player.set_media(self._next_media)
            
            # 应用 EQ
            if self._eq_enabled and self._equalizer:
                # 创建新的 equalizer 副本用于 crossfade 播放器
                self._crossfade_equalizer = vlc.AudioEqualizer()
                for i in range(min(10, vlc.libvlc_audio_equalizer_get_band_count())):
                    vlc.libvlc_audio_equalizer_set_amp_at_index(
                        self._crossfade_equalizer, self._eq_bands[i], i
                    )
                self._crossfade_player.set_equalizer(self._crossfade_equalizer)
            
            # 初始音量：主播放器100%，crossfade播放器0%
            main_volume = int(self._volume * 100)
            self._player.audio_set_volume(main_volume)
            self._crossfade_player.audio_set_volume(0)
            
            # 启动 crossfade 播放器
            self._crossfade_player.play()
            
            # 渐变过程
            steps = 50  # 渐变步数
            step_duration = self._crossfade_duration_ms / steps / 1000.0
            
            for i in range(steps + 1):
                if self._crossfade_stop_event.is_set():
                    break
                
                t = i / steps  # 0.0 -> 1.0
                
                # Equal-power crossfade 曲线
                import math
                fade_out = math.cos(t * math.pi / 2)  # 1 -> 0
                fade_in = math.sin(t * math.pi / 2)   # 0 -> 1
                
                main_vol = int(main_volume * fade_out)
                cross_vol = int(main_volume * fade_in)
                
                self._player.audio_set_volume(max(0, main_vol))
                self._crossfade_player.audio_set_volume(max(0, cross_vol))
                
                time.sleep(step_duration)
            
            # Crossfade 完成，切换播放器
            self._finalize_crossfade()
            
        except Exception as e:
            logger.error("Crossfade 执行失败: %s", e)
            self._crossfade_active = False

    def _finalize_crossfade(self) -> None:
        """Finalize crossfade and switch to the new track."""
        ended_file = None
        next_file = None

        with self._lock:
            ended_file = self._current_file
            next_file = self._next_file

            # Stop main player.
            self._player.stop()

            # Swap players/media.
            self._player, self._crossfade_player = self._crossfade_player, self._player
            self._media, self._crossfade_media = self._next_media, self._media

            # Update state.
            self._current_file = self._next_file
            self._duration_ms = self._media.get_duration() if self._media else 0

            # Cleanup.
            self._next_media = None
            self._next_file = None
            self._crossfade_active = False

            # Restore volume.
            self._apply_volume(self._player)

            # Rebind events.
            self._setup_event_callbacks()

            logger.debug("Crossfade complete, switched to new track")

        if self._on_end_callback and next_file:
            self._on_end_callback(
                PlaybackEndInfo(
                    ended_file=ended_file,
                    next_file=next_file,
                    reason="auto_advance",
                )
            )

    def _stop_crossfade(self) -> None:
        """停止 crossfade 过程"""
        self._crossfade_stop_event.set()
        self._crossfade_active = False
        if self._crossfade_thread and self._crossfade_thread.is_alive():
            self._crossfade_thread.join(timeout=1.0)
        try:
            self._crossfade_player.stop()
        except Exception:
            pass

    def pause(self) -> None:
        """暂停播放"""
        with self._lock:
            if self._state == PlayerState.PLAYING:
                self._player.pause()
                if self._crossfade_active:
                    self._crossfade_player.pause()
                self._state = PlayerState.PAUSED

    def resume(self) -> None:
        """恢复播放"""
        with self._lock:
            if self._state == PlayerState.PAUSED:
                self._player.pause()  # VLC 的 pause 是切换操作
                if self._crossfade_active:
                    self._crossfade_player.pause()
                self._state = PlayerState.PLAYING

    def stop(self) -> None:
        """停止播放"""
        with self._lock:
            self._stop_crossfade()
            self._player.stop()
            self._state = PlayerState.STOPPED
            self._playback_started = False

    def seek(self, position_ms: int) -> None:
        """跳转到指定位置"""
        with self._lock:
            if self._duration_ms > 0:
                self._player.set_time(position_ms)

    def set_volume(self, volume: float) -> None:
        """设置音量"""
        self._volume = max(0.0, min(1.0, volume))
        self._apply_volume(self._player)
        if self._crossfade_active:
            self._apply_volume(self._crossfade_player)

    def get_position(self) -> int:
        """获取当前播放位置（毫秒）"""
        pos = self._player.get_time()
        return max(0, pos) if pos >= 0 else 0

    def get_duration(self) -> int:
        """获取音频总时长（毫秒）"""
        return self._duration_ms

    def check_if_ended(self) -> bool:
        """检查播放是否结束"""
        if self._playback_started:
            state = self._player.get_state()
            if state == vlc.State.Ended:
                return True
        return False

    # ===== 高级特性实现 =====

    def supports_gapless(self) -> bool:
        # VLC 不支持真正的 gapless，但 crossfade 可以掩盖间隙
        return False

    def supports_crossfade(self) -> bool:
        return True

    def supports_equalizer(self) -> bool:
        return True

    def supports_replay_gain(self) -> bool:
        return True

    def set_next_track(self, file_path: Optional[str]) -> bool:
        """Preload next track."""
        if not file_path:
            self._stop_crossfade()
            self._next_media = None
            self._next_file = None
            return True

        try:
            self._next_media = self._instance.media_new(file_path)
            self._next_file = file_path

            # If playing and crossfade is enabled, start monitoring.
            if self._state == PlayerState.PLAYING and self._crossfade_duration_ms > 0:
                self._start_crossfade_monitor()

            return True
        except Exception as e:
            logger.warning("Preload next track failed: %s", e)
            return False

    def set_crossfade_duration(self, duration_ms: int) -> None:
        """设置淡入淡出时长"""
        self._crossfade_duration_ms = max(0, duration_ms)

    def get_crossfade_duration(self) -> int:
        return self._crossfade_duration_ms

    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """设置 ReplayGain 增益"""
        self._replay_gain_db = gain_db
        if self._state in (PlayerState.PLAYING, PlayerState.PAUSED):
            self._apply_volume(self._player)

    def set_equalizer(self, bands: List[float]) -> None:
        """设置 EQ 频段增益"""
        if len(bands) < 10:
            return

        self._eq_bands = list(bands[:10])

        # 创建或更新均衡器
        if self._equalizer is None:
            self._equalizer = vlc.AudioEqualizer()

        # 获取 VLC 支持的频段数量
        band_count = vlc.libvlc_audio_equalizer_get_band_count()

        # 设置各频段增益
        for i, gain in enumerate(self._eq_bands):
            if i < band_count:
                vlc.libvlc_audio_equalizer_set_amp_at_index(
                    self._equalizer, gain, i
                )

        # 如果已启用且正在播放，立即应用
        if self._eq_enabled:
            self._player.set_equalizer(self._equalizer)

    def set_equalizer_enabled(self, enabled: bool) -> None:
        """启用/禁用 EQ"""
        self._eq_enabled = enabled

        if enabled and self._equalizer:
            self._player.set_equalizer(self._equalizer)
        else:
            self._player.set_equalizer(None)

    def get_engine_name(self) -> str:
        return "vlc"

    def cleanup(self) -> None:
        """清理资源"""
        with self._lock:
            self._stop_crossfade()
            try:
                self._player.stop()
                self._crossfade_player.stop()
                self._player.release()
                self._crossfade_player.release()
                if self._media:
                    self._media.release()
                if self._crossfade_media:
                    self._crossfade_media.release()
                if self._next_media:
                    self._next_media.release()
                self._instance.release()
            except Exception as e:
                logger.warning("VLC cleanup 失败: %s", e)
