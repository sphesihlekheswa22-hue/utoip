"""WSGI entrypoint for production servers (gunicorn)."""
import os

from uitop import create_app
from uitop.deploy import bootstrap_production_database

_config = os.getenv("FLASK_ENV", "production")
app = create_app(_config if _config in {"development", "testing", "production"} else "production")

if os.getenv("BOOTSTRAP_DB", "").lower() in {"1", "true", "yes"}:
    bootstrap_production_database(app)
