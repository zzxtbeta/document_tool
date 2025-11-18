"""
PDF Extraction API Routes

FastAPI routes for PDF business plan extraction, task management, and queue monitoring.

Author: AI Assistant
Date: 2025-01-13
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import FileResponse, JSONResponse

from api.pdf.models import (
    PDFExtractionResponse,
    PDFTaskStatusResponse,
    PDFTaskListResponse,
    QueueStatusResponse,
    BatchUploadResponse
)
from pipelines.pdf_extraction_service import PDFExtractionService
from pipelines.async_task_queue import get_task_queue
from db.pdf_operations import list_pdf_extraction_tasks, get_pdf_extraction_task, count_tasks_by_status

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/pdf", tags=["pdf-extraction"])

# Initialize service
try:
    pdf_service = PDFExtractionService()
    logger.info("PDFExtractionService initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize PDFExtractionService: {e}")
    pdf_service = None

# Get task queue instance
task_queue = get_task_queue()


# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_FILE_SIZE_MB = int(os.getenv("PDF_MAX_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_BATCH_SIZE = int(os.getenv("PDF_MAX_BATCH_SIZE", "10"))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _validate_pdf_file(file: UploadFile) -> float:
    """
    Validate uploaded PDF file.
    
    Returns:
        float: File size in MB
    
    Raises:
        HTTPException: If validation fails
    """
    # Check file extension
    filename = file.filename or ""
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected PDF, got: {Path(filename).suffix}"
        )
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    file_size_mb = file_size / (1024 * 1024)
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE_MB}MB, got: {file_size_mb:.2f}MB"
        )
    
    logger.info(f"Validated PDF: {filename} ({file_size_mb:.2f}MB)")
    return file_size_mb


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/extract", response_model=PDFExtractionResponse)
async def extract_pdf_bp(
    file: UploadFile = File(..., description="PDF business plan file to extract"),
    user_id: Optional[str] = Form(None, description="User ID (optional)"),
    project_id: Optional[str] = Form(None, description="Project ID (optional)"),
    high_resolution: bool = Form(False, description="Enable high-resolution mode for complex PDFs"),
):
    """
    Submit a PDF business plan for extraction.
    
    Extracts structured information including:
    - Company name, industry, founding year
    - Core team members (CEO, CTO, CFO, etc.)
    - Product description
    - Business model and target market
    - Financing history and funding needs
    - Key milestones and risks
    - Keywords and summary
    
    **Parameters:**
    - `file`: PDF file (max 50MB)
    - `user_id`: Optional user identifier
    - `project_id`: Optional project identifier
    - `high_resolution`: Enable high-res mode (slower, more accurate)
    
    **Returns:**
    - `task_id`: Unique identifier to query task status
    - `status`: Task status (PENDING/PROCESSING/COMPLETED/FAILED)
    - `estimated_time`: Estimated processing time in seconds
    """
    if pdf_service is None:
        raise HTTPException(
            status_code=503,
            detail="PDF extraction service is not available. Check configuration."
        )
    
    request_time = datetime.now()
    
    try:
        # Validate file
        file_size_mb = _validate_pdf_file(file)
        
        # Save file to temporary directory
        import tempfile
        from pathlib import Path
        
        temp_dir = Path(tempfile.gettempdir()) / "pdf_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        filename = file.filename or "unknown.pdf"
        temp_file_path = temp_dir / f"{uuid4()}_{filename}"
        
        # Write uploaded file to temp location
        file_content = await file.read()
        temp_file_path.write_bytes(file_content)
        
        try:
            # Submit extraction task
            task_id = await pdf_service.submit_extraction(
                pdf_file_path=temp_file_path,
                user_id=user_id or "default_user",
                project_id=project_id or "defaultProject",
                source_filename=filename
            )
        finally:
            # Clean up temp file
            if temp_file_path.exists():
                temp_file_path.unlink()
        
        # Estimate processing time (30-60 seconds)
        estimated_time = 30 + (file_size_mb * 2)  # 2 seconds per MB
        
        response = PDFExtractionResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "pending",
                "estimated_time": int(estimated_time)
            },
            error=None,
            metadata={
                "task_id": task_id,
                "timestamp": request_time.isoformat(),
                "filename": file.filename,
                "file_size_mb": round(file_size_mb, 2),
                "high_resolution": high_resolution
            }
        )
        
        logger.info(f"PDF extraction task submitted: {task_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit PDF extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit extraction task: {str(e)}"
        )


@router.post("/extract/batch", response_model=BatchUploadResponse)
async def extract_batch_pdfs(
    files: List[UploadFile] = File(..., description="Multiple PDF files to extract"),
    user_id: Optional[str] = Form(None, description="User ID (optional)"),
    project_id: Optional[str] = Form(None, description="Project ID (optional)"),
    high_resolution: bool = Form(False, description="Enable high-resolution mode"),
):
    """
    Submit multiple PDF business plans for batch extraction.
    
    Supports uploading up to 10 PDFs at once. Each PDF is processed independently
    in the async queue.
    
    **Parameters:**
    - `files`: List of PDF files (max 10 files, each max 50MB)
    - `user_id`: Optional user identifier
    - `project_id`: Optional project identifier  
    - `high_resolution`: Enable high-res mode for all files
    
    **Returns:**
    - `task_ids`: List of task IDs for each submitted file
    - `total_submitted`: Total number of tasks submitted
    - `failed_submissions`: List of files that failed validation
    """
    if pdf_service is None:
        raise HTTPException(
            status_code=503,
            detail="PDF extraction service is not available."
        )
    
    # Validate batch size
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Max batch size: {MAX_BATCH_SIZE}, got: {len(files)}"
        )
    
    request_time = datetime.now()
    task_ids = []
    failed_submissions = []
    
    for file in files:
        try:
            # Validate each file
            file_size_mb = _validate_pdf_file(file)
            
            # Save file to temporary directory
            import tempfile
            from pathlib import Path
            
            temp_dir = Path(tempfile.gettempdir()) / "pdf_uploads"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            filename = file.filename or "unknown.pdf"
            temp_file_path = temp_dir / f"{uuid4()}_{filename}"
            
            # Write uploaded file to temp location
            file_content = await file.read()
            temp_file_path.write_bytes(file_content)
            
            try:
                # Submit extraction task
                task_id = await pdf_service.submit_extraction(
                    pdf_file_path=temp_file_path,
                    user_id=user_id or "default_user",
                    project_id=project_id or "defaultProject",
                    source_filename=filename
                )
            finally:
                # Clean up temp file
                if temp_file_path.exists():
                    temp_file_path.unlink()
            
            task_ids.append({
                "task_id": task_id,
                "filename": file.filename,
                "file_size_mb": round(file_size_mb, 2)
            })
            
            logger.info(f"Batch task submitted: {task_id} for {file.filename}")
        
        except HTTPException as e:
            failed_submissions.append({
                "filename": file.filename,
                "error": e.detail
            })
            logger.warning(f"Failed to submit {file.filename}: {e.detail}")
        except Exception as e:
            failed_submissions.append({
                "filename": file.filename,
                "error": str(e)
            })
            logger.error(f"Unexpected error for {file.filename}: {e}")
    
    response = BatchUploadResponse(
        success=True,
        data={
            "task_ids": task_ids,
            "total_submitted": len(task_ids),
            "failed_submissions": failed_submissions
        },
        error=None,
        metadata={
            "timestamp": request_time.isoformat(),
            "total_files": len(files),
            "high_resolution": high_resolution
        }
    )
    
    logger.info(f"Batch upload completed: {len(task_ids)}/{len(files)} successful")
    return response


@router.get("/extract/{task_id}", response_model=PDFTaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Query the status and result of a PDF extraction task.
    
    **Parameters:**
    - `task_id`: Task identifier from submission response
    
    **Returns:**
    - `status`: Current task status
    - `progress`: Processing progress (0-100%)
    - `result`: Extraction result (if completed)
    - `download_urls`: URLs to download result files
    """
    try:
        task = await get_pdf_extraction_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task not found: {task_id}"
            )
        
        # Build download URLs if completed
        download_urls = None
        if task["task_status"] == "SUCCEEDED" and task.get("extracted_info_url"):
            download_urls = {
                "json": task.get("extracted_info_url"),
                "original_pdf": task.get("pdf_url")
            }
        
        # 映射任务状态：SUCCEEDED -> completed
        task_status = task["task_status"]
        if task_status == "SUCCEEDED":
            frontend_status = "completed"
        elif task_status in ["PENDING", "PROCESSING", "FAILED"]:
            frontend_status = task_status.lower()
        else:
            frontend_status = "pending"
        
        submitted_at = task.get("submitted_at")
        updated_at = task.get("updated_at")
        completed_at = task.get("completed_at")

        # 统一错误字段为人类可读字符串
        error_payload = task.get("error")
        error_message = None
        if error_payload:
            if isinstance(error_payload, dict):
                error_message = error_payload.get("message") or error_payload.get("detail") or str(error_payload)
            else:
                error_message = str(error_payload)
        
        response = PDFTaskStatusResponse(
            success=True,
            data={
                "task_id": task_id,
                "original_filename": task.get("source_filename", "unknown.pdf"),
                "status": frontend_status,
                "progress": task.get("progress"),
                "error": error_message,
                "created_at": submitted_at.isoformat() if isinstance(submitted_at, datetime) else None,
                "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
                "submitted_at": submitted_at.isoformat() if isinstance(submitted_at, datetime) else None,
                "completed_at": completed_at.isoformat() if isinstance(completed_at, datetime) else None,
                "pdf_url": task.get("pdf_url"),
                "extracted_info": task.get("extracted_info"),
                "extracted_info_url": task.get("extracted_info_url"),
                "extracted_info_object_key": task.get("extracted_info_object_key"),
                "company_name": task.get("company_name"),
                "industry": task.get("industry"),
                "project_contact": task.get("project_contact"),
                "project_leader": task.get("project_leader"),
                "download_urls": download_urls
            },
            error=None,
            metadata={
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query task status: {str(e)}"
        )


@router.get("/extract", response_model=PDFTaskListResponse)
async def list_tasks(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending/processing/completed/failed)"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)")
):
    """
    List PDF extraction tasks with optional filters and pagination.
    
    **Parameters:**
    - `user_id`: Filter by user ID
    - `project_id`: Filter by project ID
    - `status`: Filter by task status
    - `industry`: Filter by extracted industry
    - `page`: Page number (starts from 1)
    - `page_size`: Items per page (max 100)
    
    **Returns:**
    - `tasks`: List of task summaries
    - `total`: Total number of matching tasks
    - `page`: Current page number
    - `page_size`: Items per page
    """
    try:
        tasks, total = await list_pdf_extraction_tasks(
            user_id=user_id,
            project_id=project_id,
            status=status,
            industry=industry,
            page=page,
            page_size=page_size
        )
        
        # Format task summaries
        task_summaries = []
        for task in tasks:
            submitted_at = task.get("submitted_at")
            updated_at = task.get("updated_at")
            error_payload = task.get("error")
            if isinstance(error_payload, dict):
                summary_error = error_payload.get("message") or error_payload.get("detail") or str(error_payload)
            else:
                summary_error = str(error_payload) if error_payload else None
            
            # 映射任务状态：PENDING/PROCESSING/SUCCEEDED/FAILED -> pending/processing/completed/failed
            task_status = task["task_status"]
            if task_status == "SUCCEEDED":
                frontend_status = "completed"
            elif task_status in ["PENDING", "PROCESSING", "FAILED"]:
                frontend_status = task_status.lower()
            else:
                frontend_status = "pending"  # 默认值
            
            task_summaries.append({
                "task_id": task["task_id"],
                "original_filename": task.get("source_filename") or task.get("filename", "unknown.pdf"),
                "status": frontend_status,
                "company_name": task.get("company_name"),
                "industry": task.get("industry"),
                "created_at": submitted_at.isoformat() if submitted_at else None,
                "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
                "pdf_url": task.get("pdf_url"),
                "extracted_info_url": task.get("extracted_info_url"),
                "error": summary_error,
            })
        
        response = PDFTaskListResponse(
            success=True,
            data={
                "tasks": task_summaries,
                "total": total,
                "page": page,
                "page_size": page_size
            },
            error=None,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "filters": {
                    "user_id": user_id,
                    "project_id": project_id,
                    "status": status,
                    "industry": industry
                }
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """
    Get current status of the PDF processing queue.
    
    **Returns:**
    - `active_workers`: Number of currently processing tasks
    - `pending_tasks`: Number of tasks waiting in queue
    - `queue_capacity`: Maximum queue size
    - `is_running`: Whether the queue is active
    """
    try:
        status = task_queue.get_status()
        try:
            completed_count = await count_tasks_by_status("SUCCEEDED")
            status["completed_tasks"] = completed_count
        except Exception as count_err:
            logger.warning(f"Failed to count completed tasks: {count_err}")
        
        response = QueueStatusResponse(
            success=True,
            data=status,
            error=None,
            metadata={
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.get("/download/{task_id}/{file_type}")
async def download_task_file(task_id: str, file_type: str):
    """
    Download result files for a completed task.
    
    **Parameters:**
    - `task_id`: Task identifier
    - `file_type`: File type to download ('json' or 'pdf')
    
    **Returns:**
    - File download response (FileResponse)
    """
    if file_type not in ["json", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: 'json', 'pdf'. Got: {file_type}"
        )
    
    try:
        task = await get_pdf_extraction_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        # 构建本地文件路径
        task_dir = Path("uploads") / "pdf" / task_id
        source_filename = task.get("source_filename", "unknown.pdf")
        pdf_name = Path(source_filename).stem
        
        if file_type == "json":
            # JSON 文件路径
            json_filename = f"{pdf_name}_extracted_info.json"
            file_path = task_dir / json_filename
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Extracted JSON not found. Task may not be completed yet."
                )
            
            return FileResponse(
                path=str(file_path),
                filename=json_filename,
                media_type="application/json"
            )
        
        else:  # pdf
            # PDF 文件路径
            file_path = task_dir / source_filename
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Original PDF not found locally."
                )
            
            return FileResponse(
                path=str(file_path),
                filename=source_filename,
                media_type="application/pdf"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for PDF extraction service."""
    queue_status = task_queue.get_status()
    
    return {
        "status": "healthy" if pdf_service else "unavailable",
        "service": "pdf-extraction",
        "pipeline_available": pdf_service is not None,
        "queue_status": {
            "running": queue_status["is_running"],
            "active_workers": queue_status["active_workers"],
            "pending_tasks": queue_status["pending_tasks"]
        },
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "max_batch_size": MAX_BATCH_SIZE,
        "model": "qwen-vl-max"
    }
