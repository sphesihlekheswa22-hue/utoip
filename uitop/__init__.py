"""UITOP Flask application factory."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify

from uitop.config import config_by_name
from uitop.extensions import cors, db, jwt, migrate


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    config_obj = config_by_name.get(config_name, config_by_name["default"])

    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config.from_object(config_obj)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    (root / "instance").mkdir(parents=True, exist_ok=True)

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli(app)
    _register_context(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    # Import models so metadata is registered for Alembic / create_all
    import uitop.models  # noqa: F401

    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parent.parent / "migrations"))
    jwt.init_app(app)

    origins = app.config.get("CORS_ORIGINS", "*")
    if origins == "*":
        cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    else:
        cors.init_app(
            app,
            resources={r"/api/*": {"origins": [o.strip() for o in origins.split(",")]}},
        )

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": {"code": "unauthorized", "message": reason, "details": None}}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": {"code": "invalid_token", "message": reason, "details": None}}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"error": {"code": "token_expired", "message": "Access token expired", "details": None}}), 401

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return jsonify({"error": {"code": "token_revoked", "message": "Token has been revoked", "details": None}}), 401


def _register_blueprints(app: Flask) -> None:
    from routes import register_blueprints as register_ui

    register_ui(app)

    from uitop.api.v1 import register_api_v1

    register_api_v1(app)


def _register_error_handlers(app: Flask) -> None:
    from uitop.core.errors import register_error_handlers

    register_error_handlers(app)


def _register_cli(app: Flask) -> None:
    from uitop.seeds.cli import register_cli

    register_cli(app)


def _register_context(app: Flask) -> None:
    from flask import redirect, request, session, url_for

    from routes.auth import PUBLIC_ENDPOINTS

    @app.before_request
    def require_ui_login():
        if request.path.startswith("/api/"):
            return None
        if request.endpoint in PUBLIC_ENDPOINTS or (request.endpoint or "").startswith("static"):
            return None
        if session.get("user_id"):
            return None
        # Allow auth blueprint pages already listed; anything else needs login
        if request.endpoint and request.endpoint.startswith("auth."):
            return None
        return redirect(url_for("auth.login", next=request.path))

    @app.context_processor
    def inject_globals():
        user = session.get("user") or {
            "name": "Guest",
            "role": "Unauthenticated",
            "email": "",
            "initials": "?",
        }
        return {
            "app_name": "UITOP",
            "org_name": "Umzinyathi Municipality",
            "demo_user": user,
            "current_user": user,
            "is_authenticated": bool(session.get("user_id")),
        }
