"""Document storage client (S3-compatible) for file uploads.

Uses aiobotocore (async botocore) to avoid blocking the event loop.
Spans use semantic-like attributes for storage operations.
"""

from __future__ import annotations

import logging

from aiobotocore.session import get_session
from botocore.config import Config
from botocore.exceptions import ClientError
from opentelemetry import trace

from app.config import settings
from app.shared.interfaces.storage.document_storage import IDocumentStorage

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__, None)


class DocumentStorageClient(IDocumentStorage):
    """S3-compatible client for storing note files. Bucket created on first use."""

    def __init__(self) -> None:
        self._endpoint_url = settings.DOCUMENT_STORAGE_ENDPOINT
        self._bucket = settings.DOCUMENT_STORAGE_BUCKET
        self._access_key = settings.DOCUMENT_STORAGE_ACCESS_KEY
        self._secret_key = settings.DOCUMENT_STORAGE_SECRET_KEY
        self._region = settings.DOCUMENT_STORAGE_REGION

        # Path-style addressing is required for MinIO and many local S3-compatible endpoints.
        self._config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

    def _client_kwargs(self) -> dict[str, object]:
        return {
            "service_name": "s3",
            "endpoint_url": self._endpoint_url,
            "aws_access_key_id": self._access_key,
            "aws_secret_access_key": self._secret_key,
            "region_name": self._region,
            "config": self._config,
        }

    async def _ensure_bucket(self, client) -> None:
        with tracer.start_as_current_span("s3.ensure_bucket") as span:
            span.set_attribute("storage.bucket", self._bucket)
            span.set_attribute("storage.system", "s3")
            span.set_attribute("storage.endpoint_url", self._endpoint_url)

            try:
                await client.head_bucket(Bucket=self._bucket)
                return
            except ClientError as e:
                code = str(e.response.get("Error", {}).get("Code", ""))
                # Not found / not created yet.
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise

            await client.create_bucket(Bucket=self._bucket)
            logger.info("Created bucket %s", self._bucket)

    async def upload(
        self,
        path: str,
        raw: bytes,
    ) -> str:
        """Upload file content as object; return storage key (object name)."""
        key = path
        with tracer.start_as_current_span("s3.put_object") as span:
            span.set_attribute("storage.bucket", self._bucket)
            span.set_attribute("storage.key", key)
            span.set_attribute("storage.system", "s3")
            span.set_attribute("storage.endpoint_url", self._endpoint_url)
            span.set_attribute("storage.object_size", len(raw))

            session = get_session()
            async with session.create_client(**self._client_kwargs()) as client:
                await self._ensure_bucket(client)
                await client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=raw,
                    ContentLength=len(raw),
                )
        return key

    async def generate_pre_signed_url(self, storage_key: str) -> str:
        """Generate a pre-signed URL for a note content object."""
        with tracer.start_as_current_span("s3.presign_get_object") as span:
            span.set_attribute("storage.bucket", self._bucket)
            span.set_attribute("storage.key", storage_key)
            span.set_attribute("storage.system", "s3")
            span.set_attribute("storage.endpoint_url", self._endpoint_url)

            session = get_session()
            async with session.create_client(**self._client_kwargs()) as client:
                return await client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self._bucket, "Key": storage_key},
                    ExpiresIn=3600,
                )

    async def delete(self, storage_key: str) -> None:
        """Remove object by storage key."""
        with tracer.start_as_current_span("s3.delete_object") as span:
            span.set_attribute("storage.bucket", self._bucket)
            span.set_attribute("storage.key", storage_key)
            span.set_attribute("storage.system", "s3")
            span.set_attribute("storage.endpoint_url", self._endpoint_url)

            session = get_session()
            async with session.create_client(**self._client_kwargs()) as client:
                await client.delete_object(Bucket=self._bucket, Key=storage_key)
