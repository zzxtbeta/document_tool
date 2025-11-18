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
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi import Query

from api.audio_models import (
    AudioTranscriptionResponse,
    AudioTranscriptionMarkdownResponse,
    AudioTranscriptionOptions,
    AsyncTaskResponse,
    LongAudioTranscriptionRequest,
    LongAudioSubmissionResponse,
    LongAudioTaskInfo,
    LongAudioStatusResponse,
    LongAudioStatusData,
    DashScopeTaskFetchResponse,
    DashScopeTaskListResponse,
    DashScopeTaskCancelResponse,
)
from pipelines.audio_pipeline import AudioPipeline
from pipelines.paraformer_long_audio import ParaformerLongAudioService
from pipelines.meeting_minutes_service import MeetingMinutesService
import httpx
from psycopg.rows import dict_row
from psycopg.types.json import Json

from db.database import DatabaseManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/audio", tags=["audio"])

# Initialize pipeline
try:
    audio_pipeline = AudioPipeline()
except Exception as e:
    logger.error(f"Failed to initialize AudioPipeline: {e}")
    audio_pipeline = None

try:
    paraformer_service = ParaformerLongAudioService()
except Exception as e:
    logger.error(f"Failed to initialize Paraformer service: {e}")
    paraformer_service = None

try:
    meeting_minutes_service = MeetingMinutesService()
except Exception as e:
    logger.error(f"Failed to initialize MeetingMinutesService: {e}")
    meeting_minutes_service = None


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

LONG_AUDIO_ALLOWED_SCHEMES = {"http", "https", "oss"}
_long_storage_env = os.getenv("LONG_AUDIO_STORAGE_DIR") or os.getenv("LONG_AUDIO_STORAGE")
LONG_AUDIO_RESULTS_DIR = Path(_long_storage_env or (AUDIO_STORAGE_PATH / "long"))
LONG_AUDIO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LONG_AUDIO_RESULT_TTL = int(os.getenv("LONG_AUDIO_RESULT_TTL", str(24 * 3600)))  # seconds
DASHSCOPE_TASK_API_BASE = os.getenv("DASHSCOPE_TASK_API_BASE", "https://dashscope.aliyuncs.com/api/v1/tasks")
DASHSCOPE_HTTP_TIMEOUT = float(os.getenv("DASHSCOPE_HTTP_TIMEOUT", "30"))

PARAFORMER_FINAL_STATUSES = {"SUCCEEDED", "FAILED"}
LONG_AUDIO_TASKS_TABLE = os.getenv("LONG_AUDIO_TASKS_TABLE", "long_audio_tasks")
_long_audio_table_ready = False
_long_audio_table_lock = asyncio.Lock()


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


def save_uploaded_file(upload_file: UploadFile, task_id: str, output_dir: str = None, kind: str = "short") -> Path:
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
        task_dir = base_dir / task_id
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dir_name = f"{timestamp}_{kind}_{task_id}"
        base_dir = SHORT_AUDIO_STORAGE_PATH if kind == "short" else AUDIO_STORAGE_PATH / kind
        base_dir.mkdir(parents=True, exist_ok=True)
        task_dir = base_dir / dir_name
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension
    filename = upload_file.filename or "audio"
    ext = Path(filename).suffix or ".m4a"
    
    # Save file
    file_path = task_dir / f"audio_original{ext}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    
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


