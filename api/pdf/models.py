"""
PDF Extraction API Models

Data models for PDF business plan extraction endpoints.

Author: AI Assistant
Date: 2025-01-13
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# REQUEST MODELS
# =============================================================================

class PDFExtractionRequest(BaseModel):
    """Request model for PDF extraction"""
    user_id: Optional[str] = Field(default=None, description="User identifier")
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    high_resolution: bool = Field(default=False, description="Enable high-resolution mode")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "project_id": "project_456",
                "high_resolution": False
            }
        }


# =============================================================================
# RESPONSE DATA MODELS
# =============================================================================

class ExtractionResult(BaseModel):
    """Structured extraction result from PDF"""
    project_source: str = Field(description="Source identifier (e.g., BP, pitch deck)")
    project_name: Optional[str] = Field(default=None, description="Project name")
    company_name: str = Field(description="Company/project name")
    industry: str = Field(description="Industry category")
    founding_year: Optional[int] = Field(default=None, description="Company founding year")
    
    core_team: List[Dict[str, str]] = Field(
        description="Core team members (name, position, background)",
        default_factory=list
    )
    
    product_description: Optional[str] = Field(
        default=None,
        description="Product/service description"
    )
    
    business_model: Optional[str] = Field(
        default=None,
        description="Business model and revenue streams"
    )
    
    target_market: Optional[str] = Field(
        default=None,
        description="Target market and customer segments"
    )
    
    financing_history: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Financing history (rounds, amounts, investors)"
    )
    
    financial_status: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Financial status (current and future)"
    )
    
    funding_needs: Optional[str] = Field(
        default=None,
        description="Current funding requirements"
    )
    
    competitive_advantage: Optional[str] = Field(
        default=None,
        description="Key competitive advantages"
    )
    
    milestones: Optional[str] = Field(
        default=None,
        description="Key achievements and milestones"
    )
    
    risks: Optional[str] = Field(
        default=None,
        description="Main business risks"
    )
    
    keywords: List[str] = Field(
        description="Extracted keywords (5-10)",
        default_factory=list
    )
    
    summary: Optional[str] = Field(
        default=None,
        description="One-sentence project summary"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_source": "BP",
                "company_name": "AI Innovation Inc.",
                "industry": "人工智能",
                "founding_year": 2023,
                "core_team": [
                    {"name": "张三", "position": "CEO", "background": "前阿里巴巴技术专家"}
                ],
                "product_description": "基于大模型的智能客服系统",
                "keywords": ["人工智能", "大模型", "客服", "SaaS", "企业服务"],
                "summary": "为企业提供基于大模型的智能客服解决方案"
            }
        }


class TaskStatusData(BaseModel):
    """Task status information"""
    task_id: str = Field(description="Task identifier")
    status: str = Field(description="Task status (pending/processing/completed/failed)")
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Processing progress (0-100%)"
    )
    result: Optional[ExtractionResult] = Field(
        default=None,
        description="Extraction result (if completed)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (if failed)"
    )
    original_filename: Optional[str] = Field(
        default=None,
        description="Original PDF filename"
    )
    pdf_url: Optional[str] = Field(
        default=None,
        description="OSS URL of the original PDF"
    )
    extracted_info: Optional[Dict[str, Any]] = Field(
      default=None,
      description="Full structured extraction payload"
    )
    extracted_info_url: Optional[str] = Field(
        default=None,
        description="OSS URL of the extracted JSON"
    )
    extracted_info_object_key: Optional[str] = Field(
        default=None,
        description="OSS object key for the extracted JSON"
    )
    company_name: Optional[str] = Field(
        default=None,
        description="Extracted company name"
    )
    industry: Optional[str] = Field(
        default=None,
        description="Extracted industry"
    )
    project_contact: Optional[str] = Field(
        default=None,
        description="Primary project contact person"
    )
    project_leader: Optional[str] = Field(
        default=None,
        description="Project leader name"
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Project name"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="Task creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="Last update timestamp"
    )
    download_urls: Optional[Dict[str, str]] = Field(
        default=None,
        description="Download URLs for result files"
    )


class TaskSummary(BaseModel):
    """Brief task summary for list view"""
    task_id: str = Field(description="Task identifier")
    filename: str = Field(description="Original PDF filename")
    status: str = Field(description="Task status")
    company_name: Optional[str] = Field(default=None, description="Extracted company name")
    industry: Optional[str] = Field(default=None, description="Extracted industry")
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Update timestamp")


class QueueStatus(BaseModel):
    """Processing queue status"""
    is_running: bool = Field(description="Whether queue is active")
    queue_length: int = Field(description="Current queue length")
    active_tasks: int = Field(description="Number of tasks currently processing")
    completed_tasks: int = Field(description="Number of tasks completed (lifetime)")
    active_workers: int = Field(description="Number of active workers")
    pending_tasks: int = Field(description="Number of pending tasks")
    queue_capacity: int = Field(description="Maximum queue size")
    max_workers: int = Field(description="Configured maximum worker count")
    max_queue_size: int = Field(description="Configured queue capacity")


# =============================================================================
# STANDARD RESPONSE MODELS
# =============================================================================

class PDFExtractionResponse(BaseModel):
    """Response for PDF extraction submission"""
    success: bool = Field(description="Request success status")
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Response data (task_id, status, estimated_time)"
    )
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(description="Request metadata")


class BatchUploadResponse(BaseModel):
    """Response for batch PDF upload"""
    success: bool = Field(description="Request success status")
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Batch upload results (task_ids, total_submitted, failed_submissions)"
    )
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(description="Request metadata")


class PDFTaskStatusResponse(BaseModel):
    """Response for task status query"""
    success: bool = Field(description="Request success status")
    data: Optional[TaskStatusData] = Field(default=None, description="Task status data")
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(description="Request metadata")


class PDFTaskListResponse(BaseModel):
    """Response for task list query"""
    success: bool = Field(description="Request success status")
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task list data (tasks, total, page, page_size)"
    )
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(description="Request metadata")


class QueueStatusResponse(BaseModel):
    """Response for queue status query"""
    success: bool = Field(description="Request success status")
    data: Optional[QueueStatus] = Field(default=None, description="Queue status data")
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(description="Request metadata")


# =============================================================================
# ERROR RESPONSE
# =============================================================================

class ErrorDetail(BaseModel):
    """Error detail information"""
    code: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    data: None = None
    error: ErrorDetail
    metadata: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "data": None,
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "PDF file exceeds maximum size limit",
                    "details": {"max_size_mb": 50, "actual_size_mb": 75.3}
                },
                "metadata": {
                    "timestamp": "2025-01-13T12:00:00Z"
                }
            }
        }
