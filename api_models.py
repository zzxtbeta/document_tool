"""
API Data Models

Pydantic models for FastAPI request/response validation.

Author: AI Assistant
Date: 2025-11-10
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class TaskStatus(str, Enum):
    """Task processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ExtractRequest(BaseModel):
    """Request model for knowledge graph extraction"""
    chunk_size: Optional[int] = Field(
        default=512,
        ge=128,
        le=2048,
        description="Chunk size in characters for text grouping"
    )
    max_workers: Optional[int] = Field(
        default=3,
        ge=1,
        le=16,
        description="Maximum number of parallel workers"
    )
    temperature: Optional[float] = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="LLM generation temperature"
    )
    similarity_threshold: Optional[float] = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Entity deduplication similarity threshold"
    )
    parallel: Optional[bool] = Field(
        default=True,
        description="Enable parallel processing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_size": 512,
                "max_workers": 3,
                "temperature": 0.3,
                "similarity_threshold": 0.85,
                "parallel": True
            }
        }


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ResponseMetadata(BaseModel):
    """Standard response metadata"""
    task_id: str = Field(description="Unique task identifier")
    timestamp: str = Field(description="Response timestamp in ISO8601 format")
    processing_time: Optional[float] = Field(
        default=None,
        description="Processing time in seconds"
    )


class ErrorDetail(BaseModel):
    """Error detail information"""
    code: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )


class StandardResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = Field(description="Request success status")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[ErrorDetail] = Field(default=None, description="Error information")
    metadata: ResponseMetadata = Field(description="Response metadata")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(description="Service status", example="healthy")
    version: str = Field(description="Pipeline version", example="1.2.0")
    llm_available: bool = Field(description="LLM API availability")
    timestamp: str = Field(description="Check timestamp")


class KnowledgeGraphData(BaseModel):
    """Knowledge graph data structure"""
    entities: Dict[str, Any] = Field(description="Entity dictionary")
    relations: List[Dict[str, Any]] = Field(description="Relations list")
    aligned_entities: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aligned entities (ontology-based)"
    )
    aligned_relations: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Aligned relations (ontology-based)"
    )
    metadata: Dict[str, Any] = Field(description="Graph metadata")


class ExtractResponseData(BaseModel):
    """Knowledge graph extraction response data"""
    raw_graph: KnowledgeGraphData = Field(description="Raw extraction result")
    aligned_graph: KnowledgeGraphData = Field(description="Aligned extraction result")
    summary: Dict[str, Any] = Field(description="Extraction summary statistics")


class ExtractResponse(BaseModel):
    """Synchronous extraction response"""
    success: bool = True
    data: ExtractResponseData
    error: Optional[ErrorDetail] = None
    metadata: ResponseMetadata


class AsyncTaskResponse(BaseModel):
    """Async task submission response"""
    success: bool = True
    data: Dict[str, str] = Field(
        description="Task information",
        example={"task_id": "uuid-here", "status": "pending"}
    )
    error: Optional[ErrorDetail] = None
    metadata: ResponseMetadata


class TaskStatusData(BaseModel):
    """Task status data"""
    task_id: str = Field(description="Task identifier")
    status: TaskStatus = Field(description="Current task status")
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Processing progress percentage"
    )
    result: Optional[ExtractResponseData] = Field(
        default=None,
        description="Extraction result (if completed)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)"
    )
    created_at: str = Field(description="Task creation timestamp")
    updated_at: str = Field(description="Last update timestamp")
    download_urls: Optional[Dict[str, str]] = Field(
        default=None,
        description="Download URLs for result files"
    )


class TaskResponse(BaseModel):
    """Task status query response"""
    success: bool = True
    data: TaskStatusData
    error: Optional[ErrorDetail] = None
    metadata: ResponseMetadata


# =============================================================================
# ERROR RESPONSE
# =============================================================================

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    data: None = None
    error: ErrorDetail
    metadata: ResponseMetadata
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_FILE_FORMAT",
                    "message": "上传的文件不是有效的 JSON 格式",
                    "details": {"file_type": "text/plain"}
                },
                "metadata": {
                    "task_id": "error-task-id",
                    "timestamp": "2025-11-10T12:00:00Z",
                    "processing_time": 0.01
                }
            }
        }


# =============================================================================
# VALIDATION MODELS
# =============================================================================

class FileValidationResult(BaseModel):
    """File validation result"""
    is_valid: bool = Field(description="Validation status")
    file_size: int = Field(description="File size in bytes")
    content_type: str = Field(description="MIME type")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if invalid"
    )
