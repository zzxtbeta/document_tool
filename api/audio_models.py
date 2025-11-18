"""
Audio API Data Models

Pydantic models for audio transcription and meeting minutes API.

Author: AI Assistant
Date: 2025-11-13
"""

from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, AnyUrl


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


class LongAudioTranscriptionRequest(BaseModel):
    """Request body for paraformer long-audio transcription"""
    file_urls: List[AnyUrl] = Field(
        description="List of HTTP/HTTPS/OSS URLs pointing to audio files",
        min_items=1,
        max_items=100
    )
    model: str = Field(
        default="paraformer-v2",
        description="DashScope paraformer model (paraformer-v2 or paraformer-8k-v2)"
    )
    language_hints: Optional[List[str]] = Field(
        default=None,
        description="Language codes (only valid when model=paraformer-v2)"
    )
    user_id: Optional[str] = Field(default=None, description="Application user identifier")
    project_id: Optional[str] = Field(default=None, description="Project/tenant identifier")
    source_filename: Optional[str] = Field(default=None, description="Original filename for downstream assets")


class LongAudioTaskInfo(BaseModel):
    """Response payload for long-audio submission"""
    task_id: str = Field(description="Internal task identifier")
    dashscope_task_id: str = Field(description="DashScope task identifier")
    task_status: str = Field(description="DashScope task status (PENDING/RUNNING/...)" )
    model: str = Field(description="Model used for transcription")


class LongAudioSubmissionResponse(BaseModel):
    """Submission response wrapper"""
    success: bool = Field(default=True, description="Whether submission succeeded")
    data: LongAudioTaskInfo = Field(description="Submission data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(description="Response metadata (task_id, timestamp)")


class LongAudioStatusData(BaseModel):
    """Detailed status for a long-audio transcription task"""
    task_id: str = Field(description="Internal task identifier")
    dashscope_task_id: str = Field(description="DashScope task identifier")
    task_status: str = Field(description="Current DashScope task status")
    model: str = Field(description="Model used for transcription")
    file_urls: List[AnyUrl] = Field(description="Submitted audio URLs")
    language_hints: Optional[List[str]] = Field(
        default=None,
        description="Language hints supplied during submission"
    )
    submitted_at: str = Field(description="Submission timestamp (ISO8601)")
    updated_at: str = Field(description="Last update timestamp (ISO8601)")
    results: Optional[List[dict]] = Field(
        default=None,
        description="DashScope result payload (mirrors API response)"
    )
    local_result_paths: Optional[List[str]] = Field(
        default=None,
        description="Local file paths of cached transcription JSON"
    )
    remote_result_urls: Optional[List[AnyUrl]] = Field(
        default=None,
        description="OSS URLs of cached transcription JSON"
    )
    local_audio_paths: Optional[List[str]] = Field(
        default=None,
        description="Local copies of source audio files"
    )
    local_dir: Optional[str] = Field(
        default=None,
        description="Local directory containing cached audio/results"
    )
    remote_result_ttl_seconds: Optional[int] = Field(
        default=None,
        description="Declared TTL (seconds) for remote DashScope result availability"
    )
    remote_result_expires_at: Optional[str] = Field(
        default=None,
        description="ISO8601 timestamp when DashScope result URL is expected to expire"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    transcription_text: Optional[str] = Field(
        default=None,
        description="Concatenated transcription text cached locally for meeting minutes"
    )
    meeting_minutes: Optional[MeetingMinutes] = Field(
        default=None,
        description="Structured meeting minutes generated from transcription"
    )
    minutes_markdown_path: Optional[str] = Field(
        default=None,
        description="Local path to generated meeting minutes Markdown file"
    )
    minutes_markdown_url: Optional[AnyUrl] = Field(
        default=None,
        description="OSS URL/path of meeting minutes Markdown file"
    )
    minutes_markdown_signed_url: Optional[AnyUrl] = Field(
        default=None,
        description="Temporary signed URL for downloading minutes Markdown"
    )
    minutes_generated_at: Optional[str] = Field(
        default=None,
        description="ISO8601 timestamp when meeting minutes were generated"
    )
    minutes_error: Optional[str] = Field(
        default=None,
        description="Error message if meeting minutes generation failed"
    )
    user_id: Optional[str] = Field(default=None, description="Task owner user ID")
    project_id: Optional[str] = Field(default=None, description="Tenant or project identifier")
    source_filename: Optional[str] = Field(default=None, description="Original filename derived from OSS URL")


class LongAudioStatusResponse(BaseModel):
    """Status response wrapper"""
    success: bool = Field(default=True, description="Whether status retrieval succeeded")
    data: LongAudioStatusData = Field(description="Status data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(description="Response metadata")


class DashScopeTaskFetchResponse(BaseModel):
    """Proxy response for DashScope单任务查询"""
    success: bool = Field(default=True, description="Whether fetch succeeded")
    data: dict = Field(description="DashScope payload (request_id/output/usage)")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(default_factory=dict, description="Echoed query metadata")


class DashScopeTaskListResponse(BaseModel):
    """Proxy response for DashScope批量查询"""
    success: bool = Field(default=True, description="Whether list succeeded")
    data: dict = Field(description="DashScope list payload (total/data/page info)")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(default_factory=dict, description="Echoed query metadata")


class DashScopeTaskCancelResponse(BaseModel):
    """Proxy response for DashScope取消任务"""
    success: bool = Field(default=True, description="Whether cancel succeeded")
    data: dict = Field(description="DashScope cancel payload (request_id)")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(default_factory=dict, description="Echoed request metadata")
