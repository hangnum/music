"""
FFmpeg 转码器测试

测试 FFmpegTranscoder 的格式判断和可用性检测功能。
"""

import pytest
from unittest.mock import patch, MagicMock

from core.ffmpeg_transcoder import (
    FFmpegTranscoder,
    MINIAUDIO_NATIVE_FORMATS,
    FFMPEG_TRANSCODABLE_FORMATS
)


class TestFFmpegTranscoder:
    """FFmpeg 转码器测试套件"""
    
    def setup_method(self):
        """每个测试前重置类状态"""
        FFmpegTranscoder._checked = False
        FFmpegTranscoder._ffmpeg_path = None
    
    # --- 静态格式判断测试 ---
    
    def test_is_native_format_mp3(self):
        """测试 MP3 是原生支持格式"""
        assert FFmpegTranscoder.is_native_format("song.mp3") is True
        assert FFmpegTranscoder.is_native_format("path/to/song.MP3") is True
    
    def test_is_native_format_flac(self):
        """测试 FLAC 是原生支持格式"""
        assert FFmpegTranscoder.is_native_format("song.flac") is True
    
    def test_is_native_format_wav(self):
        """测试 WAV 是原生支持格式"""
        assert FFmpegTranscoder.is_native_format("song.wav") is True
    
    def test_is_native_format_ogg(self):
        """测试 OGG 是原生支持格式"""
        assert FFmpegTranscoder.is_native_format("song.ogg") is True
    
    def test_is_native_format_m4a_false(self):
        """测试 M4A 不是原生支持格式"""
        assert FFmpegTranscoder.is_native_format("song.m4a") is False
    
    def test_is_transcodable_m4a(self):
        """测试 M4A 是可转码格式"""
        assert FFmpegTranscoder.is_transcodable("song.m4a") is True
    
    def test_is_transcodable_aac(self):
        """测试 AAC 是可转码格式"""
        assert FFmpegTranscoder.is_transcodable("song.aac") is True
    
    def test_is_transcodable_wma(self):
        """测试 WMA 是可转码格式"""
        assert FFmpegTranscoder.is_transcodable("song.wma") is True
    
    def test_is_transcodable_ape(self):
        """测试 APE 是可转码格式"""
        assert FFmpegTranscoder.is_transcodable("song.ape") is True
    
    def test_is_transcodable_opus(self):
        """测试 Opus 是可转码格式"""
        assert FFmpegTranscoder.is_transcodable("song.opus") is True
    
    def test_is_transcodable_mp3_false(self):
        """测试 MP3 不是可转码格式（已原生支持）"""
        assert FFmpegTranscoder.is_transcodable("song.mp3") is False
    
    def test_is_transcodable_txt_false(self):
        """测试 TXT 不是可转码格式"""
        assert FFmpegTranscoder.is_transcodable("file.txt") is False
    
    # --- 常量验证 ---
    
    def test_native_formats_not_empty(self):
        """验证原生格式集合非空"""
        assert len(MINIAUDIO_NATIVE_FORMATS) > 0
        assert ".mp3" in MINIAUDIO_NATIVE_FORMATS
        assert ".flac" in MINIAUDIO_NATIVE_FORMATS
    
    def test_transcodable_formats_not_empty(self):
        """验证可转码格式集合非空"""
        assert len(FFMPEG_TRANSCODABLE_FORMATS) > 0
        assert ".m4a" in FFMPEG_TRANSCODABLE_FORMATS
        assert ".aac" in FFMPEG_TRANSCODABLE_FORMATS
    
    def test_no_format_overlap(self):
        """验证原生格式和可转码格式不重叠"""
        overlap = MINIAUDIO_NATIVE_FORMATS & FFMPEG_TRANSCODABLE_FORMATS
        assert len(overlap) == 0, f"格式重叠: {overlap}"
    
    # --- 可用性检测测试 (Mock) ---
    
    @patch('shutil.which')
    def test_is_available_when_in_path(self, mock_which):
        """测试 FFmpeg 在 PATH 中时返回 True"""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        result = FFmpegTranscoder.is_available()
        
        assert result is True
        assert FFmpegTranscoder._ffmpeg_path == "/usr/bin/ffmpeg"
    
    @patch('shutil.which')
    @patch('os.path.isfile')
    def test_is_available_when_not_found(self, mock_isfile, mock_which):
        """测试 FFmpeg 未找到时返回 False"""
        mock_which.return_value = None
        mock_isfile.return_value = False
        
        result = FFmpegTranscoder.is_available()
        
        assert result is False
        assert FFmpegTranscoder._ffmpeg_path is None
    
    @patch('shutil.which')
    def test_is_available_caches_result(self, mock_which):
        """测试可用性检测结果被缓存"""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        # 第一次调用
        FFmpegTranscoder.is_available()
        call_count_1 = mock_which.call_count
        
        # 第二次调用应使用缓存
        FFmpegTranscoder.is_available()
        call_count_2 = mock_which.call_count
        
        assert call_count_1 == call_count_2  # 没有额外调用
    
    @patch('shutil.which')
    def test_get_ffmpeg_path(self, mock_which):
        """测试获取 FFmpeg 路径"""
        mock_which.return_value = "/opt/ffmpeg/bin/ffmpeg"
        
        path = FFmpegTranscoder.get_ffmpeg_path()
        
        assert path == "/opt/ffmpeg/bin/ffmpeg"
    
    # --- 转码方法测试 (仅测试前置条件) ---
    
    @patch('shutil.which')
    @patch('os.path.isfile')
    def test_transcode_raises_when_unavailable(self, mock_isfile, mock_which):
        """测试 FFmpeg 不可用时抛出 RuntimeError"""
        mock_which.return_value = None
        mock_isfile.return_value = False
        
        with pytest.raises(RuntimeError, match="FFmpeg 不可用"):
            FFmpegTranscoder.transcode_to_wav("test.m4a")
    
    @patch('shutil.which')
    def test_transcode_raises_when_file_not_found(self, mock_which):
        """测试文件不存在时抛出 FileNotFoundError"""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        with pytest.raises(FileNotFoundError):
            FFmpegTranscoder.transcode_to_wav("nonexistent_file.m4a")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
