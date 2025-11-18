"""
Long Audio API Routes

FastAPI routes for long-audio transcription using DashScope paraformer.
Supports asynchronous processing, OSS storage, and meeting minutes generation.

Author: AI Assistant
Date: 2025-11-18
"""

import os
import re
import uuid
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row
from psycopg.types.json import Json

from api.audio.long.models import (
    LongAudioTranscriptionRequest,
    LongAudioSubmissionResponse,
    LongAudioTaskInfo,
    LongAudioStatusResponse,
    LongAudioStatusData,
    LongAudioTaskListResponse,
    DashScopeTaskFetchResponse,
    DashScopeTaskListResponse,
    DashScopeTaskCancelResponse,
)
from api.audio.shared_models import MeetingMinutes
from pipelines.long_audio_pipeline import ParaformerLongAudioService
from pipelines.meeting_minutes_service import MeetingMinutesService
from pipelines.storage import OSSStorageClient
from db.database import DatabaseManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/audio", tags=["long-audio"])

# Initialize services
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

try:
    storage_client = OSSStorageClient()
except Exception as exc:
    logger.warning("OSS storage disabled: %s", exc)
    storage_client = None


# =============================================================================
# CONFIGURATION
# =============================================================================

LONG_AUDIO_ALLOWED_SCHEMES = {"http", "https", "oss"}
_long_storage_env = os.getenv("LONG_AUDIO_STORAGE_DIR") or os.getenv("LONG_AUDIO_STORAGE")
LONG_AUDIO_RESULTS_DIR = Path(_long_storage_env or "uploads/audios/long")
LONG_AUDIO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LONG_AUDIO_RESULT_TTL = int(os.getenv("LONG_AUDIO_RESULT_TTL", str(24 * 3600)))
DASHSCOPE_TASK_API_BASE = os.getenv("DASHSCOPE_TASK_API_BASE", "https://dashscope.aliyuncs.com/api/v1/tasks")
DASHSCOPE_HTTP_TIMEOUT = float(os.getenv("DASHSCOPE_HTTP_TIMEOUT", "30"))
DEFAULT_AUDIO_USER_ID = os.getenv("DEFAULT_AUDIO_USER_ID", "admin123")
DEFAULT_AUDIO_PROJECT_ID = os.getenv("DEFAULT_AUDIO_PROJECT_ID", "defaultProject")
OSS_SIGNED_URL_TTL = int(os.getenv("OSS_SIGNED_URL_TTL", "600"))

