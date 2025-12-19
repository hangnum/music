"""
miniaudio 音频引擎实现

基于 miniaudio 库的高质量音频后端，支持:
- Gapless Playback (Data Source Chaining)
- Crossfade (音量渐变混合)
- 10 频段 EQ (Biquad Filter)
- ReplayGain (增益调整)
"""

import logging
import threading
import math
import array
from typing import Optional, List

from core.audio_engine import AudioEngineBase, PlayerState, PlaybackEndInfo

logger = logging.getLogger(__name__)

# 尝试导入 miniaudio
try:
    import miniaudio
    MINIAUDIO_AVAILABLE = True
except ImportError:
    MINIAUDIO_AVAILABLE = False
    logger.warning("miniaudio 库未安装，MiniaudioEngine 不可用")


# ===== 10 频段 EQ Biquad 滤波器实现 =====

# EQ 频段中心频率 (Hz)
EQ_FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


class BiquadFilter:
    """
    Biquad 滤波器 - 用于 EQ 频段处理
    
    实现峰值/凹陷 EQ (peaking EQ) 滤波器
    """
    
    def __init__(self, sample_rate: int, frequency: float, gain_db: float, q: float = 1.4):
        """
        初始化 Biquad 滤波器
        
        Args:
            sample_rate: 采样率
            frequency: 中心频率 (Hz)
            gain_db: 增益 (dB)
            q: Q 因子，控制带宽
        """
        self.sample_rate = sample_rate
        self.frequency = frequency
        self.gain_db = gain_db
        self.q = q
        
        # 滤波器状态 (每声道独立)
        self.x1_l = 0.0
        self.x2_l = 0.0
        self.y1_l = 0.0
        self.y2_l = 0.0
        self.x1_r = 0.0
        self.x2_r = 0.0
        self.y1_r = 0.0
        self.y2_r = 0.0
        
        # 计算滤波器系数
        self._calculate_coefficients()
    
    def _calculate_coefficients(self) -> None:
        """计算 Biquad 滤波器系数"""
        if self.gain_db == 0.0:
            # 无增益时使用直通
            self.b0 = 1.0
            self.b1 = 0.0
            self.b2 = 0.0
            self.a1 = 0.0
            self.a2 = 0.0
            return
        
        A = 10 ** (self.gain_db / 40)  # 使用 40 而非 20 用于 peaking EQ
        omega = 2 * math.pi * self.frequency / self.sample_rate
        sin_omega = math.sin(omega)
        cos_omega = math.cos(omega)
        alpha = sin_omega / (2 * self.q)
        
        # Peaking EQ 系数
        b0 = 1 + alpha * A
        b1 = -2 * cos_omega
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_omega
        a2 = 1 - alpha / A
        
        # 归一化
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0
    
    def set_gain(self, gain_db: float) -> None:
        """更新增益并重新计算系数"""
        if self.gain_db != gain_db:
            self.gain_db = gain_db
            self._calculate_coefficients()
    
    def process_stereo(self, samples: array.array) -> array.array:
        """
        处理立体声采样数据
        
        Args:
            samples: 交错的立体声采样 [L, R, L, R, ...]
            
        Returns:
            处理后的采样数据
        """
        if self.gain_db == 0.0:
            return samples
        
        result = array.array('f', [0.0] * len(samples))
        
        for i in range(0, len(samples), 2):
            # 左声道
            x0_l = samples[i]
            y0_l = (self.b0 * x0_l + self.b1 * self.x1_l + self.b2 * self.x2_l
                    - self.a1 * self.y1_l - self.a2 * self.y2_l)
            self.x2_l = self.x1_l
            self.x1_l = x0_l
            self.y2_l = self.y1_l
            self.y1_l = y0_l
            result[i] = y0_l
            
            # 右声道
            if i + 1 < len(samples):
                x0_r = samples[i + 1]
                y0_r = (self.b0 * x0_r + self.b1 * self.x1_r + self.b2 * self.x2_r
                        - self.a1 * self.y1_r - self.a2 * self.y2_r)
                self.x2_r = self.x1_r
                self.x1_r = x0_r
                self.y2_r = self.y1_r
                self.y1_r = y0_r
                result[i + 1] = y0_r
        
        return result
    
    def reset(self) -> None:
        """重置滤波器状态"""
        self.x1_l = self.x2_l = self.y1_l = self.y2_l = 0.0
        self.x1_r = self.x2_r = self.y1_r = self.y2_r = 0.0


