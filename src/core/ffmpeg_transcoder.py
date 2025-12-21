"""
FFmpeg Audio Transcoder

Used for transcoding audio formats not supported by miniaudio to WAV format.
Supported target formats: m4a, aac, wma, ape, opus, etc.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Formats supported natively by miniaudio
MINIAUDIO_NATIVE_FORMATS: Set[str] = {'.mp3', '.flac', '.wav', '.ogg'}

# Formats that can be transcoded via FFmpeg
FFMPEG_TRANSCODABLE_FORMATS: Set[str] = {
    '.m4a', '.aac', '.wma', '.ape', '.opus', '.webm', '.mka', '.ac3', '.dts',
    '.alac', '.aiff', '.aif', '.amr', '.caf', '.mpc', '.tta', '.wv'
}


class FFmpegTranscoder:
    """
    FFmpeg Audio Transcoder
    
    Transcodes non-natively supported audio formats to WAV for playback by miniaudio.
    
    Usage Example:
        transcoder = FFmpegTranscoder()
        if transcoder.is_available():
            wav_data = transcoder.transcode_to_wav("/path/to/audio.m4a")
            # Use miniaudio.decode(wav_data, ...) for playback
    """
    
    _ffmpeg_path: Optional[str] = None
    _checked: bool = False
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if FFmpeg is available
        
        Returns:
            bool: Whether FFmpeg is available
        """
        if not cls._checked:
            cls._ffmpeg_path = cls._find_ffmpeg()
            cls._checked = True
        return cls._ffmpeg_path is not None
    
    @classmethod
    def _find_ffmpeg(cls) -> Optional[str]:
        """Find the FFmpeg executable"""
        # Try to find from PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            logger.debug("FFmpeg found: %s", ffmpeg_path)
            return ffmpeg_path
        
        # Common installation paths on Windows
        if os.name == 'nt':
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\ffmpeg\bin\ffmpeg.exe"),
            ]
            for path in common_paths:
                if os.path.isfile(path):
                    logger.debug("FFmpeg found: %s", path)
                    return path
        
        logger.debug("FFmpeg not found")
        return None
    
    @classmethod
    def get_ffmpeg_path(cls) -> Optional[str]:
        """Get the FFmpeg path"""
        if not cls._checked:
            cls.is_available()
        return cls._ffmpeg_path
    
    @staticmethod
    def is_native_format(file_path: str) -> bool:
        """
        Check if the file is in a format natively supported by miniaudio
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: Whether natively supported
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in MINIAUDIO_NATIVE_FORMATS
    
    @staticmethod
    def is_transcodable(file_path: str) -> bool:
        """
        Check if the file can be transcoded via FFmpeg
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: Whether transcodable
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in FFMPEG_TRANSCODABLE_FORMATS
    
    @classmethod
    def transcode_to_wav(cls, file_path: str, target_sample_rate: int = 44100) -> bytes:
        """
        Transcode an audio file to WAV format
        
        Args:
            file_path: Source file path
            target_sample_rate: Target sample rate
            
        Returns:
            bytes: WAV format audio data
            
        Raises:
            RuntimeError: If FFmpeg is unavailable or transcoding fails
        """
        if not cls.is_available():
            raise RuntimeError("FFmpeg is unavailable")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File does not exist: {file_path}")
        
        ffmpeg_path = cls._ffmpeg_path
        
        # Use a temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Construct FFmpeg command
            # -i: Input file
            # -f wav: Output format is WAV
            # -acodec pcm_f32le: 32-bit float PCM (compatible with miniaudio FLOAT32)
            # -ar: Sample rate
            # -ac 2: Stereo
            # -y: Overwrite output file
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
            
            # Execute transcoding
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,  # 60 second timeout
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace')
                logger.warning("FFmpeg transcoding failed: %s", error_msg[:200])
                raise RuntimeError(f"FFmpeg transcoding failed: {error_msg[:200]}")
            
            # Read the transcoded data
            with open(tmp_path, 'rb') as f:
                wav_data = f.read()
            
            logger.debug("FFmpeg transcoding successful: %s -> %d bytes", file_path, len(wav_data))
            return wav_data
            
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg transcoding timed out: %s", file_path)
            raise RuntimeError(f"FFmpeg transcoding timed out: {file_path}")
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
    
    @classmethod
    def transcode_to_wav_pipe(cls, file_path: str, target_sample_rate: int = 44100) -> bytes:
        """
        Transcode using a pipe (avoids temporary file)
        
        Args:
            file_path: Source file path
            target_sample_rate: Target sample rate
            
        Returns:
            bytes: WAV format audio data
        """
        if not cls.is_available():
            raise RuntimeError("FFmpeg is unavailable")
        
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File does not exist: {file_path}")
        
        ffmpeg_path = cls._ffmpeg_path
        
        # Use pipe for output
        cmd = [
            ffmpeg_path,
            '-i', file_path,
            '-f', 'wav',
            '-acodec', 'pcm_f32le',
            '-ar', str(target_sample_rate),
            '-ac', '2',
            '-'  # Output to stdout
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
                logger.warning("FFmpeg pipe transcoding failed: %s", error_msg[:200])
                raise RuntimeError(f"FFmpeg transcoding failed: {error_msg[:200]}")
            
            logger.debug("FFmpeg pipe transcoding successful: %s -> %d bytes", file_path, len(result.stdout))
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg pipe transcoding timed out: %s", file_path)
            raise RuntimeError(f"FFmpeg transcoding timed out: {file_path}")
