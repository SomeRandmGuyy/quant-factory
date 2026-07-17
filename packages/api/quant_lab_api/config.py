"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables with sensible defaults.
Supports both SQLite (development) and PostgreSQL (production).
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: packages/api/quant_lab_api/config.py -> ../../../
_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=(
            str(_REPO_ROOT / ".env"),
            str(_API_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Quant Factory API"
    APP_VERSION: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = f"sqlite:///{_REPO_ROOT / 'quant_lab.db'}"

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Parse CORS origins from comma-separated string or JSON-like list."""
        raw = self.cors_origins.strip()
        if raw.startswith("["):
            # tolerate .env.example JSON-ish format
            raw = raw.strip("[]").replace('"', "").replace("'", "")
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # Data paths (override via CSV_DATA_DIR / FUNDAMENTALS_FILE)
    csv_data_dir: str = str(_REPO_ROOT / "data")
    fundamentals_file: str = str(_REPO_ROOT / "data" / "fundamentals.csv")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        return self.database_url.startswith("postgresql")


settings = Settings()
