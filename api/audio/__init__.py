"""
Audio API Module

Modular audio transcription and meeting minutes generation API.
Separated into short-audio and long-audio sub-modules for independent deployment.

Author: AI Assistant
Date: 2025-11-18
"""

from api.audio.short.routes import router as short_audio_router
from api.audio.long.routes import router as long_audio_router

__all__ = ["short_audio_router", "long_audio_router"]
