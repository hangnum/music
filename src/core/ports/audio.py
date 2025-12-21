# -*- coding: utf-8 -*-
"""
Audio Engine Port Interface

Defines an abstract interface for audio engines, ensuring the playback service 
does not depend on specific audio backend implementations.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional, Protocol, runtime_checkable


class PlayerState(Enum):
    """Player Status"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"


@runtime_checkable
class IAudioEngine(Protocol):
    """Audio Engine Interface
    
    Provides core functionality for audio playback.
    Current implementations: MiniaudioEngine, PygameEngine, VLCEngine
    """
    
    @property
    def state(self) -> PlayerState:
        """Current playback state"""
        ...
    
    @property
    def volume(self) -> float:
        """Current volume (0.0 - 1.0)"""
        ...
    
    def load(self, file_path: str) -> bool:
        """Load an audio file
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            True if loading was successful
        """
        ...
    
    def play(self) -> bool:
        """Start playback
        
        Returns:
            True if playback started successfully
        """
        ...
    
    def pause(self) -> bool:
        """Pause playback
        
        Returns:
            True if paused successfully
        """
        ...
    
    def resume(self) -> bool:
        """Resume playback
        
        Returns:
            True if resumed successfully
        """
        ...
    
    def stop(self) -> bool:
        """Stop playback
        
        Returns:
            True if stopped successfully
        """
        ...
    
    def seek(self, position_ms: int) -> bool:
        """Seek to a specified position
        
        Args:
            position_ms: Target position in milliseconds
            
        Returns:
            True if seek was successful
        """
        ...
    
    def get_position(self) -> int:
        """Get current playback position
        
        Returns:
            Current position in milliseconds
        """
        ...
    
    def get_duration(self) -> int:
        """Get audio duration
        
        Returns:
            Duration in milliseconds
        """
        ...
    
    def set_volume(self, volume: float) -> None:
        """Set volume
        
        Args:
            volume: Volume value (0.0 - 1.0)
        """
        ...
    
    def set_on_end(self, callback: Optional[Callable]) -> None:
        """Set playback completion callback
        
        Args:
            callback: Callback function, receives PlaybackEndInfo
        """
        ...
    
    def set_on_error(self, callback: Optional[Callable[[str], None]]) -> None:
        """Set error callback
        
        Args:
            callback: Callback function, receives an error message
        """
        ...
    
    def set_next_track(self, file_path: Optional[str]) -> None:
        """Set the next track (for gapless/crossfade)
        
        Args:
            file_path: Path to the next file, None to clear
        """
        ...
    
    def get_engine_name(self) -> str:
        """Get the engine name"""
        ...
    
    def cleanup(self) -> None:
        """Clean up resources"""
        ...


@runtime_checkable
class IAudioEngineFactory(Protocol):
    """Audio Engine Factory Interface"""
    
    def create(self, backend: str = "miniaudio") -> IAudioEngine:
        """Create an audio engine
        
        Args:
            backend: Backend name
            
        Returns:
            An audio engine instance
        """
        ...
    
    def create_best_available(self) -> IAudioEngine:
        """Create the best available engine"""
        ...
    
    def get_available_backends(self) -> list:
        """Get a list of available backends"""
        ...
