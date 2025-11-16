"""
Audio Transcription API Routes

FastAPI routes for audio upload, transcription, and meeting minutes generation.

Author: AI Assistant
Date: 2025-11-13
"""

import os
import uuid
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse

from api.audio_models import (
    AudioTranscriptionResponse,
    AudioTranscriptionMarkdownResponse,
    AudioTranscriptionOptions,
    AsyncTaskResponse
)
from pipelines.audio_pipeline import AudioPipeline

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/audio", tags=["audio"])

# Initialize pipeline
try:
    audio_pipeline = AudioPipeline()
except Exception as e:
    logger.error(f"Failed to initialize AudioPipeline: {e}")
    audio_pipeline = None


# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_FILE_SIZE_MB = int(os.getenv("AUDIO_MAX_FILE_SIZE", "100"))  # 100MB default
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ASYNC_THRESHOLD_SECONDS = int(os.getenv("AUDIO_ASYNC_THRESHOLD", "600"))  # 10 minutes
AUDIO_STORAGE_PATH = Path("uploads/audios")
AUDIO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def should_process_async(file_size_mb: float) -> bool:
    """
    Determine if audio should be processed asynchronously.
    
    Args:
        file_size_mb: File size in MB
        
    Returns:
        True if should process async, False otherwise
    """
    # Estimate: 1MB ≈ 60 seconds of audio
    estimated_duration = file_size_mb * 60
    
    return estimated_duration >= ASYNC_THRESHOLD_SECONDS