def _persist_short_result(storage_dir: Path, result: Any) -> Path:
    """Save short-audio processing result as JSON for auditing."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    json_path = storage_dir / "result.json"
    try:
        payload = result.model_dump()
    except AttributeError:
        try:
            payload = json.loads(result.json())
        except Exception:
            payload = getattr(result, "__dict__", {})
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return json_path


def _get_dashscope_api_key() -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        return api_key
    raise HTTPException(status_code=503, detail="DASHSCOPE_API_KEY is not configured")


def _format_dashscope_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


async def _dashscope_task_request(
    method: str,
    path: str = "",
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    api_key = _get_dashscope_api_key()
    url = f"{DASHSCOPE_TASK_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=DASHSCOPE_HTTP_TIMEOUT) as client:
            resp = await client.request(method, url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        logger.error("DashScope task request failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"DashScope request error: {exc}") from exc

    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    if resp.status_code >= 400:
        detail = payload.get("message") or payload.get("error") or resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    return payload


async def _ensure_long_audio_table():
    global _long_audio_table_ready
    if _long_audio_table_ready:
        return
    async with _long_audio_table_lock:
        if _long_audio_table_ready:
            return
        pool = await DatabaseManager.get_pool()
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {LONG_AUDIO_TASKS_TABLE} (
            task_id TEXT PRIMARY KEY,
            dashscope_task_id TEXT NOT NULL,
            task_status TEXT NOT NULL,
            model TEXT NOT NULL,
            file_urls TEXT[] NOT NULL,
            language_hints TEXT[],
            results JSONB,
            local_result_paths TEXT[],
            local_audio_paths TEXT[],
            local_dir TEXT,
            remote_result_ttl_seconds INTEGER,
            remote_result_expires_at TIMESTAMPTZ,
            last_fetch_at TIMESTAMPTZ,
            submitted_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            error JSONB,
            transcription_text TEXT,
            meeting_minutes JSONB,
            minutes_markdown_path TEXT,
            minutes_generated_at TIMESTAMPTZ,
            minutes_error TEXT
        )
        """
        create_idx_status = f"CREATE INDEX IF NOT EXISTS idx_{LONG_AUDIO_TASKS_TABLE}_status ON {LONG_AUDIO_TASKS_TABLE}(task_status)"
        create_idx_dashscope = f"CREATE INDEX IF NOT EXISTS idx_{LONG_AUDIO_TASKS_TABLE}_dashscope ON {LONG_AUDIO_TASKS_TABLE}(dashscope_task_id)"
        create_idx_submitted = f"CREATE INDEX IF NOT EXISTS idx_{LONG_AUDIO_TASKS_TABLE}_submitted_at ON {LONG_AUDIO_TASKS_TABLE}(submitted_at DESC)"
        alter_columns = [
            "transcription_text TEXT",
            "meeting_minutes JSONB",
            "minutes_markdown_path TEXT",
            "minutes_generated_at TIMESTAMPTZ",
            "minutes_error TEXT"
        ]
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(create_table_sql)
                await cur.execute(create_idx_status)
                await cur.execute(create_idx_dashscope)
                await cur.execute(create_idx_submitted)
                for col in alter_columns:
                    await cur.execute(f"ALTER TABLE {LONG_AUDIO_TASKS_TABLE} ADD COLUMN IF NOT EXISTS {col}")
        _long_audio_table_ready = True


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _row_to_long_audio_record(row: Dict[str, Any]) -> Dict[str, Any]:
    def _iso(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if isinstance(dt, datetime) else None

    return {
        "task_id": row.get("task_id"),
        "dashscope_task_id": row.get("dashscope_task_id"),
        "task_status": row.get("task_status"),
        "model": row.get("model"),
        "file_urls": row.get("file_urls") or [],
        "language_hints": row.get("language_hints") or None,
        "submitted_at": _iso(row.get("submitted_at")),
        "updated_at": _iso(row.get("updated_at")),
        "results": row.get("results"),
        "local_result_paths": row.get("local_result_paths"),
        "local_audio_paths": row.get("local_audio_paths"),
        "local_dir": row.get("local_dir"),
        "remote_result_ttl_seconds": row.get("remote_result_ttl_seconds"),
        "remote_result_expires_at": _iso(row.get("remote_result_expires_at")),
        "last_fetch_at": _iso(row.get("last_fetch_at")),
        "error": row.get("error"),
        "transcription_text": row.get("transcription_text"),
        "meeting_minutes": row.get("meeting_minutes"),
        "minutes_markdown_path": row.get("minutes_markdown_path"),
        "minutes_generated_at": _iso(row.get("minutes_generated_at")),
        "minutes_error": row.get("minutes_error"),
    }


def _record_to_db_params(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": record["task_id"],
        "dashscope_task_id": record["dashscope_task_id"],
        "task_status": record["task_status"],
        "model": record["model"],
        "file_urls": record.get("file_urls") or [],
        "language_hints": record.get("language_hints"),
        "results": Json(record.get("results")) if record.get("results") is not None else None,
        "local_result_paths": record.get("local_result_paths"),
        "local_audio_paths": record.get("local_audio_paths"),
        "local_dir": record.get("local_dir"),
        "remote_result_ttl_seconds": record.get("remote_result_ttl_seconds"),
        "remote_result_expires_at": _parse_iso_datetime(record.get("remote_result_expires_at")),
        "last_fetch_at": _parse_iso_datetime(record.get("last_fetch_at")),
        "submitted_at": _parse_iso_datetime(record.get("submitted_at")),
        "updated_at": _parse_iso_datetime(record.get("updated_at")),
        "error": Json(record.get("error")) if record.get("error") is not None else None,
        "transcription_text": record.get("transcription_text"),
        "meeting_minutes": Json(record.get("meeting_minutes")) if record.get("meeting_minutes") is not None else None,
        "minutes_markdown_path": record.get("minutes_markdown_path"),
        "minutes_generated_at": _parse_iso_datetime(record.get("minutes_generated_at")),
        "minutes_error": record.get("minutes_error"),
    }


async def _get_long_audio_task(task_id: str) -> Optional[Dict[str, Any]]:
    await _ensure_long_audio_table()
    pool = await DatabaseManager.get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    f"SELECT * FROM {LONG_AUDIO_TASKS_TABLE} WHERE task_id = %s",
                    (task_id,),
                )
                row = await cur.fetchone()
    except Exception as exc:
        logger.error("Failed to load long audio task %s: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load task status") from exc

    if not row:
        return None
    return _row_to_long_audio_record(row)


