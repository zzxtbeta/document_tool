"""Object storage helpers for OSS uploads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    import oss2
except ModuleNotFoundError as exc:
    oss2 = None  # type: ignore[assignment]
    _OSS_IMPORT_ERROR = exc
else:
    _OSS_IMPORT_ERROR = None


class OSSStorageClient:
    """Thin wrapper around Alibaba Cloud OSS for file uploads and signed URLs."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        bucket_name: Optional[str] = None,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        default_prefix: Optional[str] = None,
    ) -> None:
        if oss2 is None:
            raise ImportError(
                "oss2 package is required for OSSStorageClient. Install aliyun-oss2 to enable OSS uploads."
            ) from _OSS_IMPORT_ERROR
        self.endpoint = endpoint or os.getenv("OSS_ENDPOINT")
        self.bucket_name = bucket_name or os.getenv("OSS_BUCKET")
        self.access_key_id = access_key_id or os.getenv("OSS_ACCESS_KEY_ID")
        self.access_key_secret = access_key_secret or os.getenv("OSS_ACCESS_KEY_SECRET")
        self.default_prefix = (default_prefix or os.getenv("OSS_BASE_PREFIX", "/prod")).strip("/")

        if not all([self.endpoint, self.bucket_name, self.access_key_id, self.access_key_secret]):
            raise ValueError("OSS configuration is incomplete. Check endpoint, bucket and credentials.")

        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

        endpoint_host = urlparse(self.endpoint).netloc
        self.public_endpoint = f"https://{self.bucket_name}.{endpoint_host}".rstrip("/")

    def build_object_key(self, *parts: str) -> str:
        """Join path parts into a normalized object key."""
        segments = [self.default_prefix]
        segments.extend(part.strip("/") for part in parts if part)
        return "/".join(filter(None, segments))

    def build_audio_prefix(self, project_id: str, task_id: str) -> str:
        return self.build_object_key("gold", "userUploads", project_id, "audio", task_id)

    def upload_file(self, local_path: Path, object_key: str, content_type: Optional[str] = None) -> None:
        local_path = Path(local_path)
        headers = {"Content-Type": content_type} if content_type else None
        self.bucket.put_object_from_file(object_key, str(local_path), headers=headers)

    def upload_text(self, content: str, object_key: str, content_type: Optional[str] = None) -> None:
        headers = {"Content-Type": content_type} if content_type else None
        self.bucket.put_object(object_key, content.encode("utf-8"), headers=headers)

    def build_public_url(self, object_key: str) -> str:
        key = object_key.lstrip("/")
        return f"{self.public_endpoint}/{key}"

    def generate_signed_url(self, object_key: str, expires: int = 600) -> str:
        key = object_key.lstrip("/")
        return self.bucket.sign_url("GET", key, expires)

    def extract_object_key(self, url: str) -> str:
        """Extract object key from a previously returned URL."""
        if not url:
            return ""
        if url.startswith("oss://"):
            return url.split(self.bucket_name + "/", 1)[-1]
        parsed = urlparse(url)
        if parsed.netloc.endswith(self.bucket_name + "." + urlparse(self.endpoint).netloc.split(".", 1)[-1]):
            return parsed.path.lstrip("/")
        # fallback to treating url as already a key
        return url.lstrip("/")
