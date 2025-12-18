"""
音频引擎模块 - 音频播放核心

提供音频文件的加载、播放、暂停、停止等功能。
支持多后端实现（默认使用pygame）。
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from enum import Enum
import threading
import logging

logger = logging.getLogger(__name__)


class PlayerState(Enum):
    """播放器状态"""
    IDLE = "idle"           # 空闲
    LOADING = "loading"     # 加载中
    PLAYING = "playing"     # 播放中
    PAUSED = "paused"       # 已暂停
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误


class AudioEngineBase(ABC):
    """
    音频引擎抽象基类
    
    定义音频播放的标准接口，具体实现由子类完成。
    """
    
    def __init__(self):
        self._state: PlayerState = PlayerState.IDLE
        self._volume: float = 1.0
        self._current_file: Optional[str] = None
        self._on_end_callback: Optional[Callable] = None
        self._on_error_callback: Optional[Callable[[str], None]] = None
    
    @property
    def state(self) -> PlayerState:
        """获取当前播放状态"""
        return self._state
    
    @property
    def volume(self) -> float:
        """获取当前音量"""
        return self._volume
    
    @property
    def current_file(self) -> Optional[str]:
        """获取当前加载的文件路径"""
        return self._current_file
    
    @abstractmethod
    def load(self, file_path: str) -> bool:
        """
        加载音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            bool: 是否加载成功
        """
        pass
    
    @abstractmethod
    def play(self) -> bool:
        """
        开始播放
        
        Returns:
            bool: 是否成功开始播放
        """
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """暂停播放"""
        pass
    
    @abstractmethod
    def resume(self) -> None:
        """恢复播放"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止播放"""
        pass
    
    @abstractmethod
    def seek(self, position_ms: int) -> None:
        """
        跳转到指定位置
        
        Args:
            position_ms: 目标位置（毫秒）
        """
        pass
    
    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """
        设置音量
        
        Args:
            volume: 音量值 (0.0 - 1.0)
        """
        pass
    
    @abstractmethod
    def get_position(self) -> int:
        """
        获取当前播放位置
        
        Returns:
            int: 当前位置（毫秒）
        """
        pass
    
    @abstractmethod
    def get_duration(self) -> int:
        """
        获取音频总时长
        
        Returns:
            int: 总时长（毫秒）
        """
        pass
    
    @abstractmethod
    def check_if_ended(self) -> bool:
        """
        检查播放是否结束（由主线程定期调用）
        
        Returns:
            bool: 是否播放结束
        """
        pass
    
    def set_on_end(self, callback: Callable) -> None:
        """设置播放结束回调"""
        self._on_end_callback = callback
    
    def set_on_error(self, callback: Callable[[str], None]) -> None:
        """设置错误回调"""
        self._on_error_callback = callback

    # ===== 高级音频特性接口 =====

    def supports_gapless(self) -> bool:
        """
        是否支持无缝播放

        Returns:
            bool: True 表示支持 Gapless Playback
        """
        return False

    def supports_crossfade(self) -> bool:
        """
        是否支持淡入淡出

        Returns:
            bool: True 表示支持 Crossfade
        """
        return False

    def supports_equalizer(self) -> bool:
        """
        是否支持 EQ 均衡器

        Returns:
            bool: True 表示支持 EQ
        """
        return False

    def supports_replay_gain(self) -> bool:
        """
        是否支持 ReplayGain

        Returns:
            bool: True 表示支持 ReplayGain
        """
        return False

    def set_next_track(self, file_path: str) -> bool:
        """
        预加载下一曲（用于 Gapless Playback）

        子类可覆盖此方法实现无缝过渡。

        Args:
            file_path: 下一曲的文件路径

        Returns:
            bool: 是否成功预加载
        """
        return False

    def set_crossfade_duration(self, duration_ms: int) -> None:
        """
        设置淡入淡出时长

        Args:
            duration_ms: 淡入淡出时长（毫秒）
        """
        pass

    def get_crossfade_duration(self) -> int:
        """
        获取当前淡入淡出时长

        Returns:
            int: 淡入淡出时长（毫秒），不支持时返回 0
        """
        return 0

    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """
        设置 ReplayGain 增益

        Args:
            gain_db: 增益值（dB），正值增大音量，负值减小
            peak: 峰值信息，用于防止削波
        """
        pass

    def set_equalizer(self, bands: List[float]) -> None:
        """
        设置 EQ 频段增益

        Args:
            bands: 10 频段增益列表 (dB)，从低频到高频:
                   [31Hz, 62Hz, 125Hz, 250Hz, 500Hz,
                    1kHz, 2kHz, 4kHz, 8kHz, 16kHz]
        """
        pass

    def set_equalizer_enabled(self, enabled: bool) -> None:
        """
        启用/禁用 EQ

        Args:
            enabled: True 启用，False 禁用
        """
        pass

    def get_engine_name(self) -> str:
        """
        获取引擎名称

        Returns:
            str: 引擎标识名称
        """
        return "base"


