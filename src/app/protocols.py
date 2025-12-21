# -*- coding: utf-8 -*-
"""
Protocols Definition Module

Defines the interface protocols (Protocol) for all services in the application.
Uses Protocol instead of ABC to support structural subtyping checks.

Design Decisions:
- Default to using Protocol + @runtime_checkable
- ABC is only used for base classes that need to share default implementations (e.g., AudioEngineBase)
- Runtime checks are performed as one-time assertions during container assembly or testing
"""

from __future__ import annotations

from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)

if TYPE_CHECKING:
    from models.track import Track


# =============================================================================
# Event Bus Protocol
# =============================================================================

@runtime_checkable
class IEventBus(Protocol):
    """Event Bus Interface
    
    Provides a publish-subscribe pattern event system.
    """
    
    def subscribe(
        self, 
        event_type: Enum, 
        callback: Callable[[Any], None]
    ) -> str:
        """Subscribe to an event
        
        Args:
            event_type: Event type enumeration
            callback: Callback function
            
        Returns:
            Subscription ID, used to unsubscribe
        """
        ...
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from an event
        
        Args:
            subscription_id: The ID returned when subscribing
            
        Returns:
            True if successfully unsubscribed
        """
        ...
    
    def publish(self, event_type: Enum, data: Any = None) -> None:
        """Publish an event
        
        Args:
            event_type: Event type
            data: Event data
        """
        ...
    
    def publish_sync(
        self, 
        event_type: Enum, 
        data: Any = None, 
        timeout: Optional[float] = None
    ) -> bool:
        """Publish an event synchronously
        
        Args:
            event_type: Event type
            data: Event data
            timeout: Timeout period
            
        Returns:
            True if completed before timeout
        """
        ...


# =============================================================================
# Database Protocol
# =============================================================================

# Re-export infrastructure interfaces from core.ports
from core.ports.database import IDatabase as _IDatabase, ITrackRepository
from core.ports.audio import IAudioEngine, IAudioEngineFactory
from core.ports.llm import ILLMProvider, ILLMProviderFactory, LLMSettings

# Maintain backward compatibility
IDatabase = _IDatabase


# =============================================================================
# Configuration Service Protocol
# =============================================================================

@runtime_checkable
class IConfigService(Protocol):
    """Configuration Service Interface"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value
        
        Args:
            key: Configuration key, supports dot-separated nested keys
            default: Default value
            
        Returns:
            Configuration value
        """
        ...
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        ...
    
    def save(self) -> None:
        """Save configuration to file"""
        ...


# =============================================================================
# Player Service Protocol
# =============================================================================

@runtime_checkable
class IPlayerService(Protocol):
    """Player Service Interface"""
    
    def play(self, track: Optional["Track"] = None) -> bool:
        """Play a track"""
        ...
    
    def pause(self) -> None:
        """Pause playback"""
        ...
    
    def resume(self) -> None:
        """Resume playback"""
        ...
    
    def stop(self) -> None:
        """Stop playback"""
        ...
    
    def next_track(self) -> Optional["Track"]:
        """Next track"""
        ...
    
    def previous_track(self) -> Optional["Track"]:
        """Previous track"""
        ...
    
    def seek(self, position_ms: int) -> None:
        """Seek to a specified position"""
        ...
    
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 - 1.0)"""
        ...
    
    def get_volume(self) -> float:
        """Get current volume"""
        ...
    
    @property
    def is_playing(self) -> bool:
        """Whether music is currently playing"""
        ...
    
    @property
    def current_track(self) -> Optional["Track"]:
        """Currently playing track"""
        ...
    
    @property
    def queue(self) -> List["Track"]:
        """Playback queue"""
        ...
    
    def set_queue(self, tracks: List["Track"], start_index: int = 0) -> None:
        """Set playback queue"""
        ...
    
    def toggle_play(self) -> None:
        """Toggle play/pause"""
        ...


# =============================================================================
# Library Service Protocol
# =============================================================================

@runtime_checkable
class ILibraryService(Protocol):
    """Library Service Interface"""
    
    def scan_async(self, directories: List[str]) -> None:
        """Scan directories asynchronously"""
        ...
    
    def get_all_tracks(self) -> List["Track"]:
        """Get all tracks"""
        ...
    
    def get_track(self, track_id: str) -> Optional["Track"]:
        """Get a single track"""
        ...
    
    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search the library"""
        ...
    
    def get_track_count(self) -> int:
        """Get total track count"""
        ...


# =============================================================================
# Playlist Service Protocol
# =============================================================================

@runtime_checkable
class IPlaylistService(Protocol):
    """Playlist Service Interface"""
    
    def create(self, name: str, description: str = "") -> Any:
        """Create a playlist"""
        ...
    
    def get_all(self) -> List[Any]:
        """Get all playlists"""
        ...
    
    def get(self, playlist_id: str) -> Optional[Any]:
        """Get a single playlist"""
        ...
    
    def add_track(self, playlist_id: str, track_id: str) -> bool:
        """Add a track to a playlist"""
        ...
    
    def remove_track(self, playlist_id: str, track_id: str) -> bool:
        """Remove a track from a playlist"""
        ...
