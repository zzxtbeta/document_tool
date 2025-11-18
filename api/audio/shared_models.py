"""
Shared Audio Models

Common data models used by both short-audio and long-audio modules.

Author: AI Assistant
Date: 2025-11-18
"""

from typing import List
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# SHARED MODELS
# =============================================================================

class AudioMetadata(BaseModel):
    """Audio file metadata"""
    duration_seconds: float = Field(description="Audio duration in seconds")
    format: str = Field(description="File format (m4a, mp3, etc.)")
    file_size_mb: float = Field(description="File size in MB")
    sample_rate: int | None = Field(default=None, description="Sample rate in Hz")
    channels: int | None = Field(default=None, description="Number of audio channels")


class MeetingMinutes(BaseModel):
    """Structured meeting minutes"""
    title: str = Field(description="Meeting/interview title")
    content: str = Field(description="Structured minutes content")
    key_quotes: List[str] = Field(description="Important original quotes")
    keywords: List[str] = Field(description="Extracted keywords (3-8)")
    generated_at: datetime = Field(description="Generation timestamp")


class ProcessingStats(BaseModel):
    """Processing statistics"""
    total_time: float = Field(description="Total processing time in seconds")
    transcription_time: float = Field(description="ASR processing time in seconds")
    llm_time: float = Field(description="LLM generation time in seconds")
