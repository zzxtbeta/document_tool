"""Paraformer long audio transcription service.

Integrates DashScope paraformer-v2 async submission and polling for long audio files.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from dashscope.audio.asr import Transcription
from http import HTTPStatus
import httpx

logger = logging.getLogger(__name__)


class ParaformerLongAudioService:
    """Wrapper around DashScope paraformer async transcription API."""

    DEFAULT_MODEL = "paraformer-v2"
    SUPPORTED_MODELS = {"paraformer-v2", "paraformer-8k-v2"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        storage_dir: Optional[str] = None,
        poll_interval: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY is required for paraformer service")

        storage_root = storage_dir or os.getenv("LONG_AUDIO_STORAGE_DIR") or os.getenv("LONG_AUDIO_STORAGE") or "uploads/audios/long"
        self.storage_dir = Path(storage_root)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.poll_interval = int(poll_interval or os.getenv("LONG_AUDIO_POLL_INTERVAL", "10"))
        self.timeout_seconds = int(os.getenv("LONG_AUDIO_TIMEOUT", str(4 * 3600)))  # default 4h

    def submit(
        self,
        file_urls: List[str],
        model: str = DEFAULT_MODEL,
        language_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Submit long audio transcription task to DashScope."""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model}")

        if len(file_urls) == 0 or len(file_urls) > 100:
            raise ValueError("file_urls must contain 1-100 entries")

        payload: Dict[str, Any] = {
            "model": model,
            "file_urls": file_urls,
        }

        if language_hints and model == "paraformer-v2":
            payload["language_hints"] = language_hints

        logger.info("Submitting paraformer task: model=%s urls=%d", model, len(file_urls))
        response = Transcription.async_call(**payload)

        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope submission failed: {response.message}")

        output = response.output
        safe = self._safe_dashscope_attr
        dashscope_task_id = safe(output, "task_id")
        now_token = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{now_token}_long_{dashscope_task_id}"
        task_dir = self.storage_dir / folder_name
        task_dir.mkdir(parents=True, exist_ok=True)

        submission = {
            "task_id": dashscope_task_id,
            "task_status": safe(output, "task_status", default="PENDING"),
            "submit_time": safe(output, "submit_time"),
            "scheduled_time": safe(output, "scheduled_time"),
            "task_metrics": safe(output, "task_metrics"),
            "local_dir": str(task_dir),
        }

        return submission

    def fetch(self, dashscope_task_id: str) -> Dict[str, Any]:
        """Fetch latest status from DashScope."""
        response = Transcription.fetch(task=dashscope_task_id)

        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope fetch failed: {response.message}")

        output = response.output
        safe = self._safe_dashscope_attr
        data = {
            "task_id": safe(output, "task_id"),
            "task_status": safe(output, "task_status", default="PENDING"),
            "submit_time": safe(output, "submit_time"),
            "scheduled_time": safe(output, "scheduled_time"),
            "end_time": safe(output, "end_time"),
            "task_metrics": safe(output, "task_metrics"),
            "results": safe(output, "results"),
        }

        return data

    def cache_transcriptions(self, task_dir: Path, results: List[Dict[str, Any]]) -> List[str]:
        """Download/Cache transcription JSON metadata locally."""
        if isinstance(task_dir, str):
            task_dir = Path(task_dir)
        task_dir.mkdir(parents=True, exist_ok=True)
        cached_paths: List[str] = []

        for idx, result in enumerate(results or []):
            transcription_url = result.get("transcription_url")
            if not transcription_url:
                continue

            filename = f"result_{idx}.json"
            output_path = task_dir / filename

             # Skip if already downloaded
            if output_path.exists():
                cached_paths.append(str(output_path))
                continue

            try:
                with httpx.stream("GET", transcription_url, timeout=60.0) as resp:
                    resp.raise_for_status()
                    with output_path.open("wb") as fh:
                        for chunk in resp.iter_bytes():
                            fh.write(chunk)
                cached_paths.append(str(output_path))
                logger.info("Cached transcription JSON: %s", output_path)
            except Exception as exc:
                logger.warning("Failed to cache transcription from %s: %s", transcription_url, exc)

        return cached_paths

    def download_audio(self, task_dir: Path, file_urls: List[str]) -> List[str]:
        """Download source audio files locally."""
        if isinstance(task_dir, str):
            task_dir = Path(task_dir)
        task_dir.mkdir(parents=True, exist_ok=True)
        local_paths: List[str] = []
        for idx, url in enumerate(file_urls or []):
            suffix = Path(url.split("?", 1)[0]).suffix or ".bin"
            filename = f"audio_{idx}{suffix}"
            output_path = task_dir / filename
            if output_path.exists():
                local_paths.append(str(output_path))
                continue
            try:
                with httpx.stream("GET", url, timeout=120.0) as resp:
                    resp.raise_for_status()
                    with output_path.open("wb") as fh:
                        for chunk in resp.iter_bytes():
                            fh.write(chunk)
                local_paths.append(str(output_path))
                logger.info("Cached source audio: %s", output_path)
            except Exception as exc:
                logger.warning("Failed to download audio %s: %s", url, exc)
        return local_paths

    @staticmethod
    def _safe_dashscope_attr(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely fetch attribute from DashScope response output."""
        try:
            return getattr(obj, attr)
        except KeyError:
            return default
        except AttributeError:
            return default
