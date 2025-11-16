"""
Audio API Data Models

Pydantic models for audio transcription and meeting minutes API.

Author: AI Assistant
Date: 2025-11-13
"""

from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class AudioFormat(str, Enum):
    """Supported audio file formats"""
    M4A = "m4a"
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OPUS = "opus"


# =============================================================================
# DATA MODELS
# =============================================================================

class AudioMetadata(BaseModel):
    """Audio file metadata"""
    duration_seconds: float = Field(description="Audio duration in seconds")
    format: str = Field(description="File format (m4a, mp3, etc.)")
    file_size_mb: float = Field(description="File size in MB")
    sample_rate: Optional[int] = Field(default=None, description="Sample rate in Hz")
    channels: Optional[int] = Field(default=None, description="Number of audio channels")


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


class AudioProcessingOutput(BaseModel):
    """Complete audio processing output"""
    transcription_text: str = Field(description="Full transcription text")
    meeting_minutes: MeetingMinutes = Field(description="Structured meeting minutes")
    audio_metadata: AudioMetadata = Field(description="Audio file metadata")
    processing_stats: ProcessingStats = Field(description="Processing statistics")


# =============================================================================
# API REQUEST/RESPONSE MODELS
# =============================================================================

class AudioTranscriptionOptions(BaseModel):
    """Optional parameters for audio transcription"""
    enable_itn: bool = Field(default=True, description="Enable inverse text normalization")
    language: str = Field(default="zh", description="Audio language code")


class AudioTranscriptionResponse(BaseModel):
    """API response for audio transcription (JSON format)"""
    success: bool = Field(description="Whether the request was successful")
    data: Optional[AudioProcessingOutput] = Field(default=None, description="Processing results")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(description="Request metadata (task_id, timestamp, etc.)")


class AudioTranscriptionMarkdownResponse(BaseModel):
    """API response for audio transcription (Markdown format)"""
    success: bool = Field(description="Whether the request was successful")
    transcript: Optional[str] = Field(default=None, description="Full transcription text")
    markdown_content: Optional[str] = Field(default=None, description="Markdown formatted meeting minutes")
    markdown_file_path: Optional[str] = Field(default=None, description="Path to saved Markdown file")
    download_url: Optional[str] = Field(default=None, description="URL to download Markdown file")
    processing_stats: Optional[ProcessingStats] = Field(default=None, description="Processing statistics")
    audio_metadata: Optional[AudioMetadata] = Field(default=None, description="Audio file metadata")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(description="Request metadata (task_id, timestamp, etc.)")


class AsyncTaskResponse(BaseModel):
    """Response for async task submission"""
    success: bool = Field(description="Whether the task was accepted")
    data: dict = Field(description="Task information (task_id, status, estimated_time)")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(description="Request metadata")
