"""
FastAPI Knowledge Graph Extraction API

RESTful API for document knowledge graph extraction service.

Author: AI Assistant
Date: 2025-11-10
"""

import os
import json
import uuid
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import dotenv

from api_models import (
    ExtractRequest, ExtractResponse, AsyncTaskResponse, TaskResponse,
    HealthResponse, ErrorResponse, ErrorDetail, ResponseMetadata,
    TaskStatus, TaskStatusData, ExtractResponseData, KnowledgeGraphData
)
from text_pipline import TextKnowledgeGraphPipeline, KnowledgeGraph

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """API configuration from environment variables"""
    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_VERSION: str = "1.2.0"
    
    # File storage
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))  # 50MB
    
    # Task management
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "600"))  # 10 minutes
    RESULT_TTL: int = int(os.getenv("RESULT_TTL", str(24 * 3600)))  # 24 hours
    
    # Pipeline defaults
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "512"))
    DEFAULT_MAX_WORKERS: int = int(os.getenv("DEFAULT_MAX_WORKERS", "3"))
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.3"))
    DEFAULT_SIMILARITY: float = float(os.getenv("DEFAULT_SIMILARITY", "0.85"))
    
    # File size thresholds for sync/async
    SYNC_FILE_SIZE_THRESHOLD: int = 10 * 1024 * 1024  # 10MB
    SYNC_PAGE_COUNT_THRESHOLD: int = 50
    
    @classmethod
    def ensure_directories(cls):
        """Ensure upload and output directories exist"""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


config = Config()


# =============================================================================
# TASK STORAGE (In-memory for MVP)
# =============================================================================

