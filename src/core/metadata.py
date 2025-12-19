"""
元数据解析模块

解析音频文件的元数据信息，包括标题、艺术家、专辑、封面等。
支持多种音频格式：MP3, FLAC, WAV, OGG, M4A, AAC等。
"""

from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """音频元数据"""
    
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: Optional[int] = None
    track_number: Optional[int] = None
    total_tracks: Optional[int] = None
    disc_number: Optional[int] = None
    genre: str = ""
    duration_ms: int = 0
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 2
    format: str = ""
    file_path: str = ""
    cover_data: Optional[bytes] = field(default=None, repr=False)
    cover_mime: str = ""


class MetadataParser:
    """
    元数据解析器
    
    使用mutagen库解析各种音频格式的元数据。
    
    使用示例:
        metadata = MetadataParser.parse("path/to/song.mp3")
        if metadata:
            print(f"标题: {metadata.title}")
            print(f"艺术家: {metadata.artist}")
    """
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', 
                         '.aac', '.wma', '.ape', '.opus'}
    
    @classmethod
    def parse(cls, file_path: str) -> Optional[AudioMetadata]:
        """
        解析音频文件元数据
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            AudioMetadata: 元数据对象，解析失败返回None
        """
        path = Path(file_path)
        
        if not path.exists():
            return None
        
        suffix = path.suffix.lower()
        if suffix not in cls.SUPPORTED_FORMATS:
            return None
        
        try:
            from mutagen import File
            
            audio = File(file_path)
            if audio is None:
                return None
            
            metadata = AudioMetadata(file_path=file_path)
            
            # 解析基本信息
            if audio.info:
                metadata.duration_ms = int(audio.info.length * 1000)
                metadata.bitrate = getattr(audio.info, 'bitrate', 0)
                metadata.sample_rate = getattr(audio.info, 'sample_rate', 0)
                metadata.channels = getattr(audio.info, 'channels', 2)
            
            metadata.format = suffix[1:].upper()
            
            # 根据格式解析标签
            if suffix == '.mp3':
                cls._parse_mp3(file_path, metadata)
            elif suffix == '.flac':
                cls._parse_flac(audio, metadata)
            elif suffix == '.ogg':
                cls._parse_vorbis_comment(audio, metadata)
            elif suffix in {'.m4a', '.aac'}:
                cls._parse_m4a(audio, metadata)
            else:
                cls._parse_generic(audio, metadata)
            
            # 如果没有标题，使用文件名
            if not metadata.title:
                metadata.title = path.stem
            
            return metadata
            
        except Exception as e:
            logger.debug("解析失败: %s, 错误: %s", file_path, e)
            return None
    
    @classmethod
    def _parse_mp3(cls, file_path: str, metadata: AudioMetadata) -> None:
        """解析MP3元数据"""
        try:
            from mutagen.mp3 import MP3
            
            audio = MP3(file_path)
            tags = audio.tags
            
            if tags is None:
                return
            
            # 基本标签
            if 'TIT2' in tags:
                metadata.title = str(tags['TIT2'])
            if 'TPE1' in tags:
                metadata.artist = str(tags['TPE1'])
            if 'TALB' in tags:
                metadata.album = str(tags['TALB'])
            if 'TPE2' in tags:
                metadata.album_artist = str(tags['TPE2'])
            if 'TCON' in tags:
                metadata.genre = str(tags['TCON'])
            
            # 年份
            if 'TDRC' in tags:
                try:
                    metadata.year = int(str(tags['TDRC'])[:4])
                except (ValueError, IndexError) as e:
                    logger.debug("MP3 year parse failed for %s: %s", file_path, e)
            
            # 曲目号
            if 'TRCK' in tags:
                track_str = str(tags['TRCK'])
                if '/' in track_str:
                    parts = track_str.split('/')
                    try:
                        metadata.track_number = int(parts[0])
                        metadata.total_tracks = int(parts[1])
                    except ValueError as e:
                        logger.debug("MP3 track number parse failed for %s: %s", file_path, e)
                else:
                    try:
                        metadata.track_number = int(track_str)
                    except ValueError as e:
                        logger.debug("MP3 track number parse failed for %s: %s", file_path, e)
            
            # 封面图片
            for key in tags:
                if key.startswith('APIC'):
                    apic = tags[key]
                    metadata.cover_data = apic.data
                    metadata.cover_mime = apic.mime
                    break
                    
        except Exception as e:
            logger.debug("MP3解析错误: %s", e)
    
    @classmethod
    def _parse_flac(cls, audio, metadata: AudioMetadata) -> None:
        """解析FLAC元数据"""
        cls._parse_vorbis_comment(audio, metadata)
        
        # FLAC封面
        if hasattr(audio, 'pictures') and audio.pictures:
            pic = audio.pictures[0]
            metadata.cover_data = pic.data
            metadata.cover_mime = pic.mime
    
    @classmethod
    def _parse_vorbis_comment(cls, audio, metadata: AudioMetadata) -> None:
        """解析Vorbis Comment格式（FLAC, OGG等）"""
        if not hasattr(audio, 'get'):
            return
            
        metadata.title = audio.get('title', [''])[0]
        metadata.artist = audio.get('artist', [''])[0]
        metadata.album = audio.get('album', [''])[0]
        metadata.album_artist = audio.get('albumartist', [''])[0]
        metadata.genre = audio.get('genre', [''])[0]
        
        # 年份
        if 'date' in audio:
            try:
                metadata.year = int(audio['date'][0][:4])
            except (ValueError, IndexError) as e:
                logger.debug("Vorbis year parse failed for %s: %s", metadata.file_path, e)
        
        # 曲目号
        if 'tracknumber' in audio:
            try:
                metadata.track_number = int(audio['tracknumber'][0])
            except ValueError as e:
                logger.debug("Vorbis track number parse failed for %s: %s", metadata.file_path, e)
    
    @classmethod
    def _parse_m4a(cls, audio, metadata: AudioMetadata) -> None:
        """解析M4A/AAC元数据"""
        if not hasattr(audio, 'get'):
            return
            
        metadata.title = audio.get('\xa9nam', [''])[0]
        metadata.artist = audio.get('\xa9ART', [''])[0]
        metadata.album = audio.get('\xa9alb', [''])[0]
        metadata.genre = audio.get('\xa9gen', [''])[0]
        
        # 年份
        if '\xa9day' in audio:
            try:
                metadata.year = int(audio['\xa9day'][0][:4])
            except (ValueError, IndexError) as e:
                logger.debug("M4A year parse failed for %s: %s", metadata.file_path, e)
        
        # 曲目号
        if 'trkn' in audio:
            try:
                track_info = audio['trkn'][0]
                metadata.track_number = track_info[0]
                metadata.total_tracks = track_info[1] if len(track_info) > 1 else None
            except (IndexError, TypeError) as e:
                logger.debug("M4A track number parse failed for %s: %s", metadata.file_path, e)
        
        # 封面
        if 'covr' in audio and audio['covr']:
            metadata.cover_data = bytes(audio['covr'][0])
            metadata.cover_mime = 'image/jpeg'
    
    @classmethod
    def _parse_generic(cls, audio, metadata: AudioMetadata) -> None:
        """通用元数据解析"""
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            if hasattr(tags, 'get'):
                metadata.title = tags.get('title', [''])[0] if 'title' in tags else ''
                metadata.artist = tags.get('artist', [''])[0] if 'artist' in tags else ''
                metadata.album = tags.get('album', [''])[0] if 'album' in tags else ''
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """获取支持的格式列表"""
        return list(MetadataParser.SUPPORTED_FORMATS)
    
    @staticmethod
    def is_supported(file_path: str) -> bool:
        """检查文件格式是否支持"""
        suffix = Path(file_path).suffix.lower()
        return suffix in MetadataParser.SUPPORTED_FORMATS
