"""
Audio Engine Factory

Provides for the creation and management of audio engines, supporting switching between multiple backends.
"""

import logging
from typing import List, Type, Dict, Optional

from core.audio_engine import AudioEngineBase, PygameAudioEngine

logger = logging.getLogger(__name__)

# Engine registry
_ENGINE_REGISTRY: Dict[str, Type[AudioEngineBase]] = {}


def register_engine(name: str, engine_class: Type[AudioEngineBase]) -> None:
    """
    Register an audio engine.

    Args:
        name: Engine name identifier
        engine_class: Engine class
    """
    _ENGINE_REGISTRY[name] = engine_class


# Register built-in engines
register_engine("pygame", PygameAudioEngine)

# Try to register optional engines
try:
    from core.miniaudio_engine import MiniaudioEngine
    register_engine("miniaudio", MiniaudioEngine)
except Exception:
    logger.debug("miniaudio backend unavailable")

try:
    from core.vlc_engine import VLCEngine
    register_engine("vlc", VLCEngine)
except Exception:
    logger.debug("VLC backend unavailable")


class AudioEngineFactory:
    """
    Audio Engine Factory

    Creates appropriate audio engine instances based on configuration, supporting fallback strategies.

    Usage Example:
        # Create a specific backend
        engine = AudioEngineFactory.create("miniaudio")

        # Automatically select the best available backend
        engine = AudioEngineFactory.create_best_available()

        # Get list of available backends
        backends = AudioEngineFactory.get_available_backends()
    """

    # Backend priority (fallback order)
    PRIORITY_ORDER = ["miniaudio", "vlc", "pygame"]

    @classmethod
    def create(cls, backend: str = "miniaudio") -> AudioEngineBase:
        """
        Create a specified audio engine.

        If the specified backend is unavailable, it will automatically fall back to an available one.

        Args:
            backend: Backend name ("miniaudio", "vlc", "pygame")

        Returns:
            AudioEngineBase: Audio engine instance

        Raises:
            RuntimeError: If no backends are available
        """
        # Try to create the specified backend
        if backend in _ENGINE_REGISTRY:
            try:
                engine = _ENGINE_REGISTRY[backend]()
                logger.info("Using audio backend: %s", backend)
                return engine
            except Exception as e:
                logger.warning("Failed to create %s backend: %s, attempting fallback", backend, e)

        # Fallback strategy: try other backends by priority
        return cls.create_best_available(exclude=[backend])

    @classmethod
    def create_best_available(
        cls, exclude: Optional[List[str]] = None
    ) -> AudioEngineBase:
        """
        Create the best available audio engine.

        Tries each backend in priority order.

        Args:
            exclude: List of backend names to exclude

        Returns:
            AudioEngineBase: Audio engine instance

        Raises:
            RuntimeError: If no backends are available
        """
        exclude = exclude or []

        for backend in cls.PRIORITY_ORDER:
            if backend in exclude:
                continue
            if backend not in _ENGINE_REGISTRY:
                continue

            try:
                engine = _ENGINE_REGISTRY[backend]()
                logger.info("Using audio backend: %s", backend)
                return engine
            except Exception as e:
                logger.debug("Backend %s unavailable: %s", backend, e)

        raise RuntimeError("No audio backends available. Please install pygame, miniaudio, or VLC.")

    @classmethod
    def get_available_backends(cls) -> List[str]:
        """
        Get a list of available backends.

        Returns:
            List[str]: List of available backend names, sorted by priority.
        """
        available = []

        for backend in cls.PRIORITY_ORDER:
            if backend not in _ENGINE_REGISTRY:
                continue

            engine_class = _ENGINE_REGISTRY[backend]
            
            # Check if the subclass overrides the probe() method (instead of inheriting the base class's default implementation)
            has_custom_probe = (
                'probe' in engine_class.__dict__ or  # Defined directly on the class
                any('probe' in base.__dict__ for base in engine_class.__mro__[1:-1] 
                    if base.__name__ != 'AudioEngineBase')  # Defined on an intermediate parent class
            )
            
            if has_custom_probe:
                # Use static probe() method (without touching playback state)
                try:
                    if engine_class.probe():
                        available.append(backend)
                except Exception:
                    pass
            else:
                # Engine without a probe method: try instantiating
                try:
                    engine = engine_class()
                    available.append(backend)
                    if hasattr(engine, 'cleanup'):
                        engine.cleanup()
                except Exception:
                    pass

        return available

    @classmethod
    def get_backend_info(cls, backend: str) -> Dict[str, bool]:
        """
        Get feature support information for a backend.

        Args:
            backend: Backend name

        Returns:
            Dict[str, bool]: Feature support status
        """
        if backend not in _ENGINE_REGISTRY:
            return {}

        try:
            engine = _ENGINE_REGISTRY[backend]()
            info = {
                "gapless": engine.supports_gapless(),
                "crossfade": engine.supports_crossfade(),
                "equalizer": engine.supports_equalizer(),
                "replay_gain": engine.supports_replay_gain(),
            }
            if hasattr(engine, 'cleanup'):
                engine.cleanup()
            return info
        except Exception:
            return {}

    @classmethod
    def is_available(cls, backend: str) -> bool:
        """
        Check if a backend is available.

        Args:
            backend: Backend name

        Returns:
            bool: True if available
        """
        if backend not in _ENGINE_REGISTRY:
            return False

        engine_class = _ENGINE_REGISTRY[backend]
        
        # Check if the subclass overrides the probe() method
        has_custom_probe = (
            'probe' in engine_class.__dict__ or
            any('probe' in base.__dict__ for base in engine_class.__mro__[1:-1] 
                if base.__name__ != 'AudioEngineBase')
        )
        
        if has_custom_probe:
            try:
                return engine_class.probe()
            except Exception:
                return False
        
        # Engine without a probe method: try instantiating
        try:
            engine = engine_class()
            if hasattr(engine, 'cleanup'):
                engine.cleanup()
            return True
        except Exception:
            return False
