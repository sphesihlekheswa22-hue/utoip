"""WSGI entrypoint for production servers (gunicorn)."""
import os

from uitop import create_app

_config = os.getenv("FLASK_ENV", "production")
app = create_app(_config if _config in {"development", "testing", "production"} else "production")

# DB migrate/seed runs in Render buildCommand — do not block port bind here.
