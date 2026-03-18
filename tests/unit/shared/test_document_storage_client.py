import pytest


class _FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._bucket_exists = False

    async def head_bucket(self, *, Bucket: str) -> None:
        self.calls.append(("head_bucket", {"Bucket": Bucket}))
        if not self._bucket_exists:
            # Simulate botocore ClientError for missing bucket shape enough for our code.
            from botocore.exceptions import ClientError

            raise ClientError(
                error_response={"Error": {"Code": "NoSuchBucket", "Message": "not found"}},
                operation_name="HeadBucket",
            )

    async def create_bucket(self, **params) -> None:
        self.calls.append(("create_bucket", params))
        self._bucket_exists = True

    async def put_object(self, **params) -> None:
        self.calls.append(("put_object", params))

    async def delete_object(self, **params) -> None:
        self.calls.append(("delete_object", params))

    async def generate_presigned_url(self, **params) -> str:
        self.calls.append(("generate_presigned_url", params))
        return "http://example.invalid/presigned"


class _FakeClientContext:
    def __init__(self, client: _FakeS3Client) -> None:
        self._client = client

    async def __aenter__(self) -> _FakeS3Client:
        return self._client

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSession:
    def __init__(self, client: _FakeS3Client) -> None:
        self._client = client
        self.create_client_kwargs: list[dict] = []

    def create_client(self, **kwargs):
        self.create_client_kwargs.append(kwargs)
        return _FakeClientContext(self._client)


@pytest.mark.asyncio
async def test_upload_ensures_bucket_then_put_object(monkeypatch) -> None:
    from app.shared.storage.document_storage import DocumentStorageClient

    fake_client = _FakeS3Client()
    fake_session = _FakeSession(fake_client)

    import app.shared.storage.document_storage as mod

    monkeypatch.setattr(mod, "get_session", lambda: fake_session)

    storage = DocumentStorageClient()
    key = await storage.upload("notes/abc.txt", b"hello")

    assert key == "notes/abc.txt"

    # Ensure it checks bucket, creates it, then uploads
    assert [c[0] for c in fake_client.calls] == ["head_bucket", "create_bucket", "put_object"]
    put = [c for c in fake_client.calls if c[0] == "put_object"][0][1]
    assert put["Bucket"] == storage._bucket  # noqa: SLF001 (test-only introspection)
    assert put["Key"] == "notes/abc.txt"
    assert put["Body"] == b"hello"
    assert put["ContentLength"] == 5


@pytest.mark.asyncio
async def test_generate_presigned_url_calls_s3(monkeypatch) -> None:
    from app.shared.storage.document_storage import DocumentStorageClient

    fake_client = _FakeS3Client()
    fake_client._bucket_exists = True
    fake_session = _FakeSession(fake_client)

    import app.shared.storage.document_storage as mod

    monkeypatch.setattr(mod, "get_session", lambda: fake_session)

    storage = DocumentStorageClient()
    url = await storage.generate_pre_signed_url("notes/key.txt")
    assert url == "http://example.invalid/presigned"

    assert [c[0] for c in fake_client.calls] == ["generate_presigned_url"]
    params = fake_client.calls[0][1]
    assert params["ClientMethod"] == "get_object"
    assert params["Params"]["Bucket"] == storage._bucket  # noqa: SLF001
    assert params["Params"]["Key"] == "notes/key.txt"
    assert params["ExpiresIn"] == 3600


@pytest.mark.asyncio
async def test_delete_calls_delete_object(monkeypatch) -> None:
    from app.shared.storage.document_storage import DocumentStorageClient

    fake_client = _FakeS3Client()
    fake_client._bucket_exists = True
    fake_session = _FakeSession(fake_client)

    import app.shared.storage.document_storage as mod

    monkeypatch.setattr(mod, "get_session", lambda: fake_session)

    storage = DocumentStorageClient()
    await storage.delete("notes/key.txt")

    assert [c[0] for c in fake_client.calls] == ["delete_object"]
    params = fake_client.calls[0][1]
    assert params["Bucket"] == storage._bucket  # noqa: SLF001
    assert params["Key"] == "notes/key.txt"