async def _upsert_long_audio_task(record: Dict[str, Any]):
    await _ensure_long_audio_table()
    pool = await DatabaseManager.get_pool()
    params = _record_to_db_params(record)
    columns = [
        "task_id",
        "dashscope_task_id",
        "task_status",
        "model",
        "file_urls",
        "language_hints",
        "results",
        "local_result_paths",
        "local_audio_paths",
        "local_dir",
        "remote_result_ttl_seconds",
        "remote_result_expires_at",
        "last_fetch_at",
        "submitted_at",
        "updated_at",
        "error",
        "transcription_text",
        "meeting_minutes",
        "minutes_markdown_path",
        "minutes_generated_at",
        "minutes_error",
    ]
    placeholders = ", ".join(["%s"] * len(columns))
    update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns[1:]])
    query = f"""
        INSERT INTO {LONG_AUDIO_TASKS_TABLE} ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT (task_id) DO UPDATE SET {update_clause}
    """
    values = [params[col] for col in columns]
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, values)
    except Exception as exc:
        logger.error("Failed to persist long audio task %s: %s", record.get("task_id"), exc)
        raise HTTPException(status_code=500, detail="Failed to persist task state") from exc


async def _store_long_audio_task(task_id: str, data: Dict[str, Any]):
    await _upsert_long_audio_task(data)


async def _update_long_audio_task(task_id: str, data: Dict[str, Any]):
    await _upsert_long_audio_task(data)


def _validate_long_audio_urls(urls: List[str]):
    for url in urls:
        scheme = url.split(":", 1)[0].lower()
        if scheme not in LONG_AUDIO_ALLOWED_SCHEMES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported URL scheme '{scheme}'. Only HTTP/HTTPS/OSS are allowed."
            )


