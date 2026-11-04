"""WSGI entrypoint for production servers (gunicorn)."""
import os

from uitop import create_app

_config = os.getenv("FLASK_ENV", "production")
app = create_app(_config if _config in {"development", "testing", "production"} else "production")