PARAFORMER_FINAL_STATUSES = {"SUCCEEDED", "FAILED"}
LONG_AUDIO_TASKS_TABLE = os.getenv("LONG_AUDIO_TASKS_TABLE", "long_audio_tasks")
_long_audio_table_ready = False
_long_audio_table_lock = asyncio.Lock()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
            remote_result_urls TEXT[],
            remote_result_object_keys TEXT[],
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
            minutes_markdown_url TEXT,
            minutes_markdown_object_key TEXT,
            minutes_generated_at TIMESTAMPTZ,
            minutes_error TEXT,
            user_id TEXT,
            project_id TEXT,
            source_filename TEXT,
            oss_object_prefix TEXT
        )
        """
        create_idx_status = f"CREATE INDEX IF NOT EXISTS idx_{LONG_AUDIO_TASKS_TABLE}_status ON {LONG_AUDIO_TASKS_TABLE}(task_status)"
        create_idx_dashscope = f"CREATE INDEX IF NOT EXISTS idx_{LONG_AUDIO_TASKS_TABLE}_dashscope ON {LONG_AUDIO_TASKS_TABLE}(dashscope_task_id)"
        create_idx_submitted = f"CREATE INDEX IF NOT EXISTS idx_{LONG_AUDIO_TASKS_TABLE}_submitted_at ON {LONG_AUDIO_TASKS_TABLE}(submitted_at DESC)"
        
        alter_columns = [
            "transcription_text TEXT",
            "meeting_minutes JSONB",
            "minutes_markdown_path TEXT",
            "minutes_markdown_url TEXT",
            "minutes_markdown_object_key TEXT",
            "minutes_generated_at TIMESTAMPTZ",
            "minutes_error TEXT",
            "remote_result_urls TEXT[]",
            "remote_result_object_keys TEXT[]",
            "user_id TEXT",
            "project_id TEXT",
            "source_filename TEXT",
            "oss_object_prefix TEXT"
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


def _parse_iso_datetime(value: Optional[str | datetime]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _sanitize_filename_component(name: str, fallback: str) -> str:
    token = re.sub(r"[^\w\-.]+", "_", (name or "").strip())
    token = token.strip("._")
    return token or fallback


def _derive_source_filename(file_urls: List[str]) -> str:
    for url in file_urls:
        try:
            parsed = urlparse(url)
        except Exception:
            continue
        if parsed.path:
            candidate = Path(parsed.path).name
            if candidate:
                return candidate
    return f"audio_{uuid.uuid4().hex[:8]}"


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
        "remote_result_urls": row.get("remote_result_urls"),
        "remote_result_object_keys": row.get("remote_result_object_keys"),
        "local_audio_paths": row.get("local_audio_paths"),
        "local_dir": row.get("local_dir"),
        "remote_result_ttl_seconds": row.get("remote_result_ttl_seconds"),
        "remote_result_expires_at": _iso(row.get("remote_result_expires_at")),
        "last_fetch_at": _iso(row.get("last_fetch_at")),
        "error": row.get("error"),
        "transcription_text": row.get("transcription_text"),
        "meeting_minutes": row.get("meeting_minutes"),
        "minutes_markdown_path": row.get("minutes_markdown_path"),
        "minutes_markdown_url": row.get("minutes_markdown_url"),
        "minutes_markdown_object_key": row.get("minutes_markdown_object_key"),
        "minutes_generated_at": _iso(row.get("minutes_generated_at")),
        "minutes_error": row.get("minutes_error"),
        "user_id": row.get("user_id"),
        "project_id": row.get("project_id"),
        "source_filename": row.get("source_filename"),
        "oss_object_prefix": row.get("oss_object_prefix"),
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
        "remote_result_urls": record.get("remote_result_urls"),
        "remote_result_object_keys": record.get("remote_result_object_keys"),
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
        "minutes_markdown_url": record.get("minutes_markdown_url"),
        "minutes_markdown_object_key": record.get("minutes_markdown_object_key"),
        "minutes_generated_at": _parse_iso_datetime(record.get("minutes_generated_at")),
        "minutes_error": record.get("minutes_error"),
        "user_id": record.get("user_id"),
        "project_id": record.get("project_id"),
        "source_filename": record.get("source_filename"),
        "oss_object_prefix": record.get("oss_object_prefix"),
    }


async def _get_long_audio_task(task_id: str) -> Optional[Dict[str, Any]]:
    await _ensure_long_audio_table()
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"SELECT * FROM {LONG_AUDIO_TASKS_TABLE} WHERE task_id = %s",
                (task_id,)
            )
            row = await cur.fetchone()
    if not row:
        return None
    return _row_to_long_audio_record(row)


async def _get_long_audio_task_by_dashscope_id(dashscope_task_id: str) -> Optional[Dict[str, Any]]:
    """Query long audio task by DashScope task ID."""
    await _ensure_long_audio_table()
    pool = await DatabaseManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"SELECT * FROM {LONG_AUDIO_TASKS_TABLE} WHERE dashscope_task_id = %s",
                (dashscope_task_id,)
            )
            row = await cur.fetchone()
    if not row:
        return None
    return _row_to_long_audio_record(row)


async def _list_long_audio_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[List[Dict[str, Any]], int]:
    """Query local long audio tasks with optional filters."""
    await _ensure_long_audio_table()
    pool = await DatabaseManager.get_pool()
    
    where_clause = ""
    params = []
    if status and status != "ALL":
        where_clause = "WHERE task_status = %s"
        params.append(status)
    
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # Get total count
            count_sql = f"SELECT COUNT(*) as total FROM {LONG_AUDIO_TASKS_TABLE} {where_clause}"
            await cur.execute(count_sql, params)
            count_row = await cur.fetchone()
            total = count_row["total"] if count_row else 0
            
            # Get tasks ordered by submitted_at descending
            query_sql = f"""
                SELECT * FROM {LONG_AUDIO_TASKS_TABLE}
                {where_clause}
                ORDER BY submitted_at DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
            await cur.execute(query_sql, params + [limit, offset])
            rows = await cur.fetchall()
    
    tasks = [_row_to_long_audio_record(row) for row in rows]
    return tasks, total


