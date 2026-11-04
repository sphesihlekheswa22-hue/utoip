"""UITOP application configuration."""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _normalize_database_url(raw: str | None) -> str | None:
    """Render/Heroku often provide postgres:// — SQLAlchemy needs postgresql+psycopg2://."""
    url = (raw or "").strip()
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "render.com" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def _default_sqlite_uri() -> str:
    return f"sqlite:///{BASE_DIR / 'instance' / 'uitop.db'}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "uitop-dev-secret-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL")) or _default_sqlite_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}
    TEMPLATES_AUTO_RELOAD = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    JSON_SORT_KEYS = False

    # Enterprise IT file repository (local storage; NAS/cloud backends later)
    FILES_ROOT = Path(os.getenv("FILES_ROOT", str(BASE_DIR / "instance" / "repo_files")))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "512")) * 1024 * 1024


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    DEBUG = False
    DEMO_MODE = False
    TEMPLATES_AUTO_RELOAD = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
