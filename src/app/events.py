# -*- coding: utf-8 -*-
"""
Event Types Module

Re-exports EventType from core.event_bus for use by the UI layer.
This ensures the UI layer does not need to import directly from the core layer.

Usage Example:
    from app.events import EventType
    
    # Subscribe to an event
    facade.subscribe(EventType.TRACK_STARTED, on_track_started)
"""

# Re-export EventType to maintain backward compatibility
from core.event_bus import EventType

__all__ = ["EventType"]