class EqualizerProcessor:
    """
    10 频段 EQ 处理器
    
    使用级联 Biquad 滤波器实现
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.enabled = False
        self.filters: List[BiquadFilter] = []
        self._init_filters()
    
    def _init_filters(self) -> None:
        """初始化 10 个频段滤波器"""
        self.filters = [
            BiquadFilter(self.sample_rate, freq, 0.0)
            for freq in EQ_FREQUENCIES
        ]
    
    def set_bands(self, bands: List[float]) -> None:
        """设置各频段增益"""
        for i, gain in enumerate(bands[:10]):
            if i < len(self.filters):
                self.filters[i].set_gain(gain)
    
    def set_sample_rate(self, sample_rate: int) -> None:
        """更新采样率"""
        if self.sample_rate != sample_rate:
            self.sample_rate = sample_rate
            # 重新创建滤波器
            bands = [f.gain_db for f in self.filters]
            self._init_filters()
            self.set_bands(bands)
    
    def process(self, samples: array.array) -> array.array:
        """
        处理音频数据
        
        Args:
            samples: 立体声交错采样
            
        Returns:
            EQ 处理后的采样
        """
        if not self.enabled:
            return samples
        
        # 级联处理每个频段
        result = samples
        for filt in self.filters:
            if filt.gain_db != 0.0:
                result = filt.process_stereo(result)
        
        return result
    
    def reset(self) -> None:
        """重置所有滤波器状态"""
        for filt in self.filters:
            filt.reset()


class MiniaudioEngine(AudioEngineBase):
    """
    基于 miniaudio 的高质量音频引擎

    特性:
    - 支持 Gapless Playback
    - 支持 Crossfade (真实实现)
    - 支持 10 频段 EQ (Biquad 滤波器)
    - 支持 ReplayGain
    """

    @staticmethod
    def probe() -> bool:
        """检测 miniaudio 依赖是否可用"""
        return MINIAUDIO_AVAILABLE

    def __init__(self):
        if not MINIAUDIO_AVAILABLE:
            raise ImportError("miniaudio 库未安装")

        super().__init__()

        # miniaudio 设备和解码器
        self._device: Optional[miniaudio.PlaybackDevice] = None
        self._decoded_audio: Optional[miniaudio.DecodedSoundFile] = None

        # 播放状态
        self._duration_ms: int = 0
        self._position_samples: int = 0
        self._sample_rate: int = 44100
        self._channels: int = 2
        self._playback_started: bool = False
        self._is_crossfading: bool = False

        # Crossfade 相关
        self._crossfade_duration_ms: int = 0
        self._crossfade_samples: int = 0
        self._crossfade_position: int = 0
        self._outgoing_audio: Optional[miniaudio.DecodedSoundFile] = None
        self._outgoing_position: int = 0

        # EQ 处理器
        self._eq_processor = EqualizerProcessor(self._sample_rate)

        # ReplayGain
        self._replay_gain_db: float = 0.0
        self._replay_gain_peak: float = 1.0

        # 下一曲预加载 (gapless)
        self._next_file: Optional[str] = None
        self._next_decoded: Optional[miniaudio.DecodedSoundFile] = None
        self._next_crossfade_allowed: bool = True

        # 线程锁
        self._lock = threading.Lock()

        # 初始化设备
        self._init_device()

    def _init_device(self) -> None:
        """初始化音频设备"""
        try:
            self._device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=2,
                sample_rate=44100,
            )
            self._sample_rate = 44100
            self._channels = 2
            self._eq_processor.set_sample_rate(44100)
            logger.info("miniaudio 设备初始化成功")
        except Exception as e:
            logger.error("miniaudio 设备初始化失败: %s", e)
            self._state = PlayerState.ERROR

    def _reinit_device_if_needed(self, target_sample_rate: int) -> None:
        """如果采样率变化，重建播放设备以匹配音源采样率"""
        if self._sample_rate == target_sample_rate:
            return
        
        if self._device:
            try:
                self._device.close()
            except Exception:
                pass
        
        try:
            self._device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=2,
                sample_rate=target_sample_rate,
            )
            self._sample_rate = target_sample_rate
            self._eq_processor.set_sample_rate(target_sample_rate)
            logger.info("miniaudio 设备重建，采样率: %d", target_sample_rate)
        except Exception as e:
            logger.error("miniaudio 设备重建失败: %s", e)
            self._state = PlayerState.ERROR

    def load(self, file_path: str) -> bool:
        """加载音频文件"""
        try:
            with self._lock:
                # 停止当前播放
                if self._state == PlayerState.PLAYING:
                    self._stop_internal()

                # 解码音频文件
                try:
                    self._decoded_audio = miniaudio.decode_file(
                        file_path,
                        output_format=miniaudio.SampleFormat.FLOAT32,
                        nchannels=2,
                    )
                except Exception as e:
                    logger.debug("miniaudio decode_file failed, retrying in-memory: %s", e)
                    try:
                        with open(file_path, "rb") as audio_file:
                            data = audio_file.read()
                        self._decoded_audio = miniaudio.decode(
                            data,
                            output_format=miniaudio.SampleFormat.FLOAT32,
                            nchannels=2,
                        )
                    except Exception as inner_error:
                        logger.warning("miniaudio decode failed: %s", inner_error)
                        raise

                # 检查并重建设备以匹配音源采样率（P0-2 修复）
                self._reinit_device_if_needed(self._decoded_audio.sample_rate)

                self._current_file = file_path
                self._sample_rate = self._decoded_audio.sample_rate
                self._channels = self._decoded_audio.nchannels
                self._duration_ms = int(
                    len(self._decoded_audio.samples)
                    / self._channels
                    / self._sample_rate
                    * 1000
                )
                self._position_samples = 0
                self._state = PlayerState.STOPPED
                self._playback_started = False
                self._is_crossfading = False

                # 更新 EQ 采样率
                self._eq_processor.set_sample_rate(self._sample_rate)
                self._eq_processor.reset()

                # 更新 crossfade 采样数
                self._crossfade_samples = int(
                    self._crossfade_duration_ms / 1000.0 * self._sample_rate
                )

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
                if self._decoded_audio is None:
                    return False

                if self._device is None:
                    self._init_device()
                    if self._device is None:
                        return False

                # 重置 EQ 滤波器状态
                self._eq_processor.reset()

                # 创建流生成器
                stream = self._create_stream()

                # 启动播放
                self._device.start(stream)
                self._state = PlayerState.PLAYING
                self._playback_started = True

                return True

        except Exception as e:
            self._state = PlayerState.ERROR
            logger.error("播放失败: %s", e)
            if self._on_error_callback:
                self._on_error_callback(f"播放失败: {e}")
            return False

    def _create_stream(self):
        """创建音频流生成器 - 包含完整的音频处理链"""
        samples = self._decoded_audio.samples
        channels = self._channels
        
        # Current position in frames.
        position = self._position_samples
        total_samples = len(samples)
        total_frames = total_samples // channels
        crossfade_frames = self._crossfade_samples
        crossfade_start_frame = (
            total_frames - crossfade_frames if crossfade_frames > 0 else total_frames
        )
        
        # EQ processor reference.
        eq_processor = self._eq_processor
        
        # Capture self for the closure.
        engine = self

        def stream_generator():
            nonlocal position, samples, channels, total_samples, total_frames, crossfade_frames, crossfade_start_frame
            
            framecount = yield
            
            while True:
                while position < total_frames:
                    start = position * channels
                    requested_frames = framecount or 1024
                    end = min(start + requested_frames * channels, total_samples)

                    if start >= total_samples:
                        break

                    # Raw samples.
                    chunk = array.array('f', samples[start:end])
                    chunk_frames = len(chunk) // channels

                    # Check crossfade window.
                    in_crossfade = (crossfade_frames > 0 and 
                                   position >= crossfade_start_frame and 
                                   engine._next_decoded is not None and 
                                   engine._next_crossfade_allowed)

                    # 1. EQ (skip during crossfade).
                    if eq_processor.enabled and not in_crossfade:
                        chunk = eq_processor.process(chunk)

                    # 2. Gain (ReplayGain + volume).
                    base_gain = engine._volume * (10 ** (engine._replay_gain_db / 20))
                    max_gain = 1.0 / engine._replay_gain_peak if engine._replay_gain_peak > 0 else 1.0
                    gain = min(base_gain, max_gain)
                    
                    if gain != 1.0:
                        for i in range(len(chunk)):
                            chunk[i] *= gain

                    # 3. Crossfade mixing.
                    if in_crossfade:
                        chunk = engine._apply_crossfade(
                            chunk, position, crossfade_start_frame, 
                            crossfade_frames, channels, gain
                        )

                    # Update position.
                    position += chunk_frames
                    self._position_samples = position

                    framecount = yield chunk

                ended_file, next_file, auto_advanced, stop_device = self._on_playback_finished()

                if not auto_advanced and stop_device and self._device:
                    try:
                        self._device.stop()
                    except Exception:
                        pass

                if self._on_end_callback:
                    reason = "auto_advance" if auto_advanced else "ended"
                    self._on_end_callback(
                        PlaybackEndInfo(
                            ended_file=ended_file,
                            next_file=next_file,
                            reason=reason,
                        )
                    )

                if not auto_advanced:
                    return

                samples = self._decoded_audio.samples
                channels = self._channels
                position = self._position_samples
                total_samples = len(samples)
                total_frames = total_samples // channels
                crossfade_frames = engine._crossfade_samples
                crossfade_start_frame = (
                    total_frames - crossfade_frames if crossfade_frames > 0 else total_frames
                )

        generator = stream_generator()
        next(generator)
        return generator

    def _apply_crossfade(
        self, 
        outgoing_chunk: array.array,
        position: int,
        crossfade_start: int,
        crossfade_frames: int,
        channels: int,
        gain: float
    ) -> array.array:
        """
        应用 Crossfade 混合
        
        注意：EQ 在混合后统一应用，避免滤波器状态在两个音频流之间串扰。
        
        Args:
            outgoing_chunk: 当前曲目的音频块（正在淡出，已应用 EQ）
            position: 当前播放位置（帧）
            crossfade_start: crossfade 开始位置（帧）
            crossfade_frames: crossfade 总帧数
            channels: 声道数
            gain: 当前增益
            
        Returns:
            混合后的音频块
        """
        next_samples = self._next_decoded.samples
        next_total = len(next_samples)
        chunk_frames = len(outgoing_chunk) // channels
        
        # 计算在 crossfade 区域的位置
        crossfade_pos = position - crossfade_start
        
        # 计算下一曲的起始位置（从头开始）
        next_start = crossfade_pos * channels
        next_end = min(next_start + len(outgoing_chunk), next_total)
        
        if next_start >= next_total:
            return outgoing_chunk
        
        # 获取下一曲的采样（不单独应用 EQ，避免滤波器状态串扰）
        incoming_chunk = array.array('f', next_samples[next_start:next_end])
        
        # 仅应用增益到下一曲（EQ 将在混合后统一应用）
        if gain != 1.0:
            for i in range(len(incoming_chunk)):
                incoming_chunk[i] *= gain
        
        # 混合两个音频块
        result = array.array('f', [0.0] * len(outgoing_chunk))
        
        for i in range(len(outgoing_chunk)):
            frame_in_crossfade = crossfade_pos + (i // channels)
            
            # 计算淡入淡出系数 (使用 equal-power crossfade)
            if crossfade_frames > 0:
                t = min(1.0, frame_in_crossfade / crossfade_frames)
            else:
                t = 1.0
            
            # Equal-power crossfade: 使用 sin/cos 曲线
            fade_out = math.cos(t * math.pi / 2)  # 1 -> 0
            fade_in = math.sin(t * math.pi / 2)   # 0 -> 1
            
            outgoing_sample = outgoing_chunk[i]
            incoming_sample = incoming_chunk[i] if i < len(incoming_chunk) else 0.0
            
            result[i] = outgoing_sample * fade_out + incoming_sample * fade_in
        
        # 混合后统一应用 EQ（如果启用）
        # 注意：outgoing_chunk 已经在 _create_stream 中应用了 EQ，
        # 但这里我们对混合后的结果重新应用，以保持 EQ 处理的一致性
        # 由于 crossfade 期间两个流已经混合，只需对结果应用一次 EQ
        if self._eq_processor.enabled:
            result = self._eq_processor.process(result)
        
        return result

    def _on_playback_finished(self) -> tuple[Optional[str], Optional[str], bool, bool]:
        """Playback finished handling."""
        ended_file = None
        next_file = None
        auto_advanced = False
        stop_device = False

        with self._lock:
            ended_file = self._current_file
            self._is_crossfading = False

            can_auto_advance = (
                self._next_decoded is not None
                and self._next_crossfade_allowed
                and self._next_decoded.sample_rate == self._sample_rate
            )

            if can_auto_advance:
                next_decoded = self._next_decoded
                next_file = self._next_file
                had_crossfade = self._crossfade_duration_ms > 0 and self._next_crossfade_allowed

                # Clear preloaded state before switching.
                self._next_decoded = None
                self._next_file = None
                self._next_crossfade_allowed = True

                self._decoded_audio = next_decoded
                self._current_file = next_file
                self._sample_rate = self._decoded_audio.sample_rate
                self._channels = self._decoded_audio.nchannels
                self._duration_ms = int(
                    len(self._decoded_audio.samples)
                    / self._channels
                    / self._sample_rate
                    * 1000
                )

                # Align position if crossfade already played part of the next track.
                self._position_samples = self._crossfade_samples if had_crossfade else 0

                # Refresh EQ and crossfade values for the new track.
                self._eq_processor.set_sample_rate(self._sample_rate)
                self._eq_processor.reset()
                self._crossfade_samples = int(
                    self._crossfade_duration_ms / 1000.0 * self._sample_rate
                )

                self._state = PlayerState.PLAYING
                self._playback_started = True
                auto_advanced = True
            else:
                if self._next_decoded is not None and not can_auto_advance:
                    logger.info(
                        "Auto-advance disabled due to sample rate mismatch: %d -> %d",
                        self._sample_rate,
                        self._next_decoded.sample_rate,
                    )

                # Clear preloaded state since we cannot auto-advance.
                self._next_decoded = None
                self._next_file = None
                self._next_crossfade_allowed = True

                self._state = PlayerState.STOPPED
                self._playback_started = False
                stop_device = True

        return ended_file, (next_file if auto_advanced else None), auto_advanced, stop_device

    def pause(self) -> None:
        """暂停播放"""
        with self._lock:
            if self._state == PlayerState.PLAYING and self._device:
                self._device.stop()
                self._state = PlayerState.PAUSED

    def resume(self) -> None:
        """恢复播放"""
        with self._lock:
            if self._state == PlayerState.PAUSED:
                if self._decoded_audio and self._device:
                    stream = self._create_stream()
                    self._device.start(stream)
                    self._state = PlayerState.PLAYING

    def stop(self) -> None:
        """停止播放"""
        with self._lock:
            self._stop_internal()

    def _stop_internal(self) -> None:
        """内部停止方法（无锁）"""
        if self._device:
            try:
                self._device.stop()
            except Exception:
                pass
        self._state = PlayerState.STOPPED
        self._playback_started = False
        self._position_samples = 0
        self._is_crossfading = False

    def seek(self, position_ms: int) -> None:
        """跳转到指定位置"""
        with self._lock:
            if self._decoded_audio:
                self._position_samples = int(
                    position_ms / 1000.0 * self._sample_rate
                )
                self._eq_processor.reset()
                
                if self._state == PlayerState.PLAYING:
                    self._device.stop()
                    stream = self._create_stream()
                    self._device.start(stream)

    def set_volume(self, volume: float) -> None:
        """设置音量"""
        self._volume = max(0.0, min(1.0, volume))

    def get_position(self) -> int:
        """获取当前播放位置（毫秒）"""
        if self._sample_rate > 0:
            return int(self._position_samples / self._sample_rate * 1000)
        return 0

    def get_duration(self) -> int:
        """获取音频总时长（毫秒）"""
        return self._duration_ms

    def check_if_ended(self) -> bool:
        """检查播放是否结束"""
        if self._playback_started and self._state == PlayerState.PLAYING:
            if self._decoded_audio:
                total_samples = len(self._decoded_audio.samples) // self._channels
                if self._position_samples >= total_samples:
                    return True
        return False

    # ===== 高级特性实现 =====

    def supports_gapless(self) -> bool:
        return True

    def supports_crossfade(self) -> bool:
        return True

    def supports_equalizer(self) -> bool:
        return True

    def supports_replay_gain(self) -> bool:
        return True

    def set_next_track(self, file_path: Optional[str]) -> bool:
        """Preload next track for gapless/crossfade playback."""
        if not file_path:
            self._next_decoded = None
            self._next_file = None
            self._next_crossfade_allowed = True
            return True

        try:
            try:
                decoded = miniaudio.decode_file(
                    file_path,
                    output_format=miniaudio.SampleFormat.FLOAT32,
                    nchannels=2,
                )
            except Exception as e:
                logger.debug("miniaudio decode_file failed, retrying in-memory: %s", e)
                try:
                    with open(file_path, "rb") as audio_file:
                        data = audio_file.read()
                    decoded = miniaudio.decode(
                        data,
                        output_format=miniaudio.SampleFormat.FLOAT32,
                        nchannels=2,
                    )
                except Exception as inner_error:
                    logger.warning("miniaudio decode failed: %s", inner_error)
                    raise
            self._next_decoded = decoded
            self._next_file = file_path

            # Avoid crossfade mixing when sample rates differ.
            self._next_crossfade_allowed = (
                self._sample_rate == decoded.sample_rate
            )
            if self._crossfade_duration_ms > 0 and not self._next_crossfade_allowed:
                logger.info(
                    "Crossfade disabled due to sample rate mismatch: %d -> %d",
                    self._sample_rate,
                    decoded.sample_rate,
                )

            logger.debug("Preloaded next track: %s", file_path)
            return True
        except Exception as e:
            logger.warning("Preload next track failed: %s", e)
            return False

    def set_crossfade_duration(self, duration_ms: int) -> None:
        """设置淡入淡出时长"""
        self._crossfade_duration_ms = max(0, duration_ms)
        self._crossfade_samples = int(
            self._crossfade_duration_ms / 1000.0 * self._sample_rate
        )

    def get_crossfade_duration(self) -> int:
        return self._crossfade_duration_ms

    def set_replay_gain(self, gain_db: float, peak: float = 1.0) -> None:
        """设置 ReplayGain 增益"""
        self._replay_gain_db = gain_db
        self._replay_gain_peak = max(0.001, peak)

    def set_equalizer(self, bands: List[float]) -> None:
        """设置 EQ 频段增益"""
        if len(bands) >= 10:
            self._eq_processor.set_bands(bands[:10])

    def set_equalizer_enabled(self, enabled: bool) -> None:
        """启用/禁用 EQ"""
        self._eq_processor.enabled = enabled

    def get_engine_name(self) -> str:
        return "miniaudio"

    def cleanup(self) -> None:
        """清理资源"""
        with self._lock:
            self._stop_internal()
            if self._device:
                try:
                    self._device.close()
                except Exception as e:
                    logger.warning("miniaudio cleanup 失败: %s", e)
                self._device = None
            self._decoded_audio = None
            self._next_decoded = None