async def _upsert_long_audio_task(record: Dict[str, Any]):
    await _ensure_long_audio_table()
    params = _record_to_db_params(record)
    pool = await DatabaseManager.get_pool()
    
    columns = list(params.keys())
    placeholders = ", ".join([f"%({col})s" for col in columns])
    updates = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != "task_id"])
    
    upsert_sql = f"""
    INSERT INTO {LONG_AUDIO_TASKS_TABLE} ({", ".join(columns)})
    VALUES ({placeholders})
    ON CONFLICT (task_id) DO UPDATE SET {updates}
    """
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(upsert_sql, params)


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


def _build_status_data(record: Dict[str, Any], minutes_signed_url: Optional[str] = None) -> LongAudioStatusData:
    # Handle error field - convert dict to JSON string if needed
    error_value = record.get("error")
    if isinstance(error_value, dict):
        error_str = json.dumps(error_value, ensure_ascii=False)
    else:
        error_str = error_value
    
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
        remote_result_urls=record.get("remote_result_urls"),
        local_audio_paths=record.get("local_audio_paths"),
        local_dir=record.get("local_dir"),
        remote_result_ttl_seconds=record.get("remote_result_ttl_seconds"),
        remote_result_expires_at=record.get("remote_result_expires_at"),
        error=error_str,
        transcription_text=record.get("transcription_text"),
        meeting_minutes=record.get("meeting_minutes"),
        minutes_markdown_path=record.get("minutes_markdown_path"),
        minutes_markdown_url=record.get("minutes_markdown_url"),
        minutes_generated_at=record.get("minutes_generated_at"),
        minutes_error=record.get("minutes_error"),
        minutes_markdown_signed_url=minutes_signed_url,
        user_id=record.get("user_id"),
        project_id=record.get("project_id"),
        source_filename=record.get("source_filename"),
        oss_object_prefix=record.get("oss_object_prefix"),
    )


def _extract_transcription_text(data: Dict[str, Any]) -> Optional[str]:
    """Extract text from cached DashScope JSON file."""
    if not data or not isinstance(data, dict):
        return None
    
    # DashScope paraformer JSON structure: {"transcripts": [{"text": "...", "sentences": [...]}]}
    transcripts = data.get("transcripts")
    if not isinstance(transcripts, list):
        return None
    
    fragments: List[str] = []
    for transcript_entry in transcripts:
        if isinstance(transcript_entry, dict):
            text = transcript_entry.get("text")
            if text:
                fragments.append(text.strip())
    
    combined = "\n\n".join(filter(None, fragments)).strip()
    return combined or None


def _load_transcription_from_cached_results(paths: Optional[List[str]]) -> Optional[str]:
    """Load transcription text from cached JSON files."""
    if not paths:
        return None
    
    for path_str in paths:
        if not path_str:
            continue
        
        try:
            p = Path(path_str)
            if not p.exists():
                continue
            
            data = json.loads(p.read_text(encoding="utf-8"))
            text = _extract_transcription_text(data)
            if text:
                logger.info("Loaded transcription from %s: %d chars", path_str, len(text))
                return text
        except Exception as exc:
            logger.warning("Failed to load transcription from %s: %s", path_str, exc)
    
    return None


