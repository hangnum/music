"""
Media Library Scanner Module

Responsible for physical file scanning and parsing of the media library.
"""

from typing import List, Optional, Callable, Dict, Any, Generator
from pathlib import Path
from datetime import datetime
import uuid
import threading
import logging

from core.database import DatabaseManager
from core.event_bus import EventBus, EventType
from core.metadata import MetadataParser, AudioMetadata
from models.track import Track
from .library_indexer import LibraryIndexer

logger = logging.getLogger(__name__)


class LibraryScanner:
    """
    Media Library Scanner
    
    Handles directory scanning, file statistics, metadata parsing, and batch import.
    """
    
    def __init__(self, db: DatabaseManager, event_bus: EventBus, indexer: LibraryIndexer):
        self._db = db
        self._event_bus = event_bus
        self._indexer = indexer
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_scan = threading.Event()
        self._lock = threading.RLock()
    
    def scan(self, directories: List[str], 
             progress_callback: Optional[Callable[[int, int, str], None]] = None) -> int:
        """
        Synchronously scan directories
        
        Uses two-phase approach: first quickly count files, then scan and process.
        This provides accurate progress percentage while avoiding loading all file paths into memory at once.
        
        Args:
            directories: List of directories
            progress_callback: Progress callback (current, total, file_path)
            
        Returns:
            int: Number of tracks scanned
        """
        self._stop_scan.clear()
        total_added = 0
        scanned_count = 0
        
        supported_exts = set(MetadataParser.get_supported_formats())
        
        # Phase 1: Quick file count (count only, don't store paths)
        total_files = self._count_audio_files(directories, supported_exts)
        
        if self._stop_scan.is_set():
            self._event_bus.publish(EventType.LIBRARY_SCAN_COMPLETED, {
                "total_scanned": 0,
                "total_added": 0
            })
            return 0
        
        self._event_bus.publish(EventType.LIBRARY_SCAN_STARTED, {
            "total": total_files,
            "directories": directories
        })

        # Preload indexed file paths to reduce SELECT queries for each file
        existing_paths = self._get_existing_file_paths()
        
        # Batch commit threshold
        batch_size = 50
        pending_count = 0
        
        # Phase 2: Scan and process
        for file_path in self._iter_audio_files(directories, supported_exts):
            if self._stop_scan.is_set():
                break
            
            scanned_count += 1
            file_str = str(file_path)
            
            # Check if already exists
            if file_str not in existing_paths:
                track = self._add_track_from_file(file_str, commit=False)
                if track:
                    total_added += 1
                    pending_count += 1
                    existing_paths.add(file_str)
                    
                    # Batch commit
                    if pending_count >= batch_size:
                        self._db.commit()
                        pending_count = 0
            
            # Progress callback
            if progress_callback:
                progress_callback(scanned_count, total_files, file_str)
            
            self._event_bus.publish(EventType.LIBRARY_SCAN_PROGRESS, {
                "current": scanned_count,
                "total": total_files,
                "file": file_str,
                "added": total_added
            })
        
        # Commit remaining records
        if pending_count > 0:
            self._db.commit()
        
        # Use actual scanned count
        self._event_bus.publish(EventType.LIBRARY_SCAN_COMPLETED, {
            "total_scanned": scanned_count,
            "total_added": total_added
        })
        
        return total_added
    
    def _count_audio_files(self, directories: List[str], supported_exts: set) -> int:
        """Quickly count audio files."""
        total_files = 0
        for directory in directories:
            if self._stop_scan.is_set():
                break
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            for file_path in dir_path.rglob("*"):
                if self._stop_scan.is_set():
                    break
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    total_files += 1
        return total_files
    
    def _iter_audio_files(self, directories: List[str], supported_exts: set) -> Generator[Path, None, None]:
        """Iterate through audio files generator."""
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            for file_path in dir_path.rglob("*"):
                if self._stop_scan.is_set():
                    return
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    yield file_path
    
    def _get_existing_file_paths(self) -> set:
        """Get the set of indexed file paths."""
        try:
            rows = self._db.fetch_all("SELECT file_path FROM tracks")
            return {row["file_path"] for row in rows if row.get("file_path")}
        except Exception:
            return set()
    
    def _add_track_from_file(self, file_path: str, commit: bool = True) -> Optional[Track]:
        """Add a track from a file to the database.
        
        Args:
            file_path: Audio file path
            commit: Whether to commit immediately (set to False during batch scan)
        """
        try:
            metadata = MetadataParser.parse(file_path)
        except Exception as e:
            logger.warning("Failed to parse metadata: %s - %s", file_path, e)
            return None
            
        if not metadata:
            return None
        
        # Handle artist
        artist_id = None
        if metadata.artist:
            artist_id = self._indexer.get_or_create_artist(metadata.artist, commit=commit)
        
        # Handle album
        album_id = None
        if metadata.album:
            album_id = self._indexer.get_or_create_album(
                metadata.album,
                artist_id,
                metadata.year,
                commit=commit
            )
        
        # Create track
        track = self._indexer.create_track_from_metadata(
            metadata, file_path, artist_id, album_id, commit
        )

        if track:
            self._event_bus.publish(EventType.TRACK_ADDED, track)
        
        return track
    
    def scan_async(self, directories: List[str]) -> None:
        """
        Asynchronously scan directories.
        
        Args:
            directories: List of directories
        """
        if self._scan_thread and self._scan_thread.is_alive():
            return
        
        def _safe_scan():
            try:
                self.scan(directories)
            except Exception as e:
                logger.exception("Scan thread exception: %s", e)
                self._event_bus.publish(EventType.LIBRARY_SCAN_COMPLETED, {
                    "total_scanned": 0,
                    "total_added": 0,
                    "error": str(e)
                })
        
        self._scan_thread = threading.Thread(
            target=_safe_scan,
            daemon=True
        )
        self._scan_thread.start()
    
    def join_scan_thread(self, timeout: float = 5.0) -> None:
        """Wait for the scan thread to end (for cleanup on exit)."""
        if self._scan_thread and self._scan_thread.is_alive():
            self._stop_scan.set()
            self._scan_thread.join(timeout=timeout)
    
    def stop_scan(self) -> None:
        """Stop the scan."""
        self._stop_scan.set()
    
    def is_scanning(self) -> bool:
        """Check if scanning is in progress."""
        return self._scan_thread is not None and self._scan_thread.is_alive()
