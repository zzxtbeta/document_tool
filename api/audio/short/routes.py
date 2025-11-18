"""
Short Audio API Routes

FastAPI routes for short-audio upload, transcription, and meeting minutes generation.

Author: AI Assistant
Date: 2025-11-18
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse

from api.audio.short.models import (
    AudioTranscriptionResponse,
    AudioTranscriptionMarkdownResponse,
    AudioTranscriptionOptions,
)
from api.audio.shared_models import AudioMetadata, MeetingMinutes, ProcessingStats
from pipelines.short_audio_pipeline import AudioPipeline

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/audio", tags=["short-audio"])

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
AUDIO_STORAGE_PATH = Path(os.getenv("AUDIO_STORAGE_DIR", "uploads/audios"))
AUDIO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
SHORT_AUDIO_STORAGE_PATH = AUDIO_STORAGE_PATH / "short"
SHORT_AUDIO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def should_process_async(file_size_mb: float) -> bool:
    """Determine if audio should be processed asynchronously based on estimated duration."""
    estimated_duration = file_size_mb * 60  # 1MB ≈ 60 seconds
    return estimated_duration >= ASYNC_THRESHOLD_SECONDS


def save_uploaded_file(upload_file: UploadFile, task_id: str, output_dir: Optional[str] = None) -> Path:
    """Save uploaded audio file to disk."""
    if output_dir:
        custom_dir = Path(output_dir)
        if custom_dir.is_absolute() or ".." in str(custom_dir):
            raise ValueError("output_dir must be a relative path without '..'")
        task_dir = AUDIO_STORAGE_PATH / custom_dir / task_id
    else:
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_dir = SHORT_AUDIO_STORAGE_PATH / f"{now_str}_{task_id}"
    
    task_dir.mkdir(parents=True, exist_ok=True)
    
    filename = upload_file.filename or "audio"
    ext = Path(filename).suffix or ".m4a"
    file_path = task_dir / f"audio_original{ext}"
    
    with open(file_path, "wb") as f:
        upload_file.file.seek(0)
        f.write(upload_file.file.read())
    
    logger.info(f"Saved uploaded file: {file_path}")
    return file_path


def _resolve_short_task_dir(task_id: str) -> Path:
    """Locate the storage directory for a short-audio task."""
    legacy_dir = AUDIO_STORAGE_PATH / task_id
    if legacy_dir.exists():
        return legacy_dir
    
    short_matches = list(SHORT_AUDIO_STORAGE_PATH.glob(f"*_{task_id}"))
    if short_matches:
        return short_matches[0]
    
    matches = list(AUDIO_STORAGE_PATH.glob(f"*_{task_id}"))
    if matches:
        return matches[0]
    
    raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")


def _persist_short_result(storage_dir: Path, result) -> Path:
    """Save short-audio processing result as JSON."""
    import json
    storage_dir.mkdir(parents=True, exist_ok=True)
    json_path = storage_dir / "result.json"
    
    try:
        payload = result.model_dump()
    except AttributeError:
        payload = result.dict() if hasattr(result, "dict") else {"error": "Unable to serialize result"}
    
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return json_path


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/transcribe", response_model=AudioTranscriptionResponse | AudioTranscriptionMarkdownResponse)
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
    - `json` (default): Returns structured JSON
    - `markdown`: Returns Markdown content and download URL
    
    **Parameters:**
    - `file`: Audio file (max 100MB)
    - `output_format`: 'json' or 'markdown'
    - `enable_itn`: Enable inverse text normalization
    - `asr_context`: Specialized terminology context
    - `language`: Audio language code
    """
    if audio_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Audio processing service is not available. Check DASHSCOPE_API_KEY."
        )
    
    if output_format not in ["json", "markdown"]:
        raise HTTPException(status_code=400, detail="output_format must be 'json' or 'markdown'")
    
    task_id = str(uuid.uuid4())
    request_time = datetime.now()
    
    try:
        # Validate file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large. Max: {MAX_FILE_SIZE_MB}MB")
        
        # Validate format
        filename = file.filename or ""
        ext = Path(filename).suffix.lstrip('.').lower()
        supported_formats = ['m4a', 'mp3', 'wav', 'flac', 'opus', 'aac']
        
        if ext not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {ext}. Supported: {', '.join(supported_formats)}"
            )
        
        logger.info(f"Processing audio: {filename} ({file_size_mb:.2f}MB), format: {output_format}")
        
        if should_process_async(file_size_mb):
            logger.warning(f"Large file ({file_size_mb:.2f}MB), async not yet implemented")
        
        # Save file
        try:
            file_path = save_uploaded_file(file, task_id, output_dir)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        storage_dir = file_path.parent
        result_json_path: Optional[Path] = None
        
        # Process audio
        try:
            result = audio_pipeline.process(
                str(file_path),
                enable_itn=enable_itn,
                asr_context=asr_context,
                language=language
            )
            result_json_path = _persist_short_result(storage_dir, result)
            
            if output_format == "markdown":
                md_filename = f"{Path(filename).stem}_minutes.md"
                md_path = file_path.parent / md_filename
                
                audio_pipeline.save_as_markdown(
                    meeting_minutes=result.meeting_minutes,
                    output_path=md_path,
                    transcript=result.transcription_text
                )
                
                markdown_content = md_path.read_text(encoding='utf-8')
                
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
                        "output_format": "markdown",
                        "local_dir": str(storage_dir),
                        "local_audio_path": str(file_path),
                        "local_markdown_path": str(md_path),
                        "local_result_json": str(result_json_path) if result_json_path else None
                    }
                )
                logger.info(f"Audio processing successful (Markdown): {task_id}")
                return response
            
            else:  # json
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
                        "output_format": "json",
                        "local_dir": str(storage_dir),
                        "local_audio_path": str(file_path),
                        "local_result_json": str(result_json_path) if result_json_path else None
                    }
                )
                logger.info(f"Audio processing successful (JSON): {task_id}")
                return response
        
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/download/{task_id}")
async def download_audio_result(task_id: str):
    """Download meeting minutes Markdown file for a task."""
    try:
        task_dir = _resolve_short_task_dir(task_id)
    except HTTPException:
        raise
    
    md_files = list(task_dir.glob("*_minutes.md"))
    if not md_files:
        raise HTTPException(status_code=404, detail="Markdown file not found for this task")
    
    md_path = md_files[0]
    return FileResponse(
        path=str(md_path),
        media_type="text/markdown",
        filename=md_path.name
    )


@router.get("/health")
async def health_check():
    """Health check endpoint for short-audio service."""
    return {
        "status": "healthy",
        "service": "short-audio",
        "pipeline_available": audio_pipeline is not None,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "async_threshold_seconds": ASYNC_THRESHOLD_SECONDS,
        "model": audio_pipeline.asr_model if audio_pipeline else None
    }
