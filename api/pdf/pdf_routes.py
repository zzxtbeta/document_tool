"""
PDF 处理接口 - 用于系统集成

此模块提供独立的 PDF 处理接口，接收已上传到 OSS 的 PDF 文件信息，
异步处理并返回提取结果。

Author: AI Assistant
Date: 2025-11-19
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.pdf.models import PDFExtractionResponse, PDFTaskStatusResponse, PDFTaskListResponse
from pipelines.pdf_extraction_service import PDFExtractionService
from db.pdf_operations import get_pdf_queue_task, list_pdf_queue_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pdf", tags=["pdf-processing"])


# 请求模型
class PDFProcessRequest(BaseModel):
    """PDF 批量处理请求"""
    oss_key_list: List[str] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="OSS 文件路径列表，例如: ['path/to/file1.pdf', 'path/to/file2.pdf']"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="项目 ID"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="用户 ID"
    )
    file_id_list: Optional[List[str]] = Field(
        default=None,
        description="文件 ID 列表，与 oss_key_list 长度一致"
    )
    high_resolution: bool = Field(
        default=False,
        description="是否启用高分辨率模式"
    )
    retry_count: int = Field(
        default=1,
        ge=0,
        le=3,
        description="失败重试次数 (0-3)"
    )


# 初始化服务
try:
    pdf_service = PDFExtractionService()
    logger.info("[PDF Extract] PDFExtractionService initialized for process routes")
except Exception as e:
    logger.error(f"[PDF Extract] Failed to initialize service: {e}")
    pdf_service = None


@router.post("/process", response_model=PDFExtractionResponse)
async def process_pdf_batch(request: PDFProcessRequest):
    """
    批量处理已上传到 OSS 的 PDF 文件。
    
    此接口用于与其他系统集成。当其他系统已将 PDF 上传到 OSS 时，
    调用此接口来异步处理 PDF 并提取结构化信息。
    
    **参数说明：**
    - `oss_key_list`: OSS 文件路径列表 (JSON 数组字符串)
      - 例如: `["projects/proj_123/files/bp1.pdf", "projects/proj_123/files/bp2.pdf"]`
    - `project_id`: 项目 ID（可选，无则使用 "default_project"）
    - `user_id`: 用户 ID（可选，无则使用 "default_user"）
    - `file_id_list`: 文件 ID 列表 (JSON 数组字符串，用于关联上传系统)
    - `high_resolution`: 启用高分辨率模式（可选）
    - `retry_count`: 失败重试次数，0-3（可选，默认 1）
    
    **返回值：**
    - `success`: 请求是否成功
    - `data`: 包含任务信息
      - `total`: 总文件数
      - `submitted`: 成功提交的文件数
      - `failed`: 失败的文件数
      - `tasks`: 任务详情列表
        - `task_id`: 处理任务 ID
        - `oss_key`: 对应的 OSS 文件路径
        - `file_id`: 关联的文件 ID
        - `status`: 任务状态 (pending)
      - `estimated_time`: 预计处理时间（秒）
    - `error`: 错误信息（仅在失败时返回）
    
    **使用示例：**
    ```bash
    curl -X POST http://localhost:8000/api/v1/pdf/process \\
      -F 'oss_key_list=["projects/proj_123/files/bp1.pdf", "projects/proj_123/files/bp2.pdf"]' \\
      -F 'project_id=proj_123' \\
      -F 'user_id=user_789' \\
      -F 'file_id_list=["file_456", "file_789"]' \\
      -F 'high_resolution=false' \\
      -F 'retry_count=1'
    ```
    
    **响应示例：**
    ```json
    {
        "success": true,
        "data": {
            "total": 2,
            "submitted": 2,
            "failed": 0,
            "tasks": [
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440001",
                    "oss_key": "projects/proj_123/files/bp1.pdf",
                    "file_id": "file_456",
                    "status": "pending"
                },
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440002",
                    "oss_key": "projects/proj_123/files/bp2.pdf",
                    "file_id": "file_789",
                    "status": "pending"
                }
            ],
            "estimated_time": 90
        },
        "error": null,
        "metadata": {
            "timestamp": "2025-11-19T20:56:00Z",
            "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
        }
    }
    ```
    """
    if pdf_service is None:
        raise HTTPException(
            status_code=503,
            detail="PDF extraction service is not available. Check configuration."
        )
    
    request_time = datetime.now()
    request_id = f"req_{request_time.timestamp()}"
    
    try:
        # 验证参数
        if len(request.oss_key_list) == 0:
            raise ValueError("oss_key_list cannot be empty")
        if len(request.oss_key_list) > 50:
            raise ValueError("oss_key_list cannot exceed 50 items")
        
        # 验证文件 ID 列表长度
        if request.file_id_list and len(request.file_id_list) != len(request.oss_key_list):
            raise ValueError("file_id_list length must match oss_key_list length")
        
        # 提交处理任务
        tasks = await pdf_service.submit_extraction_from_oss(
            oss_key_list=request.oss_key_list,
            project_id=request.project_id or "default_project",
            user_id=request.user_id or "default_user",
            file_id_list=request.file_id_list,
            high_resolution=request.high_resolution,
            retry_count=request.retry_count
        )
        
        # 构建响应
        response = PDFExtractionResponse(
            success=True,
            data={
                "total": len(request.oss_key_list),
                "submitted": len(tasks),
                "failed": 0,
                "tasks": tasks,
                "estimated_time": 45 * len(request.oss_key_list)  # 每个文件预计 45 秒
            },
            error=None,
            metadata={
                "timestamp": request_time.isoformat(),
                "request_id": request_id,
                "count": len(request.oss_key_list)
            }
        )
        
        logger.info(f"[PDF Extract] Batch process submitted: {len(request.oss_key_list)} files, request_id={request_id}")
        return response
    
    except ValueError as e:
        logger.warning(f"[PDF Extract] Invalid input: {e}, request_id={request_id}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[PDF Extract] Failed to submit batch process: {e}, request_id={request_id}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit batch process: {str(e)}"
        )


@router.get("/process/{task_id}", response_model=PDFTaskStatusResponse)
async def get_process_task_status(task_id: str):
    """
    查询 PDF 处理任务的状态和结果。
    
    **参数：**
    - `task_id`: 处理任务 ID（从 POST /api/v1/pdf/process 返回）
    
    **返回值：**
    - `status`: 任务状态 (pending/processing/completed/failed)
    - `extracted_info`: 提取的结构化信息（任务完成时）
    - `extracted_info_url`: OSS 中的 JSON 结果文件 URL
    - `download_urls`: 下载链接（JSON 和原始 PDF）
    
    **响应示例：**
    ```json
    {
        "success": true,
        "data": {
            "task_id": "7b39129e-d785-44d0-bbfc-55a467283aa5",
            "status": "completed",
            "extracted_info": {
                "company_name": "象量科技",
                "project_name": "AI+大数据投资研究智能体",
                "industry": "人工智能",
                "keywords": ["AI+智库", "全链条分析", ...]
            },
            "extracted_info_url": "https://..../extracted_info.json",
            "download_urls": {
                "json": "https://..../extracted_info.json",
                "original_pdf": "https://..../file.pdf"
            }
        }
    }
    ```
    """
    try:
        task = await get_pdf_queue_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task not found: {task_id}"
            )
        
        # Build download URLs if completed
        download_urls = None
        if task["task_status"] == "completed" and task.get("extracted_info_url"):
            download_urls = {
                "json": task.get("extracted_info_url"),
                "original_pdf": task.get("pdf_url")
            }
        
        # 任务状态直接使用（已是小写）
        frontend_status = task["task_status"]
        
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
                "submitted_at": submitted_at.isoformat() if isinstance(submitted_at, datetime) else None,
                "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
                "completed_at": completed_at.isoformat() if isinstance(completed_at, datetime) else None,
                "pdf_url": task.get("pdf_url"),
                "extracted_info": task.get("extracted_info"),
                "extracted_info_url": task.get("extracted_info_url"),
                "extracted_info_object_key": task.get("extracted_info_object_key"),
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
        logger.error(f"[PDF Extract] Failed to get task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query task status: {str(e)}"
        )


@router.get("/process", response_model=PDFTaskListResponse)
async def list_process_tasks(
    user_id: Optional[str] = Query(None, description="按用户 ID 筛选"),
    project_id: Optional[str] = Query(None, description="按项目 ID 筛选"),
    status: Optional[str] = Query(None, description="按状态筛选 (pending/processing/completed/failed)"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（最多 100）")
):
    """
    列出 PDF 处理任务，支持筛选和分页。
    
    **参数：**
    - `user_id`: 按用户 ID 筛选（可选）
    - `project_id`: 按项目 ID 筛选（可选）
    - `status`: 按任务状态筛选（可选）
    - `page`: 页码，从 1 开始（默认 1）
    - `page_size`: 每页数量，最多 100（默认 20）
    
    **返回值：**
    - `tasks`: 任务列表
    - `total`: 总任务数
    - `page`: 当前页码
    - `page_size`: 每页数量
    """
    try:
        tasks, total = await list_pdf_queue_tasks(
            user_id=user_id,
            project_id=project_id,
            status=status,
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
            
            # 任务状态直接使用（已是小写）
            task_status = task["task_status"]
            
            task_summaries.append({
                "task_id": task["task_id"],
                "status": task_status,
                "original_filename": task.get("source_filename", "unknown.pdf"),
                "submitted_at": submitted_at.isoformat() if isinstance(submitted_at, datetime) else None,
                "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
                "error": summary_error
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
                "total_pages": (total + page_size - 1) // page_size
            }
        )
        
        return response
    
    except Exception as e:
        logger.error(f"[PDF Extract] Failed to list tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tasks: {str(e)}"
        )
