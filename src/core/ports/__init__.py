# -*- coding: utf-8 -*-
"""
Ports Interfaces Package

Defines the interfaces between the application and external infrastructure (database, audio engine, LLM).

Design Principles:
- Use Protocol to define interfaces, supporting structural subtyping.
- Service layer depends on these interfaces rather than concrete implementations.
- Facilitates replacing with fake/mock during testing.
"""

from core.ports.database import IDatabase, ITrackRepository
from core.ports.audio import IAudioEngine
from core.ports.llm import ILLMProvider

__all__ = [
    "IDatabase",
    "ITrackRepository", 
    "IAudioEngine",
    "ILLMProvider",
]
