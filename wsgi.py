"""WSGI entrypoint for production servers (gunicorn)."""
from uitop import create_app

app = create_app()