def _maybe_upload_minutes_to_oss(record: Dict[str, Any]) -> Dict[str, Any]:
    if not storage_client:
        return record
    
    md_path = record.get("minutes_markdown_path")
    if not md_path or not Path(md_path).exists():
        return record
    
    if record.get("minutes_markdown_url"):
        return record
    
    try:
        project_id = record.get("project_id") or DEFAULT_AUDIO_PROJECT_ID
        task_id = record.get("task_id")
        source_filename = record.get("source_filename") or "minutes"
        base_name = Path(source_filename).stem
        
        object_key = storage_client.build_object_key(
            "bronze", "userUploads", project_id, "audio", task_id, f"{base_name}_minutes.md"
        )
        
        storage_client.upload_file(Path(md_path), object_key, content_type="text/markdown")
        public_url = storage_client.build_public_url(object_key)
        
        record["minutes_markdown_url"] = public_url
        record["minutes_markdown_object_key"] = object_key
        logger.info("Uploaded minutes to OSS: %s", object_key)
    except Exception as exc:
        logger.error("Failed to upload minutes to OSS: %s", exc)
        record["minutes_error"] = f"OSS upload failed: {exc}"
    
    return record


def _build_minutes_signed_url(record: Dict[str, Any]) -> Optional[str]:
    if not storage_client:
        return None
    
    object_key = record.get("minutes_markdown_object_key")
    if not object_key:
        return None
    
    try:
        return storage_client.generate_signed_url(object_key, expires=OSS_SIGNED_URL_TTL)
    except Exception as exc:
        logger.warning("Failed to generate signed URL: %s", exc)
        return None


async def _maybe_generate_meeting_minutes(record: Dict[str, Any]) -> Dict[str, Any]:
    if record.get("meeting_minutes"):
        return record
    
    if not meeting_minutes_service:
        record["minutes_error"] = "Meeting minutes service not available"
        return record
    
    # Load transcription from cached JSON files (DashScope API doesn't return full text)
    transcription = record.get("transcription_text")
    if not transcription and record.get("local_result_paths"):
        transcription = _load_transcription_from_cached_results(record.get("local_result_paths"))
        if transcription:
            record["transcription_text"] = transcription
    
    if not transcription:
        record["minutes_error"] = "No transcription available"
        logger.warning("No transcription found for task %s (cached_files=%s)", 
                      record.get("task_id"), 
                      bool(record.get("local_result_paths")))
        return record
    
    try:
        minutes = meeting_minutes_service.generate_minutes(transcription)
        record["meeting_minutes"] = minutes.model_dump(mode="json")
        record["minutes_generated_at"] = datetime.now(timezone.utc).isoformat()
        
        local_dir = Path(record.get("local_dir") or LONG_AUDIO_RESULTS_DIR / record["task_id"])
        local_dir.mkdir(parents=True, exist_ok=True)
        
        source_filename = record.get("source_filename") or "minutes"
        md_filename = f"{Path(source_filename).stem}_minutes.md"
        md_path = local_dir / md_filename
        
        meeting_minutes_service.save_as_markdown(minutes, md_path, transcription)
        record["minutes_markdown_path"] = str(md_path)
        
        record = _maybe_upload_minutes_to_oss(record)
        logger.info("Generated meeting minutes for task %s", record["task_id"])
    except Exception as exc:
        logger.error("Failed to generate meeting minutes: %s", exc)
        record["minutes_error"] = str(exc)
    
    return record


# =============================================================================
# API ENDPOINTS
# =============================================================================

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
    dashscope_task_id = submission["task_id"]
    
    user_id = request.user_id or DEFAULT_AUDIO_USER_ID
    project_id = request.project_id or DEFAULT_AUDIO_PROJECT_ID
    source_filename = request.source_filename or _derive_source_filename(file_urls)
    
    oss_object_prefix = None
    if storage_client is not None:
        oss_object_prefix = storage_client.build_audio_prefix(project_id, task_id)
    
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "task_id": task_id,
        "dashscope_task_id": dashscope_task_id,
        "task_status": submission["task_status"],
        "model": request.model,
        "file_urls": file_urls,
        "language_hints": request.language_hints,
        "submitted_at": now,
        "updated_at": now,
        "results": None,
        "local_result_paths": None,
        "remote_result_urls": None,
        "remote_result_object_keys": None,
        "local_audio_paths": None,
        "local_dir": submission.get("local_dir"),
        "remote_result_ttl_seconds": LONG_AUDIO_RESULT_TTL,
        "remote_result_expires_at": None,
        "last_fetch_at": None,
        "error": None,
        "user_id": user_id,
        "project_id": project_id,
        "source_filename": source_filename,
        "oss_object_prefix": oss_object_prefix,
    }
    
    await _store_long_audio_task(task_id, record)
    
    return LongAudioSubmissionResponse(
        success=True,
        data=LongAudioTaskInfo(
            task_id=task_id,
            dashscope_task_id=dashscope_task_id,
            task_status=record["task_status"],
            model=request.model,
        ),
        metadata={
            "timestamp": now,
        }
    )