def _build_status_data(record: Dict[str, Any]) -> LongAudioStatusData:
    return LongAudioStatusData(
        task_id=record["task_id"],
        dashscope_task_id=record["dashscope_task_id"],
        task_status=record["task_status"],
        model=record["model"],
        file_urls=record["file_urls"],
        language_hints=record.get("language_hints"),
        submitted_at=record["submitted_at"],
        updated_at=record["updated_at"],
        results=record.get("results"),
        local_result_paths=record.get("local_result_paths"),
        local_audio_paths=record.get("local_audio_paths"),
        local_dir=record.get("local_dir"),
        remote_result_ttl_seconds=record.get("remote_result_ttl_seconds"),
        remote_result_expires_at=record.get("remote_result_expires_at"),
        error=record.get("error"),
        transcription_text=record.get("transcription_text"),
        meeting_minutes=record.get("meeting_minutes"),
        minutes_markdown_path=record.get("minutes_markdown_path"),
        minutes_generated_at=record.get("minutes_generated_at"),
        minutes_error=record.get("minutes_error"),
    )


def _extract_transcription_text(results: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    if not results:
        return None
    fragments: List[str] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        transcripts = result.get("transcripts")
        if isinstance(transcripts, list):
            for entry in transcripts:
                if isinstance(entry, dict):
                    text = entry.get("text")
                    if text:
                        fragments.append(text.strip())
        text = result.get("transcript") or result.get("text")
        if text:
            fragments.append(str(text).strip())
    combined = "\n\n".join(filter(None, fragments)).strip()
    return combined or None


def _load_transcription_from_cached_results(paths: Optional[List[str]]) -> Optional[str]:
    if not paths:
        return None
    for path_str in paths:
        if not path_str:
            continue
        try:
            path = Path(path_str)
        except TypeError:
            continue
        if not path.exists():
            logger.warning("Cached transcription missing: %s", path)
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to parse cached transcription %s: %s", path, exc)
            continue
        text = _extract_transcription_text([payload])
        if text:
            return text
    return None


async def _maybe_generate_meeting_minutes(record: Dict[str, Any]) -> Dict[str, Any]:
    if meeting_minutes_service is None:
        return record
    if record.get("meeting_minutes"):
        return record
    if record.get("minutes_error"):
        return record
    transcription_text = record.get("transcription_text")
    if not transcription_text:
        if not record.get("local_result_paths") and record.get("results") and paraformer_service is not None:
            task_dir = Path(record.get("local_dir") or LONG_AUDIO_RESULTS_DIR / record["dashscope_task_id"])
            task_dir.mkdir(parents=True, exist_ok=True)
            record["local_dir"] = str(task_dir)
            record["local_result_paths"] = paraformer_service.cache_transcriptions(task_dir, record.get("results"))
        transcription_text = _load_transcription_from_cached_results(record.get("local_result_paths"))
        if transcription_text:
            record["transcription_text"] = transcription_text
    if not transcription_text:
        return record
    try:
        minutes = meeting_minutes_service.generate_minutes(transcription_text)
        record["meeting_minutes"] = minutes.model_dump(mode="json")
        record["minutes_generated_at"] = datetime.now(timezone.utc).isoformat()
        task_dir = Path(record.get("local_dir") or LONG_AUDIO_RESULTS_DIR / record["dashscope_task_id"])
        task_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = task_dir / "meeting_minutes.md"
        meeting_minutes_service.save_as_markdown(minutes, markdown_path, transcript=transcription_text)
        record["minutes_markdown_path"] = str(markdown_path)
        record["minutes_error"] = None
    except Exception as exc:
        logger.error("Meeting minutes generation failed for %s: %s", record.get("task_id"), exc)
        record["minutes_error"] = str(exc)
    return record


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
                        "output_format": "markdown",
                        "local_dir": str(storage_dir),
                        "local_audio_path": str(file_path),
                        "local_markdown_path": str(md_path),
                        "local_result_json": str(result_json_path) if result_json_path else None
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


@router.post("/transcribe-long", response_model=LongAudioSubmissionResponse)
async def submit_long_audio_transcription(request: LongAudioTranscriptionRequest):
    """Submit long audio transcription task using paraformer."""
    if paraformer_service is None:
        raise HTTPException(
            status_code=503,
            detail="Paraformer service is not available. Check DASHSCOPE_API_KEY."
        )

    file_urls = [str(url) for url in request.file_urls]
    _validate_long_audio_urls(file_urls)

    if request.model == "paraformer-8k-v2" and request.language_hints:
        raise HTTPException(
            status_code=400,
            detail="language_hints is only supported by paraformer-v2"
        )

    try:
        submission = paraformer_service.submit(
            file_urls=file_urls,
            model=request.model,
            language_hints=request.language_hints,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("Paraformer submission failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "task_id": task_id,
        "dashscope_task_id": submission["task_id"],
        "task_status": submission["task_status"],
        "model": request.model,
        "file_urls": file_urls,
        "language_hints": request.language_hints,
        "submitted_at": now,
        "updated_at": now,
        "results": None,
        "local_result_paths": None,
        "local_audio_paths": None,
        "local_dir": submission.get("local_dir"),
        "remote_result_ttl_seconds": LONG_AUDIO_RESULT_TTL,
        "remote_result_expires_at": None,
        "last_fetch_at": None,
        "error": None,
    }
    await _store_long_audio_task(task_id, record)

    response = LongAudioSubmissionResponse(
        success=True,
        data=LongAudioTaskInfo(
            task_id=task_id,
            dashscope_task_id=submission["task_id"],
            task_status=submission["task_status"],
            model=request.model,
        ),
        metadata={
            "timestamp": now,
        }
    )

    return response


@router.get("/transcribe-long/{task_id}", response_model=LongAudioStatusResponse)
async def get_long_audio_status(task_id: str):
    """Fetch long audio transcription status (polls DashScope when needed)."""
    if paraformer_service is None:
        raise HTTPException(
            status_code=503,
            detail="Paraformer service is not available. Check DASHSCOPE_API_KEY."
        )

    record = await _get_long_audio_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    now_dt = datetime.now(timezone.utc)
    poll_interval = getattr(paraformer_service, "poll_interval", 10)
    should_fetch = record["task_status"] not in PARAFORMER_FINAL_STATUSES
    last_fetch_iso = record.get("last_fetch_at")
    last_fetch_dt: Optional[datetime] = None
    if last_fetch_iso:
        try:
            last_fetch_dt = datetime.fromisoformat(last_fetch_iso)
        except ValueError:
            last_fetch_dt = None

    try:
        if should_fetch:
            throttle_seconds = (now_dt - last_fetch_dt).total_seconds() if last_fetch_dt else None
            if throttle_seconds is None or throttle_seconds >= poll_interval:
                dashscope_data = paraformer_service.fetch(record["dashscope_task_id"])
                record["last_fetch_at"] = now_dt.isoformat()
                record["task_status"] = dashscope_data["task_status"]
                record["results"] = dashscope_data.get("results")
                record["updated_at"] = datetime.now(timezone.utc).isoformat()

                if record["task_status"] == "SUCCEEDED" and record["results"]:
                    task_dir = Path(record.get("local_dir") or LONG_AUDIO_RESULTS_DIR / record["dashscope_task_id"])
                    task_dir.mkdir(parents=True, exist_ok=True)
                    record["local_dir"] = str(task_dir)
                    record["local_result_paths"] = paraformer_service.cache_transcriptions(task_dir, record["results"])
                    record["local_audio_paths"] = paraformer_service.download_audio(task_dir, record["file_urls"])
                    ttl_seconds = record.get("remote_result_ttl_seconds") or LONG_AUDIO_RESULT_TTL
                    record["remote_result_ttl_seconds"] = ttl_seconds
                    record["remote_result_expires_at"] = (now_dt + timedelta(seconds=ttl_seconds)).isoformat()
                    if not record.get("transcription_text"):
                        record["transcription_text"] = _extract_transcription_text(record["results"])
                elif record["task_status"] == "FAILED":
                    record["error"] = dashscope_data

                await _update_long_audio_task(task_id, record)
    except RuntimeError as exc:
        logger.error("Paraformer fetch failed for %s: %s", task_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if record["task_status"] == "SUCCEEDED":
        record = await _maybe_generate_meeting_minutes(record)
        await _update_long_audio_task(task_id, record)

    expires_at_iso = record.get("remote_result_expires_at")
    remote_result_expired = False
    if expires_at_iso:
        try:
            expires_dt = _parse_iso_datetime(expires_at_iso)
            if expires_dt is not None and expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if expires_dt is not None:
                remote_result_expired = now_dt >= expires_dt
        except ValueError:
            remote_result_expired = False

    return LongAudioStatusResponse(
        success=True,
        data=_build_status_data(record),
        metadata={
            "timestamp": now_dt.isoformat(),
            "poll_interval_seconds": poll_interval,
            "remote_result_ttl_seconds": record.get("remote_result_ttl_seconds"),
            "remote_result_expires_at": expires_at_iso,
            "remote_result_expired": remote_result_expired,
            "meeting_minutes_ready": bool(record.get("meeting_minutes")),
            "minutes_markdown_path": record.get("minutes_markdown_path"),
            "minutes_error": record.get("minutes_error"),
        }
    )


@router.get("/dashscope/tasks/{dashscope_task_id}", response_model=DashScopeTaskFetchResponse)
async def fetch_dashscope_task(dashscope_task_id: str):
    """Proxy DashScope single task fetch."""
    data = await _dashscope_task_request("GET", f"/{dashscope_task_id}")
    return DashScopeTaskFetchResponse(
        success=True,
        data=data,
        metadata={
            "dashscope_task_id": dashscope_task_id,
        },
    )


@router.get("/dashscope/tasks", response_model=DashScopeTaskListResponse)
async def list_dashscope_tasks(
    task_id: Optional[str] = Query(None, description="Optional DashScope task_id for direct lookup"),
    start_time: Optional[str] = Query(None, description="Start time YYYYMMDDhhmmss"),
    end_time: Optional[str] = Query(None, description="End time YYYYMMDDhhmmss"),
    model_name: Optional[str] = Query(None, description="DashScope model name"),
    status: Optional[str] = Query(None, description="Task status filter"),
    page_no: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    params: Dict[str, Any] = {
        "page_no": page_no,
        "page_size": page_size,
    }

    if task_id:
        params["task_id"] = task_id

    now = datetime.utcnow()
    if not task_id:
        if not end_time:
            end_time = _format_dashscope_timestamp(now)
        if not start_time:
            start_time = _format_dashscope_timestamp(now - timedelta(hours=24))

    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if model_name:
        params["model_name"] = model_name
    if status:
        params["status"] = status

    data = await _dashscope_task_request("GET", params=params)
    return DashScopeTaskListResponse(
        success=True,
        data=data,
        metadata={
            "task_id": task_id,
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
            "page_no": page_no,
            "page_size": page_size,
        },
    )


@router.post("/dashscope/tasks/{dashscope_task_id}/cancel", response_model=DashScopeTaskCancelResponse)
async def cancel_dashscope_task(dashscope_task_id: str):
    """Proxy DashScope cancel task endpoint."""
    data = await _dashscope_task_request("POST", f"/{dashscope_task_id}/cancel")
    return DashScopeTaskCancelResponse(
        success=True,
        data=data,
        metadata={
            "dashscope_task_id": dashscope_task_id,
        },
    )


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
        base_dir = _resolve_short_task_dir(task_id)
        
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
