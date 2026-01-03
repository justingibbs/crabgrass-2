"""Application configuration via environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env file relative to this file's location (project_root/.env)
_this_file = Path(__file__).resolve()
_project_root = _this_file.parent.parent.parent  # config.py -> crabgrass -> backend -> project_root
_env_file = _project_root / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
    )

    # Database
    database_path: Path = Path("./data/crabgrass.duckdb")

    # File storage for JJ repositories
    storage_root: Path = Path("./data/ideas")

    # Gemini API (matches GOOGLE_API_KEY in .env)
    google_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Dev auth cookie name
    dev_user_cookie: str = "crabgrass_dev_user"


settings = Settings()
