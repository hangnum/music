"""
FFmpeg Transcoder Tests

Tests for format determination and availability detection in FFmpegTranscoder.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.ffmpeg_transcoder import (
    FFmpegTranscoder,
    MINIAUDIO_NATIVE_FORMATS,
    FFMPEG_TRANSCODABLE_FORMATS
)


class TestFFmpegTranscoder:
    """FFmpeg Transcoder Test Suite."""
    
    def setup_method(self):
        """Reset class state before each test."""
        FFmpegTranscoder._checked = False
        FFmpegTranscoder._ffmpeg_path = None
    
    # --- Static Format Determination Tests ---
    
    def test_is_native_format_mp3(self):
        """Test that MP3 is a natively supported format."""
        assert FFmpegTranscoder.is_native_format("song.mp3") is True
        assert FFmpegTranscoder.is_native_format("path/to/song.MP3") is True
    
    def test_is_native_format_flac(self):
        """Test that FLAC is a natively supported format."""
        assert FFmpegTranscoder.is_native_format("song.flac") is True
    
    def test_is_native_format_wav(self):
        """Test that WAV is a natively supported format."""
        assert FFmpegTranscoder.is_native_format("song.wav") is True
    
    def test_is_native_format_ogg(self):
        """Test that OGG is a natively supported format."""
        assert FFmpegTranscoder.is_native_format("song.ogg") is True
    
    def test_is_native_format_m4a_false(self):
        """Test that M4A is not a natively supported format."""
        assert FFmpegTranscoder.is_native_format("song.m4a") is False
    
    def test_is_transcodable_m4a(self):
        """Test that M4A is a transcodable format."""
        assert FFmpegTranscoder.is_transcodable("song.m4a") is True
    
    def test_is_transcodable_aac(self):
        """Test that AAC is a transcodable format."""
        assert FFmpegTranscoder.is_transcodable("song.aac") is True
    
    def test_is_transcodable_wma(self):
        """Test that WMA is a transcodable format."""
        assert FFmpegTranscoder.is_transcodable("song.wma") is True
    
    def test_is_transcodable_ape(self):
        """Test that APE is a transcodable format."""
        assert FFmpegTranscoder.is_transcodable("song.ape") is True
    
    def test_is_transcodable_opus(self):
        """Test that Opus is a transcodable format."""
        assert FFmpegTranscoder.is_transcodable("song.opus") is True
    
    def test_is_transcodable_mp3_false(self):
        """Test that MP3 is not considered transcodable (as it is natively supported)."""
        assert FFmpegTranscoder.is_transcodable("song.mp3") is False
    
    def test_is_transcodable_txt_false(self):
        """Test that TXT is not a transcodable format."""
        assert FFmpegTranscoder.is_transcodable("file.txt") is False
    
    # --- Constant Validation ---
    
    def test_native_formats_not_empty(self):
        """Verify the native formats set is not empty."""
        assert len(MINIAUDIO_NATIVE_FORMATS) > 0
        assert ".mp3" in MINIAUDIO_NATIVE_FORMATS
        assert ".flac" in MINIAUDIO_NATIVE_FORMATS
    
    def test_transcodable_formats_not_empty(self):
        """Verify the transcodable formats set is not empty."""
        assert len(FFMPEG_TRANSCODABLE_FORMATS) > 0
        assert ".m4a" in FFMPEG_TRANSCODABLE_FORMATS
        assert ".aac" in FFMPEG_TRANSCODABLE_FORMATS
    
    def test_no_format_overlap(self):
        """Verify that native and transcodable formats sets do not overlap."""
        overlap = MINIAUDIO_NATIVE_FORMATS & FFMPEG_TRANSCODABLE_FORMATS
        assert len(overlap) == 0, f"Format overlap detected: {overlap}"
    
    # --- Availability Detection Tests (Mock) ---
    
    @patch('shutil.which')
    def test_is_available_when_in_path(self, mock_which):
        """Test that is_available returns True when FFmpeg is in the system PATH."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        result = FFmpegTranscoder.is_available()
        
        assert result is True
        assert FFmpegTranscoder._ffmpeg_path == "/usr/bin/ffmpeg"
    
    @patch('shutil.which')
    @patch('os.path.isfile')
    def test_is_available_when_not_found(self, mock_isfile, mock_which):
        """Test that is_available returns False when FFmpeg is not found."""
        mock_which.return_value = None
        mock_isfile.return_value = False
        
        result = FFmpegTranscoder.is_available()
        
        assert result is False
        assert FFmpegTranscoder._ffmpeg_path is None
    
    @patch('shutil.which')
    def test_is_available_caches_result(self, mock_which):
        """Test that the result of the availability check is cached."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        # First call
        FFmpegTranscoder.is_available()
        call_count_1 = mock_which.call_count
        
        # Second call should use the cached result
        FFmpegTranscoder.is_available()
        call_count_2 = mock_which.call_count
        
        assert call_count_1 == call_count_2  # No extra call made
    
    @patch('shutil.which')
    def test_get_ffmpeg_path(self, mock_which):
        """Test getting the FFmpeg path."""
        mock_which.return_value = "/opt/ffmpeg/bin/ffmpeg"
        
        path = FFmpegTranscoder.get_ffmpeg_path()
        
        assert path == "/opt/ffmpeg/bin/ffmpeg"
    
    # --- Transcoding Method Tests (Testing Preconditions Only) ---
    
    @patch('shutil.which')
    @patch('os.path.isfile')
    def test_transcode_raises_when_unavailable(self, mock_isfile, mock_which):
        """Test that RuntimeError is raised when FFmpeg is unavailable."""
        mock_which.return_value = None
        mock_isfile.return_value = False
        
        with pytest.raises(RuntimeError, match="FFmpeg is unavailable"):
            FFmpegTranscoder.transcode_to_wav("test.m4a")
    
    @patch('shutil.which')
    def test_transcode_raises_when_file_not_found(self, mock_which):
        """Test that FileNotFoundError is raised when the source file does not exist."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        with pytest.raises(FileNotFoundError):
            FFmpegTranscoder.transcode_to_wav("nonexistent_file.m4a")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
