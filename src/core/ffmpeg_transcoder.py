"""
FFmpeg 音频转码器

用于将 miniaudio 不支持的音频格式转码为 WAV 格式。
支持的目标格式：m4a, aac, wma, ape, opus 等。
"""

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional, Set

logger = logging.getLogger(__name__)

# miniaudio 原生支持的格式
MINIAUDIO_NATIVE_FORMATS: Set[str] = {'.mp3', '.flac', '.wav', '.ogg'}

# 可以通过 FFmpeg 转码的格式
FFMPEG_TRANSCODABLE_FORMATS: Set[str] = {
    '.m4a', '.aac', '.wma', '.ape', '.opus', '.webm', '.mka', '.ac3', '.dts',
    '.alac', '.aiff', '.aif', '.amr', '.caf', '.mpc', '.tta', '.wv'
}


class FFmpegTranscoder:
    """
    FFmpeg 音频转码器
    
    将非原生支持的音频格式转码为 WAV 格式，供 miniaudio 播放。
    
    使用示例:
        transcoder = FFmpegTranscoder()
        if transcoder.is_available():
            wav_data = transcoder.transcode_to_wav("/path/to/audio.m4a")
            # 使用 miniaudio.decode(wav_data, ...) 播放
    """
    
    _ffmpeg_path: Optional[str] = None
    _checked: bool = False
    
    @classmethod
    def is_available(cls) -> bool:
        """
        检测 FFmpeg 是否可用
        
        Returns:
            bool: FFmpeg 是否可用
        """
        if not cls._checked:
            cls._ffmpeg_path = cls._find_ffmpeg()
            cls._checked = True
        return cls._ffmpeg_path is not None
    
    @classmethod
    def _find_ffmpeg(cls) -> Optional[str]:
        """查找 FFmpeg 可执行文件"""
        # 尝试从 PATH 中查找
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            logger.debug("找到 FFmpeg: %s", ffmpeg_path)
            return ffmpeg_path
        
        # Windows 常见安装路径
        if os.name == 'nt':
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\ffmpeg\bin\ffmpeg.exe"),
            ]
            for path in common_paths:
                if os.path.isfile(path):
                    logger.debug("找到 FFmpeg: %s", path)
                    return path
        
        logger.debug("未找到 FFmpeg")
        return None
    
    @classmethod
    def get_ffmpeg_path(cls) -> Optional[str]:
        """获取 FFmpeg 路径"""
        if not cls._checked:
            cls.is_available()
        return cls._ffmpeg_path
    
    @staticmethod
    def is_native_format(file_path: str) -> bool:
        """
        检查文件是否为 miniaudio 原生支持的格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否原生支持
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in MINIAUDIO_NATIVE_FORMATS
    
    @staticmethod
    def is_transcodable(file_path: str) -> bool:
        """
        检查文件是否可以通过 FFmpeg 转码
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否可转码
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in FFMPEG_TRANSCODABLE_FORMATS
    
    @classmethod
    def transcode_to_wav(cls, file_path: str, target_sample_rate: int = 44100) -> bytes:
        """
        将音频文件转码为 WAV 格式
        
        Args:
            file_path: 源文件路径
            target_sample_rate: 目标采样率
            
        Returns:
            bytes: WAV 格式的音频数据
            
        Raises:
            RuntimeError: FFmpeg 不可用或转码失败
        """
        if not cls.is_available():
            raise RuntimeError("FFmpeg 不可用")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        ffmpeg_path = cls._ffmpeg_path
        
        # 使用临时文件存储输出
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 构建 FFmpeg 命令
            # -i: 输入文件
            # -f wav: 输出格式为 WAV
            # -acodec pcm_f32le: 32位浮点 PCM（与 miniaudio FLOAT32 兼容）
            # -ar: 采样率
            # -ac 2: 立体声
            # -y: 覆盖输出文件
            cmd = [
                ffmpeg_path,
                '-i', file_path,
                '-f', 'wav',
                '-acodec', 'pcm_f32le',
                '-ar', str(target_sample_rate),
                '-ac', '2',
                '-y',
                tmp_path
            ]
            
            # 执行转码
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,  # 60秒超时
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace')
                logger.warning("FFmpeg 转码失败: %s", error_msg[:200])
                raise RuntimeError(f"FFmpeg 转码失败: {error_msg[:200]}")
            
            # 读取转码后的数据
            with open(tmp_path, 'rb') as f:
                wav_data = f.read()
            
            logger.debug("FFmpeg 转码成功: %s -> %d bytes", file_path, len(wav_data))
            return wav_data
            
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg 转码超时: %s", file_path)
            raise RuntimeError(f"FFmpeg 转码超时: {file_path}")
        finally:
            # 清理临时文件
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
    
    @classmethod
    def transcode_to_wav_pipe(cls, file_path: str, target_sample_rate: int = 44100) -> bytes:
        """
        使用管道方式转码（避免临时文件）
        
        Args:
            file_path: 源文件路径
            target_sample_rate: 目标采样率
            
        Returns:
            bytes: WAV 格式的音频数据
        """
        if not cls.is_available():
            raise RuntimeError("FFmpeg 不可用")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        ffmpeg_path = cls._ffmpeg_path
        
        # 使用管道输出
        cmd = [
            ffmpeg_path,
            '-i', file_path,
            '-f', 'wav',
            '-acodec', 'pcm_f32le',
            '-ar', str(target_sample_rate),
            '-ac', '2',
            '-'  # 输出到 stdout
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace')
                logger.warning("FFmpeg 管道转码失败: %s", error_msg[:200])
                raise RuntimeError(f"FFmpeg 转码失败: {error_msg[:200]}")
            
            logger.debug("FFmpeg 管道转码成功: %s -> %d bytes", file_path, len(result.stdout))
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg 管道转码超时: %s", file_path)
            raise RuntimeError(f"FFmpeg 转码超时: {file_path}")
