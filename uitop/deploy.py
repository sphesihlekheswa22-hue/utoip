"""Production deploy helpers (Render, etc.)."""
from __future__ import annotations

import logging

from flask import Flask

logger = logging.getLogger(__name__)


def bootstrap_production_database(app: Flask) -> None:
    """Run migrations and first-run seed once (use with gunicorn --preload)."""
    with app.app_context():
        from flask_migrate import upgrade

        from uitop.models.user import User
        from uitop.seeds.bootstrap import run_seed

        logger.info("Running database migrations…")
        upgrade()
        if User.query.count() == 0:
            logger.info("Empty database — running initial seed…")
            run_seed()
            logger.info("Initial seed completed.")
        else:
            logger.info("Database already has users; skipping seed.")
