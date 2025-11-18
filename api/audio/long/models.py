"""
Long Audio API Models

Pydantic models for long-audio transcription requests and responses.

Author: AI Assistant
Date: 2025-11-18
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, AnyUrl

from api.audio.shared_models import MeetingMinutes


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

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
    task_status: str = Field(description="DashScope task status (PENDING/RUNNING/...)")
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
    data: LongAudioStatusData = Field(description="Task status data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(description="Response metadata")


class DashScopeTaskFetchResponse(BaseModel):
    """Proxy response for DashScope task fetch"""
    success: bool = Field(default=True)
    data: dict = Field(description="DashScope task data")
    error: Optional[str] = Field(default=None)
    metadata: dict = Field(description="Response metadata")


class DashScopeTaskListResponse(BaseModel):
    """Proxy response for DashScope task list"""
    success: bool = Field(default=True)
    data: dict = Field(description="DashScope task list data")
    error: Optional[str] = Field(default=None)
    metadata: dict = Field(description="Response metadata")


class DashScopeTaskCancelResponse(BaseModel):
    """Proxy response for DashScope task cancellation"""
    success: bool = Field(default=True)
    data: dict = Field(description="DashScope cancellation response")
    error: Optional[str] = Field(default=None)
    metadata: dict = Field(description="Response metadata")


class LongAudioTaskListResponse(BaseModel):
    """Response for local long audio task list"""
    success: bool = Field(default=True)
    data: List[LongAudioStatusData] = Field(description="List of task status data")
    metadata: dict = Field(description="Response metadata (total, page, etc.)")
