"""Document storage client (S3/MinIO) for file uploads."""

from __future__ import annotations

from datetime import timedelta
import io
import logging

from app.config import settings
from app.shared.interfaces.storage.document_storage import IDocumentStorage
from minio import Minio

logger = logging.getLogger(__name__)


class DocumentStorageClient(IDocumentStorage):
    """S3-compatible (MinIO) client for storing note files. Bucket created on first use."""

    def __init__(self) -> None:
        self._endpoint = settings.DOCUMENT_STORAGE_ENDPOINT
        self._bucket = settings.DOCUMENT_STORAGE_BUCKET
        self._access_key = settings.DOCUMENT_STORAGE_ACCESS_KEY
        self._secret_key = settings.DOCUMENT_STORAGE_SECRET_KEY
        self._secure = settings.DOCUMENT_STORAGE_SECURE
        self._client = Minio(
            self._endpoint.replace("https://", "").replace("http://", ""),
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=self._secure,
        )

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info("Created bucket %s", self._bucket)

    async def upload(
        self,
        path: str,
        raw: bytes,
    ) -> str:
        """Upload file content as object; return storage key (object name)."""
        key = path
        data = io.BytesIO(raw)
        self._ensure_bucket()
        self._client.put_object(
            self._bucket,
            key,
            data,
            length=len(raw),
        )
        return key

    async def generate_pre_signed_url(self, storage_key: str) -> str:
        """Generate a pre-signed URL for a note content object."""
        client = self._client()
        return client.presigned_get_object(self._bucket, storage_key, expires=timedelta(hours=1))

    async def delete(self, storage_key: str) -> None:
        """Remove object by storage key."""
        self._client.remove_object(self._bucket, storage_key)
