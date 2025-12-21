"""
Metadata Parser Module

Parses metadata information from audio files, including title, artist, album, cover, etc.
Supports multiple audio formats: MP3, FLAC, WAV, OGG, M4A, AAC, etc.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Audio metadata"""
    
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
    Metadata parser
    
    Uses mutagen library to parse metadata of various audio formats.
    
    Usage example:
        metadata = MetadataParser.parse("path/to/song.mp3")
        if metadata:
            print(f"Title: {metadata.title}")
            print(f"Artist: {metadata.artist}")
    """
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', 
                         '.aac', '.wma', '.ape', '.opus'}
    
    @classmethod
    def parse(cls, file_path: str) -> Optional[AudioMetadata]:
        """
        Parse audio file metadata
        
        Args:
            file_path: Audio file path
            
        Returns:
            AudioMetadata: Metadata object, returns None if parsing fails
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
            
            # Parse basic information
            if audio.info:
                metadata.duration_ms = int(audio.info.length * 1000)
                metadata.bitrate = getattr(audio.info, 'bitrate', 0)
                metadata.sample_rate = getattr(audio.info, 'sample_rate', 0)
                metadata.channels = getattr(audio.info, 'channels', 2)
            
            metadata.format = suffix[1:].upper()
            
            # Parse tags based on format
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
            
            # If no title, use filename
            if not metadata.title:
                metadata.title = path.stem
            
            return metadata
            
        except Exception as e:
            logger.debug("Parsing failed: %s, Error: %s", file_path, e)
            return None
    
    @classmethod
    def _parse_mp3(cls, file_path: str, metadata: AudioMetadata) -> None:
        """Parse MP3 metadata"""
        try:
            from mutagen.mp3 import MP3
            
            audio = MP3(file_path)
            tags = audio.tags
            
            if tags is None:
                return
            
            # Basic tags
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
            
            # Year
            if 'TDRC' in tags:
                try:
                    metadata.year = int(str(tags['TDRC'])[:4])
                except (ValueError, IndexError) as e:
                    logger.debug("MP3 year parse failed for %s: %s", file_path, e)
            
            # Track number
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
            
            # Cover image
            for key in tags:
                if key.startswith('APIC'):
                    apic = tags[key]
                    metadata.cover_data = apic.data
                    metadata.cover_mime = apic.mime
                    break
                    
        except Exception as e:
            logger.debug("MP3 parsing error: %s", e)
    
    @classmethod
    def _parse_flac(cls, audio, metadata: AudioMetadata) -> None:
        """Parse FLAC metadata"""
        cls._parse_vorbis_comment(audio, metadata)
        
        # FLAC cover
        if hasattr(audio, 'pictures') and audio.pictures:
            pic = audio.pictures[0]
            metadata.cover_data = pic.data
            metadata.cover_mime = pic.mime
    
    @classmethod
    def _parse_vorbis_comment(cls, audio, metadata: AudioMetadata) -> None:
        """Parse Vorbis Comment format (FLAC, OGG, etc.)"""
        if not hasattr(audio, 'get'):
            return
            
        metadata.title = audio.get('title', [''])[0]
        metadata.artist = audio.get('artist', [''])[0]
        metadata.album = audio.get('album', [''])[0]
        metadata.album_artist = audio.get('albumartist', [''])[0]
        metadata.genre = audio.get('genre', [''])[0]
        
        # Year
        if 'date' in audio:
            try:
                metadata.year = int(audio['date'][0][:4])
            except (ValueError, IndexError) as e:
                logger.debug("Vorbis year parse failed for %s: %s", metadata.file_path, e)
        
        # Track number
        if 'tracknumber' in audio:
            try:
                metadata.track_number = int(audio['tracknumber'][0])
            except ValueError as e:
                logger.debug("Vorbis track number parse failed for %s: %s", metadata.file_path, e)
    
    @classmethod
    def _parse_m4a(cls, audio, metadata: AudioMetadata) -> None:
        """Parse M4A/AAC metadata"""
        if not hasattr(audio, 'get'):
            return
            
        metadata.title = audio.get('\xa9nam', [''])[0]
        metadata.artist = audio.get('\xa9ART', [''])[0]
        metadata.album = audio.get('\xa9alb', [''])[0]
        metadata.genre = audio.get('\xa9gen', [''])[0]
        
        # Year
        if '\xa9day' in audio:
            try:
                metadata.year = int(audio['\xa9day'][0][:4])
            except (ValueError, IndexError) as e:
                logger.debug("M4A year parse failed for %s: %s", metadata.file_path, e)
        
        # Track number
        if 'trkn' in audio:
            try:
                track_info = audio['trkn'][0]
                metadata.track_number = track_info[0]
                metadata.total_tracks = track_info[1] if len(track_info) > 1 else None
            except (IndexError, TypeError) as e:
                logger.debug("M4A track number parse failed for %s: %s", metadata.file_path, e)
        
        # Cover
        if 'covr' in audio and audio['covr']:
            metadata.cover_data = bytes(audio['covr'][0])
            metadata.cover_mime = 'image/jpeg'
    
    @classmethod
    def _parse_generic(cls, audio, metadata: AudioMetadata) -> None:
        """Generic metadata parsing"""
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            if hasattr(tags, 'get'):
                metadata.title = tags.get('title', [''])[0] if 'title' in tags else ''
                metadata.artist = tags.get('artist', [''])[0] if 'artist' in tags else ''
                metadata.album = tags.get('album', [''])[0] if 'album' in tags else ''
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported formats"""
        return list(MetadataParser.SUPPORTED_FORMATS)
    
    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check if file format is supported"""
        suffix = Path(file_path).suffix.lower()
        return suffix in MetadataParser.SUPPORTED_FORMATS
