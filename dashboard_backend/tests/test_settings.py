from __future__ import annotations

from dashboard_backend.config.settings import get_settings


def test_settings_uses_env(monkeypatch):
    monkeypatch.setenv("CYBERSCOPE_DATABASE_URL", "sqlite:///./override.db")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = get_settings()
    assert settings.database_url.startswith("sqlite+aiosqlite")
    assert settings.frontend_origin == "http://localhost:5173"
    get_settings.cache_clear()  # type: ignore[attr-defined]
