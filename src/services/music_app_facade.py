# -*- coding: utf-8 -*-
"""
Music Application Facade Module

Provides a unified interface for the UI layer to access service layer functionality, 
narrowing the dependency surface.

Design Principles:
- UI components should only depend on this Facade, not directly on underlying services.
- The Facade only exposes "use-case level methods" actually needed by the UI.
- Internal service references are hidden from the outside.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from enum import Enum
    from app.protocols import (
        IConfigService,
        IEventBus,
        ILibraryService,
        IPlayerService,
        IPlaylistService,
    )
    from models.track import Track
    from models.tag import Tag
    from services.tag_service import TagService
    from services.favorites_service import FavoritesService
    from services.daily_playlist_service import DailyPlaylistResult

logger = logging.getLogger(__name__)


class MusicAppFacade:
    """Music Application Facade
    
    UI Use-Case Facade - narrows the dependency surface between UI and service layers.
    Sub-components should only receive this Facade rather than the AppContainer or individual services.
    
    Usage Example:
        # Inside a widget
        class MyWidget(QWidget):
            def __init__(self, facade: MusicAppFacade):
                self._facade = facade
                self._facade.subscribe(EventType.TRACK_STARTED, self._on_track)
                
            def play_track(self, track):
                self._facade.play(track)
    """
    
    def __init__(
        self,
        player: "IPlayerService",
        library: "ILibraryService",
        playlist_service: "IPlaylistService",
        config: "IConfigService",
        event_bus: "IEventBus",
        tag_service: Optional["TagService"] = None,
        favorites_service: Optional["FavoritesService"] = None,
    ):
        """Initialize the facade.
        
        Args:
            player: Playback service
            library: Media library service
            playlist_service: Playlist service
            config: Configuration service
            event_bus: Event bus
            tag_service: Tag service (optional)
            favorites_service: Favorites service (optional)
        """
        self._player = player
        self._library = library
        self._playlist = playlist_service
        self._config = config
        self._event_bus = event_bus
        self._tag_service = tag_service
        self._favorites_service = favorites_service
    
    # =========================================================================
    # Playback Control
    # =========================================================================
    
    def play(self, track: Optional["Track"] = None) -> bool:
        """Play a track.
        
        Args:
            track: Track to play; if None, play the current track.
            
        Returns:
            True if playback started successfully.
        """
        return self._player.play(track)
    
    def pause(self) -> None:
        """Pause playback."""
        self._player.pause()
    
    def resume(self) -> None:
        """Resume playback."""
        self._player.resume()
    
    def stop(self) -> None:
        """Stop playback."""
        self._player.stop()
    
    def toggle_play(self) -> None:
        """Toggle play/pause."""
        self._player.toggle_play()
    
    def next_track(self) -> Optional["Track"]:
        """Next track."""
        return self._player.next_track()
    
    def previous_track(self) -> Optional["Track"]:
        """Previous track."""
        return self._player.previous_track()
    
    def seek(self, position_ms: int) -> None:
        """Seek to a specified position.
        
        Args:
            position_ms: Target position in milliseconds.
        """
        self._player.seek(position_ms)
    
    def set_volume(self, volume: float) -> None:
        """Set volume.
        
        Args:
            volume: Volume value (0.0 - 1.0).
        """
        self._player.set_volume(volume)
    
    def get_volume(self) -> float:
        """Get current volume."""
        return self._player.get_volume()
    
    @property
    def is_playing(self) -> bool:
        """Whether music is currently playing."""
        return self._player.is_playing
    
    @property
    def current_track(self) -> Optional["Track"]:
        """The currently playing track."""
        return self._player.current_track
    
    @property
    def queue(self) -> List["Track"]:
        """The playback queue."""
        return self._player.queue
    
    def set_queue(self, tracks: List["Track"], start_index: int = 0) -> None:
        """Set the playback queue.
        
        Args:
            tracks: List of tracks.
            start_index: Starting index in the queue.
        """
        self._player.set_queue(tracks, start_index)
    
    # =========================================================================
    # Library Operations
    # =========================================================================
    
    def scan_library(self, directories: List[str]) -> None:
        """Asynchronously scan the media library.
        
        Args:
            directories: List of directories to scan.
        """
        self._library.scan_async(directories)
    
    def get_all_tracks(self) -> List["Track"]:
        """Get all tracks from the library."""
        return self._library.get_all_tracks()
    
    def get_track(self, track_id: str) -> Optional["Track"]:
        """Get a single track by ID."""
        return self._library.get_track(track_id)
    
    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search the media library.
        
        Args:
            query: Search keyword.
            limit: Result count limit.
            
        Returns:
            Search results containing tracks, albums, and artists.
        """
        return self._library.search(query, limit)
    
    def get_track_count(self) -> int:
        """Get total track count in the library."""
        return self._library.get_track_count()
    
    # =========================================================================
    # Playlist Operations
    # =========================================================================
    
    def create_playlist(self, name: str, description: str = "") -> Any:
        """Create a new playlist.
        
        Args:
            name: Playlist name.
            description: Playlist description.
            
        Returns:
            The created playlist object.
        """
        return self._playlist.create(name, description)
    
    def get_playlists(self) -> List[Any]:
        """Get all playlists."""
        return self._playlist.get_all()
    
    def get_playlist(self, playlist_id: str) -> Optional[Any]:
        """Get a single playlist by ID."""
        return self._playlist.get(playlist_id)
    
    def add_track_to_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Add a track to a playlist."""
        return self._playlist.add_track(playlist_id, track_id)
    
    def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Remove a track from a playlist."""
        return self._playlist.remove_track(playlist_id, track_id)
    
    # =========================================================================
    # Configuration Operations
    # =========================================================================
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._config.set(key, value)
    
    def save_config(self) -> None:
        """Save configuration to file."""
        self._config.save()
    
    # =========================================================================
    # Event Subscription
    # =========================================================================
    
    def subscribe(
        self, 
        event_type: "Enum", 
        callback: Callable[[Any], None]
    ) -> str:
        """Subscribe to an event.
        
        Args:
            event_type: Event type enumeration.
            callback: Callback function.
            
        Returns:
            Subscription ID.
        """
        return self._event_bus.subscribe(event_type, callback)
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from an event.
        
        Args:
            subscription_id: Subscription ID.
            
        Returns:
            True if successfully unsubscribed.
        """
        return self._event_bus.unsubscribe(subscription_id)
    
    def publish(self, event_type: "Enum", data: Any = None) -> None:
        """Publish an event.
        
        Args:
            event_type: Event type.
            data: Event data.
        """
        self._event_bus.publish(event_type, data)
    
    # =========================================================================
    # Tag Operations
    # =========================================================================
    
    def get_all_tags(self) -> List["Tag"]:
        """Get all tags."""
        if not self._tag_service:
            return []
        return self._tag_service.get_all_tags()
    
    def get_track_tags(self, track_id: str) -> List["Tag"]:
        """Get tags for a specific track."""
        if not self._tag_service:
            return []
        return self._tag_service.get_track_tags(track_id)
    
    def get_track_tag_names(self, track_id: str) -> List[str]:
        """Get tag names for a specific track."""
        if not self._tag_service:
            return []
        return self._tag_service.get_track_tag_names(track_id)
    
    def create_tag(self, name: str, color: str = "#808080") -> Optional["Tag"]:
        """Create a new tag.
        
        Args:
            name: Tag name.
            color: Tag color.
            
        Returns:
            The created Tag object, or None if it already exists.
        """
        if not self._tag_service:
            return None
        return self._tag_service.create_tag(name, color)
    
    def add_tag_to_track(self, track_id: str, tag_id: str) -> bool:
        """Add a tag to a track."""
        if not self._tag_service:
            return False
        return self._tag_service.add_tag_to_track(track_id, tag_id)
    
    def remove_tag_from_track(self, track_id: str, tag_id: str) -> bool:
        """Remove a tag from a track."""
        if not self._tag_service:
            return False
        return self._tag_service.remove_tag_from_track(track_id, tag_id)
    
    def set_track_tags(self, track_id: str, tag_ids: List[str]) -> bool:
        """Set tags for a track (replaces existing tags)."""
        if not self._tag_service:
            return False
        return self._tag_service.set_track_tags(track_id, tag_ids)
    
    def get_tracks_by_tags(
        self, 
        tag_names: List[str], 
        match_mode: str = "any",
        limit: int = 200
    ) -> List[str]:
        """Query track IDs by tag names."""
        if not self._tag_service:
            return []
        return self._tag_service.get_tracks_by_tags(tag_names, match_mode, limit)
    
    @property
    def tag_service(self) -> Optional["TagService"]:
        """Get the tag service (for advanced use-cases)."""
        return self._tag_service
    
    # =========================================================================
    # Favorites Operations
    # =========================================================================
    
    def get_favorite_ids(self) -> set:
        """Get IDs of all favorited tracks."""
        if not self._favorites_service:
            return set()
        return self._favorites_service.get_favorite_ids()
    
    def is_favorite(self, track_id: str) -> bool:
        """Check if a track is favorited."""
        if not self._favorites_service:
            return False
        return self._favorites_service.is_favorite(track_id)
    
    def add_to_favorites(self, tracks: List["Track"]) -> int:
        """Add tracks to favorites.
        
        Args:
            tracks: List of tracks to favorite.
            
        Returns:
            Number of successfully added tracks.
        """
        if not self._favorites_service:
            return 0
        return self._favorites_service.add_tracks(tracks)
    
    def remove_from_favorites(self, track_ids: List[str]) -> int:
        """Remove tracks from favorites.
        
        Args:
            track_ids: List of track IDs to remove from favorites.
            
        Returns:
            Number of successfully removed tracks.
        """
        if not self._favorites_service:
            return 0
        return self._favorites_service.remove_tracks(track_ids)
    
    @property
    def favorites_service(self) -> Optional["FavoritesService"]:
        """Get the favorites service (for advanced use-cases)."""
        return self._favorites_service
    
    @property
    def config(self) -> "IConfigService":
        """Get the configuration service (for advanced use-cases)."""
        return self._config
    
    @property
    def library_service(self) -> "ILibraryService":
        """Get the library service (for advanced use-cases)."""
        return self._library
    
    # =========================================================================
    # Daily Playlist
    # =========================================================================
    
    def generate_daily_playlist(
        self, 
        tags: List[str], 
        limit: int = 50
    ) -> Optional["DailyPlaylistResult"]:
        """Generate a daily playlist.
        
        Args:
            tags: List of tags to guide generation.
            limit: Target number of tracks.
            
        Returns:
            Generation result, or None if service is unavailable.
        """
        if not self._tag_service:
            return None
        
        from services.daily_playlist_service import DailyPlaylistService
        from services.llm_providers import create_llm_provider
        
        # Attempt to create an LLM provider
        try:
            llm_provider = create_llm_provider(self._config)
        except Exception:
            llm_provider = None
        
        service = DailyPlaylistService(
            tag_service=self._tag_service,
            library_service=self._library,
            llm_provider=llm_provider,
        )
        
        return service.generate(tags, limit=limit)