class TaskStore:
    """In-memory task status storage"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskStatusData] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(self, task_id: str) -> TaskStatusData:
        """Create a new task"""
        async with self._lock:
            task_data = TaskStatusData(
                task_id=task_id,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            self.tasks[task_id] = task_data
            return task_data
    
    async def get_task(self, task_id: str) -> Optional[TaskStatusData]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    async def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        result: Optional[ExtractResponseData] = None,
        error: Optional[str] = None,
        download_urls: Optional[Dict[str, str]] = None
    ):
        """Update task status"""
        async with self._lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            if status:
                task.status = status
            if progress is not None:
                task.progress = progress
            if result:
                task.result = result
            if error:
                task.error = error
            if download_urls:
                task.download_urls = download_urls
            task.updated_at = datetime.utcnow().isoformat()
    
    async def cleanup_old_tasks(self):
        """Remove tasks older than TTL"""
        async with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(seconds=config.RESULT_TTL)
            to_remove = []
            
            for task_id, task in self.tasks.items():
                created_at = datetime.fromisoformat(task.created_at)
                if created_at < cutoff_time:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
                # Clean up files
                task_upload_dir = config.UPLOAD_DIR / task_id
                task_output_dir = config.OUTPUT_DIR / task_id
                if task_upload_dir.exists():
                    import shutil
                    shutil.rmtree(task_upload_dir)
                if task_output_dir.exists():
                    import shutil
                    shutil.rmtree(task_output_dir)
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old tasks")


task_store = TaskStore()


# =============================================================================
# LIFESPAN EVENTS
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Knowledge Graph Extraction API")
    config.ensure_directories()
    logger.info(f"📁 Upload directory: {config.UPLOAD_DIR}")
    logger.info(f"📁 Output directory: {config.OUTPUT_DIR}")
    
    # Start cleanup task
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # Every hour
            await task_store.cleanup_old_tasks()
    
    cleanup_task = asyncio.create_task(cleanup_loop())
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down API")
    cleanup_task.cancel()


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Knowledge Graph Extraction API",
    description="RESTful API for extracting knowledge graphs from documents using LLM",
    version=config.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# =============================================================================
# MIDDLEWARE
# =============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID and logging middleware
@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    """Add request ID and log requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to logging context
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.request_id = request_id
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {processing_time:.3f}s"
        )
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
        
        return response
    
    finally:
        logging.setLogRecordFactory(old_factory)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=exc.detail,
                details=None
            ),
            metadata=ResponseMetadata(
                task_id=getattr(request.state, 'request_id', 'unknown'),
                timestamp=datetime.utcnow().isoformat()
            )
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An internal server error occurred",
                details={"exception": str(exc)}
            ),
            metadata=ResponseMetadata(
                task_id=getattr(request.state, 'request_id', 'unknown'),
                timestamp=datetime.utcnow().isoformat()
            )
        ).model_dump()
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def validate_uploaded_file(file: UploadFile) -> Optional[ErrorDetail]:
    """
    Validate uploaded file.
    
    Returns:
        ErrorDetail if validation fails, None if valid
    """
    # Check content type
    if file.content_type not in ["application/json", "text/json"]:
        return ErrorDetail(
            code="INVALID_CONTENT_TYPE",
            message=f"Invalid content type: {file.content_type}. Expected application/json",
            details={"content_type": file.content_type}
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset
    
    if file_size > config.MAX_UPLOAD_SIZE:
        return ErrorDetail(
            code="FILE_TOO_LARGE",
            message=f"File size ({file_size} bytes) exceeds maximum ({config.MAX_UPLOAD_SIZE} bytes)",
            details={"file_size": file_size, "max_size": config.MAX_UPLOAD_SIZE}
        )
    
    # Try to parse as JSON
    try:
        content = await file.read()
        data = json.loads(content)
        await file.seek(0)  # Reset for later use
        
        # Check if it's a list
        if not isinstance(data, list):
            return ErrorDetail(
                code="INVALID_JSON_STRUCTURE",
                message="JSON must be an array of content items",
                details={"type": type(data).__name__}
            )
        
        # Check for required fields in first item
        if data and len(data) > 0:
            first_item = data[0]
            if "type" not in first_item:
                return ErrorDetail(
                    code="MISSING_REQUIRED_FIELD",
                    message="Content items must have 'type' field",
                    details={"missing_field": "type"}
                )
        
    except json.JSONDecodeError as e:
        return ErrorDetail(
            code="INVALID_JSON",
            message="File is not valid JSON",
            details={"error": str(e)}
        )
    except Exception as e:
        return ErrorDetail(
            code="FILE_READ_ERROR",
            message="Error reading file",
            details={"error": str(e)}
        )
    
    return None


def should_process_async(file_size: int, content: list) -> bool:
    """Determine if file should be processed asynchronously"""
    if file_size > config.SYNC_FILE_SIZE_THRESHOLD:
        return True
    
    # Count pages
    page_count = len(set(item.get("page_idx", 0) for item in content if item.get("type") == "text"))
    if page_count > config.SYNC_PAGE_COUNT_THRESHOLD:
        return True
    
    return False


def knowledge_graph_to_response_data(graph: KnowledgeGraph) -> ExtractResponseData:
    """Convert KnowledgeGraph to response data"""
    # Extract raw graph
    raw_graph = KnowledgeGraphData(
        entities={name: entity.model_dump() for name, entity in graph.entities.items()},
        relations=[rel.model_dump() for rel in graph.relations],
        metadata=graph.metadata
    )
    
    # Extract aligned graph
    aligned_graph = KnowledgeGraphData(
        entities={name: entity.model_dump() for name, entity in graph.aligned_entities.items()},
        relations=[rel.model_dump() for rel in graph.aligned_relations],
        aligned_entities={name: entity.model_dump() for name, entity in graph.aligned_entities.items()},
        aligned_relations=[rel.model_dump() for rel in graph.aligned_relations],
        metadata=graph.metadata
    )
    
    # Create summary
    summary = {
        "total_raw_entities": len(graph.entities),
        "total_raw_relations": len(graph.relations),
        "total_aligned_entities": len(graph.aligned_entities),
        "total_aligned_relations": len(graph.aligned_relations),
        "entity_types": graph.metadata.get("entity_types", []),
        "aligned_entity_types": graph.metadata.get("aligned_entity_types", [])
    }
    
    return ExtractResponseData(
        raw_graph=raw_graph,
        aligned_graph=aligned_graph,
        summary=summary
    )


async def process_extraction_task(
    task_id: str,
    file_path: Path,
    extract_params: ExtractRequest
):
    """Background task for processing extraction"""
    try:
        await task_store.update_task(task_id, status=TaskStatus.PROCESSING, progress=0.0)
        
        logger.info(f"Task {task_id}: Starting extraction")
        
        # Create pipeline
        pipeline = TextKnowledgeGraphPipeline(
            chunk_size=extract_params.chunk_size,
            max_workers=extract_params.max_workers,
            temperature=extract_params.temperature,
            similarity_threshold=extract_params.similarity_threshold,
            parallel=extract_params.parallel
        )
        
        # Process document
        await task_store.update_task(task_id, progress=25.0)
        graph = pipeline.process_document(str(file_path))
        
        # Save results
        await task_store.update_task(task_id, progress=75.0)
        output_dir = config.OUTPUT_DIR / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_base = output_dir / "result"
        pipeline.save_graph(graph, str(output_base))
        
        # Create response data
        result_data = knowledge_graph_to_response_data(graph)
        
        # Update task
        download_urls = {
            "raw": f"/api/v1/download/{task_id}/result_raw.json",
            "aligned": f"/api/v1/download/{task_id}/result_aligned.json"
        }
        
        await task_store.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100.0,
            result=result_data,
            download_urls=download_urls
        )
        
        logger.info(f"Task {task_id}: Completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id}: Failed with error: {e}", exc_info=True)
        await task_store.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=str(e)
        )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and LLM API availability.
    """
    # Check LLM API
    llm_available = False
    try:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        llm_available = bool(api_key)
    except Exception:
        pass
    
    return HealthResponse(
        status="healthy",
        version=config.API_VERSION,
        llm_available=llm_available,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/v1/extract", tags=["Extraction"])
async def extract_knowledge_graph(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="JSON document file"),
    chunk_size: Optional[int] = config.DEFAULT_CHUNK_SIZE,
    max_workers: Optional[int] = config.DEFAULT_MAX_WORKERS,
    temperature: Optional[float] = config.DEFAULT_TEMPERATURE,
    similarity_threshold: Optional[float] = config.DEFAULT_SIMILARITY,
    parallel: Optional[bool] = True
):
    """
    Extract knowledge graph from uploaded JSON document.
    
    - **Sync**: Small files (< 10MB, < 50 pages) return results immediately
    - **Async**: Large files return task_id for later retrieval
    """
    task_id = request.state.request_id
    start_time = time.time()
    
    # Validate file
    validation_error = await validate_uploaded_file(file)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error.message)
    
    # Save uploaded file
    task_upload_dir = config.UPLOAD_DIR / task_id
    task_upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = task_upload_dir / "input.json"
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse content to determine sync/async
    data = json.loads(content)
    is_async = should_process_async(len(content), data)
    
    # Create extraction parameters
    extract_params = ExtractRequest(
        chunk_size=chunk_size,
        max_workers=max_workers,
        temperature=temperature,
        similarity_threshold=similarity_threshold,
        parallel=parallel
    )
    
    if is_async:
        # Async processing
        await task_store.create_task(task_id)
        background_tasks.add_task(process_extraction_task, task_id, file_path, extract_params)
        
        return AsyncTaskResponse(
            data={
                "task_id": task_id,
                "status": "pending",
                "message": "Task submitted for processing. Use /api/v1/tasks/{task_id} to check status."
            },
            metadata=ResponseMetadata(
                task_id=task_id,
                timestamp=datetime.utcnow().isoformat()
            )
        )
    
    else:
        # Sync processing
        try:
            pipeline = TextKnowledgeGraphPipeline(
                chunk_size=extract_params.chunk_size,
                max_workers=extract_params.max_workers,
                temperature=extract_params.temperature,
                similarity_threshold=extract_params.similarity_threshold,
                parallel=extract_params.parallel
            )
            
            graph = pipeline.process_document(str(file_path))
            result_data = knowledge_graph_to_response_data(graph)
            
            processing_time = time.time() - start_time
            
            return ExtractResponse(
                data=result_data,
                metadata=ResponseMetadata(
                    task_id=task_id,
                    timestamp=datetime.utcnow().isoformat(),
                    processing_time=processing_time
                )
            )
        
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task_status(request: Request, task_id: str):
    """
    Query task status and results.
    
    Returns current task status, progress, and results if completed.
    """
    task = await task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return TaskResponse(
        data=task,
        metadata=ResponseMetadata(
            task_id=request.state.request_id,
            timestamp=datetime.utcnow().isoformat()
        )
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level="info"
    )
