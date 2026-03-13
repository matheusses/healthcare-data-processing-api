"""Unit tests for database engine and session factory."""

from unittest.mock import MagicMock, patch

from app.config import Settings
from app.shared.db.database import build_engine


def test_build_engine_instruments_sqlalchemy_for_tracing() -> None:
    """build_engine instruments the async engine's sync_engine so DB ops are traced."""
    with patch("app.shared.db.database.SQLAlchemyInstrumentor") as mock_instrumentor:
        mock_instrumentor.return_value.instrument = MagicMock()
        # Use in-memory SQLite so no real DB is required
        settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
        engine = build_engine(settings)
        mock_instrumentor.return_value.instrument.assert_called_once()
        call_kw = mock_instrumentor.return_value.instrument.call_args[1]
        assert "engine" in call_kw
        assert call_kw["engine"] is engine.sync_engine
