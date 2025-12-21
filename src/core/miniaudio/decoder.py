"""
miniaudio Decoder Module

Responsible for audio file decoding, supports native formats and FFmpeg transcoding.
"""

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import miniaudio
try:
    import miniaudio
    MINIAUDIO_AVAILABLE = True
except ImportError:
    MINIAUDIO_AVAILABLE = False
    logger.warning("miniaudio library not installed")

# Try to import FFmpeg transcoder
try:
    from core.ffmpeg_transcoder import FFmpegTranscoder, MINIAUDIO_NATIVE_FORMATS
    FFMPEG_TRANSCODER_AVAILABLE = True
except ImportError:
    FFmpegTranscoder = None  # type: ignore
    MINIAUDIO_NATIVE_FORMATS = {'.mp3', '.flac', '.wav', '.ogg'}
    FFMPEG_TRANSCODER_AVAILABLE = False


class UnsupportedFormatError(Exception):


    """


    Unsupported audio format exception


    


    Thrown when miniaudio doesn't natively support and FFmpeg transcoding fails.


    PlayerService can catch this exception and try VLC fallback.


    """


    def __init__(self, file_path: str, format_ext: str, reason: str = ""):


        self.file_path = file_path


        self.format_ext = format_ext


        self.reason = reason


        super().__init__(


            f"Unsupported format {format_ext}: {file_path}" + 


            (f" ({reason})" if reason else "")


        )








class AudioDecoder:


    """


    Audio Decoder


    


    Responsible for audio file decoding, supports multiple formats and transcoding strategies.


    """


    


    def __init__(self, sample_rate: int = 44100, channels: int = 2):


        """


        Initialize decoder


        


        Args:


            sample_rate: Target sample rate


            channels: Target channel count


        """


        if not MINIAUDIO_AVAILABLE:


            raise ImportError("miniaudio library not installed")


        


        self._sample_rate = sample_rate


        self._channels = channels


    


    def decode_file(self, file_path: str) -> miniaudio.DecodedSoundFile:


        """


        Decode audio file


        


        Decoding strategy:


        1. Direct decode for natively supported formats


        2. Try FFmpeg transcode for non-native formats


        3. Throw UnsupportedFormatError if both fail


        


        Args:


            file_path: Audio file path


            


        Returns:


            Decoded audio data


            


        Raises:


            UnsupportedFormatError: Format not supported and transcoding failed


            Exception: Other decoding errors


        """


        ext = os.path.splitext(file_path)[1].lower()


        is_native = ext in MINIAUDIO_NATIVE_FORMATS


        


        decode_error = None


        


        # Strategy 1: Try Native decode


        if is_native:


            try:


                return self._decode_native(file_path)


            except Exception as e:


                decode_error = e


                logger.debug("Native decode failed: %s", e)


        


        # Strategy 2: Non-native format or Native decode failed, try FFmpeg transcoding


        if FFMPEG_TRANSCODER_AVAILABLE and FFmpegTranscoder.is_available():


            try:


                decoded = self._decode_via_ffmpeg(file_path)


                logger.info("Decoded via FFmpeg transcoding: %s", file_path)


                return decoded


            except Exception as e:


                logger.warning("FFmpeg Transcode failed: %s", e)


                if decode_error is None:


                    decode_error = e


        


        # Strategy 3: Both failed, throw exception


        reason = str(decode_error) if decode_error else "Unknown error"


        raise UnsupportedFormatError(file_path, ext, reason)


    


    def _decode_native(self, file_path: str) -> miniaudio.DecodedSoundFile:


        """


        Use miniaudio native decode


        


        First try decode_file, then try in-memory decoding on failure.


        """


        try:


            return miniaudio.decode_file(


                file_path,


                output_format=miniaudio.SampleFormat.FLOAT32,


                nchannels=self._channels,


            )


        except Exception as e:


            logger.debug("miniaudio decode_file failed, retrying in-memory: %s", e)


            with open(file_path, "rb") as audio_file:


                data = audio_file.read()


            return miniaudio.decode(


                data,


                output_format=miniaudio.SampleFormat.FLOAT32,


                nchannels=self._channels,


            )


    


    def _decode_via_ffmpeg(self, file_path: str) -> miniaudio.DecodedSoundFile:


        """


        Decode after transcoding via FFmpeg


        


        Transcode file to WAV format, then decode with miniaudio.


        """


        if not FFMPEG_TRANSCODER_AVAILABLE or FFmpegTranscoder is None:


            raise ImportError("FFmpegTranscoder unavailable")


        


        wav_data = FFmpegTranscoder.transcode_to_wav_pipe(


            file_path, 


            target_sample_rate=self._sample_rate


        )


        return miniaudio.decode(


            wav_data,


            output_format=miniaudio.SampleFormat.FLOAT32,


            nchannels=self._channels,


        )


    


    def get_native_formats(self) -> set:


        """Get natively supported formats"""


        return MINIAUDIO_NATIVE_FORMATS.copy()


    


    def is_format_native(self, file_path: str) -> bool:


        """Check if format is natively supported"""


        ext = os.path.splitext(file_path)[1].lower()


        return ext in MINIAUDIO_NATIVE_FORMATS


    


    def is_ffmpeg_available(self) -> bool:


        """Check if FFmpeg transcoding is available"""


        return FFMPEG_TRANSCODER_AVAILABLE and FFmpegTranscoder.is_available()