def save_uploaded_file(upload_file: UploadFile, task_id: str, output_dir: str = None) -> Path:
    """
    Save uploaded audio file to disk.
    
    Args:
        upload_file: FastAPI UploadFile object
        task_id: Unique task identifier
        output_dir: Custom output directory (optional)
        
    Returns:
        Path to saved file
    """
    # Validate and resolve output directory
    if output_dir:
        # Security check: prevent path traversal
        if '..' in output_dir or output_dir.startswith('/'):
            raise ValueError("Invalid output_dir: path traversal not allowed")
        
        base_dir = Path(output_dir).resolve()
    else:
        base_dir = AUDIO_STORAGE_PATH
    
    # Create task directory
    task_dir = base_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension
    filename = upload_file.filename or "audio"
    ext = Path(filename).suffix or ".m4a"
    
    # Save file
    file_path = task_dir / f"input{ext}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    
    logger.info(f"Saved uploaded file: {file_path}")
    return file_path


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    output_format: str = Form("json", description="Output format: 'json' or 'markdown'"),
    output_dir: Optional[str] = Form(None, description="Custom output directory (optional)"),
    enable_itn: bool = Form(True, description="Enable inverse text normalization"),
    asr_context: Optional[str] = Form(None, description="ASR context for specialized terminology"),
    language: Optional[str] = Form(None, description="Audio language code (e.g., 'zh', 'en')")
):
    """
    Transcribe audio file and generate meeting minutes.
    
    Supports formats: m4a, mp3, wav, flac, opus, aac
    
    **Output Formats:**
    - `json` (default): Returns structured JSON with meeting_minutes object
    - `markdown`: Returns Markdown formatted content and saves .md file
    
    **Parameters:**
    - `file`: Audio file to upload (max 100MB)
    - `output_format`: 'json' or 'markdown' (default: 'json')
    - `output_dir`: Custom output directory, relative path (default: 'uploads/audios')
    - `enable_itn`: Enable inverse text normalization in ASR (default: true)
    - `asr_context`: Custom context for ASR to improve recognition of specialized terms
      Example: "This discussion involves medical terms like CT scan, MRI, blood test"
    - `language`: Specify audio language ('zh', 'en', 'ja', 'ko', etc.) to improve accuracy
      If not specified, language will be auto-detected
    
    **Response:**
    - For `json` format: Returns AudioTranscriptionResponse with structured data
    - For `markdown` format: Returns markdown_content, file path, and download URL
    
    Args:
        file: Audio file upload
        output_format: Output format ('json' or 'markdown')
        output_dir: Custom output directory
        enable_itn: Enable inverse text normalization in ASR
        asr_context: ASR context for specialized terminology
        language: Audio language code
        
    Returns:
        AudioTranscriptionResponse (json) or AudioTranscriptionMarkdownResponse (markdown)
    """
    # Check if pipeline is initialized
    if audio_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Audio processing service is not available. Check DASHSCOPE_API_KEY."
        )
    
    # Validate output_format
    if output_format not in ["json", "markdown"]:
        raise HTTPException(
            status_code=400,
            detail="output_format must be 'json' or 'markdown'"
        )
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    request_time = datetime.now()
    
    try:
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start
        
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
            )
        
        # Validate file format
        filename = file.filename or ""
        ext = Path(filename).suffix.lstrip('.').lower()
        supported_formats = ['m4a', 'mp3', 'wav', 'flac', 'opus', 'aac']
        
        if ext not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}. Supported: {', '.join(supported_formats)}"
            )
        
        logger.info(f"Processing audio upload: {filename} ({file_size_mb:.2f}MB), format: {output_format}")
        
        # Check if should process async
        if should_process_async(file_size_mb):
            logger.warning(f"Large file detected ({file_size_mb:.2f}MB), but async processing not yet implemented")
        
        # Save uploaded file
        try:
            file_path = save_uploaded_file(file, task_id, output_dir)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Process audio
        try:
            result = audio_pipeline.process(
                str(file_path), 
                enable_itn=enable_itn,
                asr_context=asr_context,
                language=language
            )
            
            # Build response based on output_format
            if output_format == "markdown":
                # Save as Markdown file
                md_filename = f"{Path(filename).stem}_minutes.md"
                md_path = file_path.parent / md_filename
                
                audio_pipeline.save_as_markdown(
                    meeting_minutes=result.meeting_minutes,
                    output_path=md_path,
                    transcript=result.transcription_text
                )
                
                # Read Markdown content
                markdown_content = md_path.read_text(encoding='utf-8')
                
                # Build Markdown response
                response = AudioTranscriptionMarkdownResponse(
                    success=True,
                    transcript=result.transcription_text,
                    markdown_content=markdown_content,
                    markdown_file_path=str(md_path),
                    download_url=f"/api/v1/audio/download/{task_id}",
                    processing_stats=result.processing_stats,
                    audio_metadata=result.audio_metadata,
                    error=None,
                    metadata={
                        "task_id": task_id,
                        "timestamp": request_time.isoformat(),
                        "filename": filename,
                        "file_size_mb": round(file_size_mb, 2),
                        "processing_time": result.processing_stats.total_time,
                        "output_format": "markdown"
                    }
                )
                
                logger.info(f"Audio processing successful (Markdown): {task_id}")
                return response
            
            else:  # json format (default)
                # Build JSON response (backward compatible)
                response = AudioTranscriptionResponse(
                    success=True,
                    data=result,
                    error=None,
                    metadata={
                        "task_id": task_id,
                        "timestamp": request_time.isoformat(),
                        "filename": filename,
                        "file_size_mb": round(file_size_mb, 2),
                        "processing_time": result.processing_stats.total_time,
                        "output_format": "json"
                    }
                )
                
                logger.info(f"Audio processing successful (JSON): {task_id}")
                return response
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio processing failed: {str(e)}"
            )
        
        finally:
            # Keep files for now (can implement cleanup later)
            pass
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/download/{task_id}")
async def download_markdown(task_id: str):
    """
    Download Markdown meeting minutes file.
    
    Args:
        task_id: Task ID returned from /transcribe endpoint
        
    Returns:
        FileResponse with Markdown file
        
    Raises:
        404: If task_id not found or Markdown file doesn't exist
    """
    try:
        # Search for Markdown file in default directory
        base_dir = AUDIO_STORAGE_PATH / task_id
        
        if not base_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Task not found: {task_id}"
            )
        
        # Find Markdown file
        md_files = list(base_dir.glob("*_minutes.md"))
        
        if not md_files:
            raise HTTPException(
                status_code=404,
                detail=f"Markdown file not found for task: {task_id}"
            )
        
        md_path = md_files[0]
        
        # Use original filename if available, otherwise use timestamp
        filename = md_path.stem.replace("_minutes", "")
        download_filename = f"{filename}_会议纪要.md"
        
        logger.info(f"Downloading Markdown file: {md_path.name} as {download_filename}")
        
        # Return file response
        return FileResponse(
            path=md_path,
            filename=download_filename,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"',
                "Cache-Control": "no-cache"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/health")
async def audio_health():
    """
    Check audio service health.
    
    Returns:
        Health status and service availability
    """
    return {
        "status": "healthy" if audio_pipeline is not None else "unavailable",
        "service": "audio_transcription",
        "models": {
            "asr": "qwen3-asr-flash",
            "llm": "qwen-plus-latest"
        },
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "async_threshold_seconds": ASYNC_THRESHOLD_SECONDS
    }
