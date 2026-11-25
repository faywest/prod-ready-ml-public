"""Configuration, read from environment variables or a `.env` file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Spotify keys and app settings. Fill these in via `.env`, never in code."""

    # .env lives in packages/hitster_bingo/, no matter where you start the app from
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[2] / ".env", extra="ignore"
    )

    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8000/callback"
    playlist_id: str = "321iL49aeqqqtKfrQLO91I"


settings = Settings()
