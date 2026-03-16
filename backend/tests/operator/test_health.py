from unittest.mock import MagicMock, patch

from app.ops.health import check_service_health


def test_check_service_health_returns_ready_with_healthy_db() -> None:
    # We can't easily use the real engine without a DB, but we can mock it
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection

    with patch("app.ops.health.settings") as mock_settings:
        mock_settings.POSTGRES_SERVER = "server"
        mock_settings.POSTGRES_USER = "user"
        mock_settings.POSTGRES_DB = "db"

        result = check_service_health(mock_engine)
        assert result.status == "ready"
        assert result.service == "telegram-first-backend"
        assert result.database_configured is True
        assert result.database_reachable is True

def test_check_service_health_returns_not_ready_when_db_unreachable() -> None:
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("connection refused")

    with patch("app.ops.health.settings") as mock_settings:
        mock_settings.POSTGRES_SERVER = "server"
        mock_settings.POSTGRES_USER = "user"
        mock_settings.POSTGRES_DB = "db"

        result = check_service_health(mock_engine)
        assert result.status == "not_ready"
        assert result.service == "telegram-first-backend"
        assert result.database_configured is True
        assert result.database_reachable is False

def test_check_service_health_returns_not_ready_when_db_not_configured() -> None:
    # Mock settings to simulate missing configuration
    with patch("app.ops.health.settings") as mock_settings:
        mock_settings.POSTGRES_SERVER = None
        mock_settings.POSTGRES_USER = "user"
        mock_settings.POSTGRES_DB = "db"

        mock_engine = MagicMock()
        result = check_service_health(mock_engine)
        assert result.status == "not_ready"
        assert result.database_configured is False
        assert result.database_reachable is False
