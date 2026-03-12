"""Wait for PostgreSQL to be ready using app Settings and asyncpg. Used by initial_db.sh."""

import asyncio
import sys
import time

from app.config import Settings


async def wait_for_db(timeout_seconds: float = 60, interval: float = 1.0) -> bool:
    """Return True when DB is accepting connections, False on timeout."""
    settings = Settings()
    url = settings.database_url
    if not url.startswith("postgresql+asyncpg://"):
        print("DATABASE_URL is not PostgreSQL asyncpg; skipping wait.", file=sys.stderr)
        return True
    # asyncpg connection string (no +asyncpg in the lib's connect)
    dsn = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    import asyncpg

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=5.0)
            await conn.close()
            return True
        except Exception:
            await asyncio.sleep(interval)
    return False


def main() -> None:
    ok = asyncio.run(wait_for_db())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