class PygameAudioEngine(AudioEngineBase):
    """
    基于Pygame的音频引擎实现
    
    使用pygame.mixer进行音频播放，支持大多数常见音频格式。
    """
    
    _initialized = False
    _mixer_refcount = 0
    _lock = threading.Lock()
    
    def __init__(self):
        super().__init__()
        self._duration_ms: int = 0
        self._playback_started = False
        self._cleaned_up = False
        
        # 初始化pygame mixer
        self._acquire_mixer()
    
    def _acquire_mixer(self) -> None:
        """初始化全局 pygame mixer，并用引用计数避免误关。"""
        with PygameAudioEngine._lock:
            if not PygameAudioEngine._initialized:
                try:
                    import pygame
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                    PygameAudioEngine._initialized = True
                except Exception as e:
                    logger.error("pygame初始化失败: %s", e)
                    self._state = PlayerState.ERROR
                    return

            PygameAudioEngine._mixer_refcount += 1
    
    def load(self, file_path: str) -> bool:
        """加载音频文件"""
        try:
            import pygame
            
            # 停止当前播放
            if self._state == PlayerState.PLAYING:
                self.stop()
            
            # 加载新文件
            pygame.mixer.music.load(file_path)
            self._current_file = file_path
            self._state = PlayerState.STOPPED
            self._playback_started = False
            
            # 获取时长
            self._duration_ms = self._get_duration_from_file(file_path)
            
            return True
            
        except Exception as e:
            self._state = PlayerState.ERROR
            if self._on_error_callback:
                self._on_error_callback(f"加载文件失败: {e}")
            return False
    
    def _get_duration_from_file(self, file_path: str) -> int:
        """从文件获取时长"""
        try:
            from mutagen import File
            audio = File(file_path)
            if audio and audio.info:
                return int(audio.info.length * 1000)
        except Exception:
            pass
        return 0
    
    def play(self) -> bool:
        """开始播放"""
        try:
            import pygame
            
            if self._current_file is None:
                return False
            
            pygame.mixer.music.play()
            self._state = PlayerState.PLAYING
            self._playback_started = True
            return True
            
        except Exception as e:
            self._state = PlayerState.ERROR
            if self._on_error_callback:
                self._on_error_callback(f"播放失败: {e}")
            return False
    
    def pause(self) -> None:
        """暂停播放"""
        import pygame
        
        if self._state == PlayerState.PLAYING:
            pygame.mixer.music.pause()
            self._state = PlayerState.PAUSED
    
    def resume(self) -> None:
        """恢复播放"""
        import pygame
        
        if self._state == PlayerState.PAUSED:
            pygame.mixer.music.unpause()
            self._state = PlayerState.PLAYING
    
    def stop(self) -> None:
        """停止播放"""
        import pygame
        
        pygame.mixer.music.stop()
        self._state = PlayerState.STOPPED
        self._playback_started = False
    
    def seek(self, position_ms: int) -> None:
        """跳转到指定位置"""
        import pygame
        
        try:
            # pygame的set_pos接受秒为单位
            pygame.mixer.music.set_pos(position_ms / 1000.0)
        except Exception as e:
            logger.warning("跳转失败: %s", e)
    
    def set_volume(self, volume: float) -> None:
        """设置音量"""
        import pygame
        
        self._volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._volume)
    
    def get_position(self) -> int:
        """获取当前播放位置"""
        import pygame
        
        if self._state in (PlayerState.PLAYING, PlayerState.PAUSED):
            pos = pygame.mixer.music.get_pos()
            return max(0, pos)  # 返回非负值
        return 0
    
    def get_duration(self) -> int:
        """获取音频总时长"""
        return self._duration_ms
    
    def check_if_ended(self) -> bool:
        """
        检查播放是否结束
        
        由主线程定期调用，确保线程安全。
        """
        import pygame
        
        if self._playback_started and self._state == PlayerState.PLAYING:
            try:
                busy = pygame.mixer.music.get_busy()
            except Exception as e:
                logger.warning("pygame mixer 未初始化，无法检查播放状态: %s", e)
                self._state = PlayerState.ERROR
                self._playback_started = False
                return False

            if not busy:
                self._state = PlayerState.STOPPED
                self._playback_started = False
                return True
        return False
    
    def cleanup(self) -> None:
        """清理资源"""
        import pygame

        with PygameAudioEngine._lock:
            if self._cleaned_up:
                return
            self._cleaned_up = True

            if PygameAudioEngine._mixer_refcount > 0:
                PygameAudioEngine._mixer_refcount -= 1

            should_quit = PygameAudioEngine._initialized and PygameAudioEngine._mixer_refcount == 0

        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        if should_quit:
            try:
                pygame.mixer.quit()
            except Exception as e:
                logger.warning("pygame cleanup 失败: %s", e)
            finally:
                with PygameAudioEngine._lock:
                    PygameAudioEngine._initialized = False

    def get_engine_name(self) -> str:
        """获取引擎名称"""
        return "pygame"

