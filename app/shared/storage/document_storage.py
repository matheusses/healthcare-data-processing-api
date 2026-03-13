"""Document storage client (S3/MinIO) for file uploads."""

from __future__ import annotations

import io
import logging
from uuid import UUID

from app.config import Settings

logger = logging.getLogger(__name__)


class DocumentStorageClient:
    """S3-compatible (MinIO) client for storing note files. Bucket created on first use."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.document_storage_endpoint
        self._bucket = settings.document_storage_bucket
        self._access_key = settings.document_storage_access_key
        self._secret_key = settings.document_storage_secret_key
        self._secure = settings.document_storage_secure
        self._client = None

    def _get_client(self):
        if self._client is None:
            from minio import Minio

            # Strip protocol from endpoint for Minio()
            endpoint = self._endpoint.replace("https://", "").replace("http://", "")
            self._client = Minio(
                endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
        return self._client

    def _ensure_bucket(self) -> None:
        client = self._get_client()
        if not client.bucket_exists(self._bucket):
            client.make_bucket(self._bucket)
            logger.info("Created bucket %s", self._bucket)

    def upload_note_content(
        self,
        patient_id: UUID,
        note_id: UUID,
        content: str,
        content_type: str = "text/plain",
    ) -> str:
        """Upload note content as object; return storage key (object name)."""
        self._ensure_bucket()
        key = f"patients/{patient_id}/notes/{note_id}.txt"
        data = io.BytesIO(content.encode("utf-8"))
        client = self._get_client()
        client.put_object(
            self._bucket,
            key,
            data,
            length=len(content.encode("utf-8")),
            content_type=content_type,
        )
        return key

    def delete_object(self, storage_key: str) -> None:
        """Remove object by storage key."""
        client = self._get_client()
        try:
            client.remove_object(self._bucket, storage_key)
        except Exception as e:
            logger.warning("Failed to delete object %s: %s", storage_key, e)