@router.get("/transcribe-long", response_model=LongAudioTaskListResponse)
async def list_long_audio_tasks(
    status: Optional[str] = Query(None, description="Filter by task status (PENDING/RUNNING/SUCCEEDED/FAILED/ALL)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List local long audio transcription tasks."""
    offset = (page - 1) * page_size
    tasks, total = await _list_long_audio_tasks(status=status, limit=page_size, offset=offset)
    
    # Build status data for each task
    task_data = []
    for record in tasks:
        task_data.append(_build_status_data(record))
    
    return LongAudioTaskListResponse(
        success=True,
        data=task_data,
        metadata={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }
    )


@router.get("/transcribe-long/{task_id}", response_model=LongAudioStatusResponse)
async def get_long_audio_status(task_id: str):
    """Query long audio transcription task status."""
    if paraformer_service is None:
        raise HTTPException(status_code=503, detail="Paraformer service unavailable")
    
    record = await _get_long_audio_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    now_dt = datetime.now(timezone.utc)
    current_status = record.get("task_status")
    poll_interval = getattr(paraformer_service, "poll_interval", 10)
    should_fetch = current_status not in PARAFORMER_FINAL_STATUSES
    
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
                record["updated_at"] = now_dt.isoformat()
                
                if record["task_status"] == "SUCCEEDED" and record["results"]:
                    # Setup task directory
                    task_dir = Path(record.get("local_dir") or LONG_AUDIO_RESULTS_DIR / record["dashscope_task_id"])
                    task_dir.mkdir(parents=True, exist_ok=True)
                    record["local_dir"] = str(task_dir)
                    
                    # Cache transcriptions
                    record["local_result_paths"] = paraformer_service.cache_transcriptions(task_dir, record["results"])
                    
                    # Download audio files
                    record["local_audio_paths"] = paraformer_service.download_audio(task_dir, record["file_urls"])
                    
                    # Upload to OSS if available
                    if storage_client is not None and record.get("local_result_paths"):
                        uploaded_urls: List[str] = []
                        uploaded_keys: List[str] = []
                        base_prefix = record.get("oss_object_prefix")
                        source_filename = record.get("source_filename") or record["dashscope_task_id"]
                        safe_base = _sanitize_filename_component(source_filename, record["dashscope_task_id"])
                        
                        for idx, path_str in enumerate(record["local_result_paths"]):
                            try:
                                path = Path(path_str)
                            except TypeError:
                                continue
                            if not path.exists() or not base_prefix:
                                continue
                            
                            object_key = f"{base_prefix.rstrip('/')}/{safe_base}_result_{idx}.json"
                            try:
                                storage_client.upload_file(path, object_key, content_type="application/json")
                                uploaded_keys.append(object_key)
                                uploaded_urls.append(storage_client.build_public_url(object_key))
                            except Exception as exc:
                                logger.warning("Failed to upload transcription JSON %s: %s", path, exc)
                        
                        if uploaded_urls:
                            record["remote_result_urls"] = uploaded_urls
                            record["remote_result_object_keys"] = uploaded_keys
                    
                    # Set TTL
                    ttl_seconds = record.get("remote_result_ttl_seconds") or LONG_AUDIO_RESULT_TTL
                    record["remote_result_ttl_seconds"] = ttl_seconds
                    record["remote_result_expires_at"] = (now_dt + timedelta(seconds=ttl_seconds)).isoformat()
                    
                    # Extract transcription text from cached JSON files
                    if not record.get("transcription_text") and record.get("local_result_paths"):
                        record["transcription_text"] = _load_transcription_from_cached_results(record["local_result_paths"])
                
                elif record["task_status"] == "FAILED":
                    # Serialize error dict to JSON string for Pydantic validation
                    record["error"] = json.dumps(dashscope_data, ensure_ascii=False) if isinstance(dashscope_data, dict) else str(dashscope_data)
                
                await _update_long_audio_task(task_id, record)
    
    except RuntimeError as exc:
        logger.error("Paraformer fetch failed for %s: %s", task_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    
    # Generate meeting minutes if succeeded
    if record["task_status"] == "SUCCEEDED":
        record = await _maybe_generate_meeting_minutes(record)
        await _update_long_audio_task(task_id, record)
    
    # Build signed URL for minutes
    minutes_signed_url = _build_minutes_signed_url(record)
    if minutes_signed_url:
        record["minutes_markdown_signed_url"] = minutes_signed_url
    
    # Check if remote result expired
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
        data=_build_status_data(record, minutes_signed_url=minutes_signed_url),
        metadata={
            "timestamp": now_dt.isoformat(),
            "poll_interval_seconds": poll_interval,
            "remote_result_ttl_seconds": record.get("remote_result_ttl_seconds"),
            "remote_result_expires_at": expires_at_iso,
            "remote_result_expired": remote_result_expired,
            "meeting_minutes_ready": bool(record.get("meeting_minutes")),
            "minutes_markdown_path": record.get("minutes_markdown_path"),
            "minutes_error": record.get("minutes_error"),
            "minutes_markdown_signed_url": minutes_signed_url,
            "minutes_markdown_url": record.get("minutes_markdown_url"),
        }
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

    now = datetime.now(timezone.utc)
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

    try:
        data = await _dashscope_task_request("GET", params=params)
    except HTTPException as exc:
        if exc.status_code == 404:
            logger.info("DashScope task list returned 404 (no data); responding with empty list")
            data = {
                "total": 0,
                "data": [],
                "page_no": page_no,
                "page_size": page_size,
            }
        else:
            raise
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


@router.post("/dashscope/tasks/{dashscope_task_id}/cancel", response_model=DashScopeTaskCancelResponse)
async def cancel_dashscope_task(dashscope_task_id: str):
    """Cancel a DashScope task (only PENDING tasks can be cancelled).
    
    According to DashScope API docs:
    - Only tasks in PENDING status (queued but not yet processing) can be cancelled
    - Returns 400 UnsupportedOperation for tasks in other statuses
    - Rate limit: 20 QPS per account
    """
    # Check local task status first to avoid unnecessary API calls
    record = await _get_long_audio_task_by_dashscope_id(dashscope_task_id)
    if record:
        current_status = record.get("task_status")
        if current_status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"无法取消任务: 当前状态为 {current_status},仅支持取消排队中(PENDING)的任务"
            )
    
    try:
        data = await _dashscope_task_request("POST", f"/{dashscope_task_id}/cancel")
        return DashScopeTaskCancelResponse(
            success=True,
            data=data,
            metadata={
                "dashscope_task_id": dashscope_task_id,
            },
        )
    except HTTPException as exc:
        # DashScope returns 400 if task is not in PENDING status
        if exc.status_code == 400:
            logger.warning("Cannot cancel task %s: %s", dashscope_task_id, exc.detail)
            raise HTTPException(
                status_code=400,
                detail="无法取消任务: 仅支持取消排队中(PENDING)的任务"
            ) from exc
        raise


@router.get("/health")
async def health_check():
    """Health check endpoint for long-audio service."""
    return {
        "status": "healthy",
        "service": "long-audio",
        "paraformer_available": paraformer_service is not None,
        "meeting_minutes_available": meeting_minutes_service is not None,
        "oss_storage_available": storage_client is not None,
        "result_ttl_seconds": LONG_AUDIO_RESULT_TTL,
        "poll_interval": paraformer_service.poll_interval if paraformer_service else None,
    }
