"""UITOP Flask application factory."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify

from uitop.config import config_by_name
from uitop.extensions import cors, db, jwt, migrate


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    config_obj = config_by_name.get(config_name, config_by_name["default"])

    # Project root (or PyInstaller _MEIPASS when frozen)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        root = Path(__file__).resolve().parent.parent

    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config.from_object(config_obj)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    # Prefer explicit DATABASE_URL (desktop sets this next to the .exe)
    if not os.getenv("DATABASE_URL"):
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
    from flask import abort, flash, redirect, request, session, url_for

    from routes.auth import PUBLIC_ENDPOINTS
    from uitop.core.ui_rbac import (
        has_perm,
        is_employee_session,
        required_permission_for_request,
        safe_home_endpoint,
        sync_session_permissions,
    )

    @app.before_request
    def require_ui_login():
        if request.path.startswith("/api/"):
            return None
        if request.endpoint in PUBLIC_ENDPOINTS or (request.endpoint or "").startswith("static"):
            return None
        # Allow auth blueprint pages already listed; anything else needs login
        if request.endpoint and request.endpoint.startswith("auth."):
            return None
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))

        # Keep RBAC session in sync with DB roles
        sync_session_permissions()

        # Discovery API — any inventory module permission (checked again in-route)
        if request.endpoint and request.endpoint.startswith("discovery."):
            from flask import jsonify

            from uitop.core.permissions import (
                COMPUTERS_READ,
                COMPUTERS_WRITE,
                NETWORK_READ,
                NETWORK_WRITE,
                PRINTERS_READ,
                PRINTERS_WRITE,
                SERVERS_READ,
                SERVERS_WRITE,
            )

            if request.endpoint == "discovery.import_hosts":
                ok = has_perm(COMPUTERS_WRITE, NETWORK_WRITE, SERVERS_WRITE, PRINTERS_WRITE)
            else:
                ok = has_perm(COMPUTERS_READ, NETWORK_READ, SERVERS_READ, PRINTERS_READ)
            if not ok:
                return jsonify({"error": "Forbidden"}), 403
            return None

        # Enforce RBAC on UI routes — soft deny (no hard 403 pages for HTML)
        needed = required_permission_for_request(request.endpoint, request.method)
        if needed and not has_perm(needed):
            wants_json = (
                request.path.startswith("/ai/ask")
                or request.path.startswith("/ai/sessions")
                or request.path.startswith("/api/")
                or request.accept_mimetypes.best == "application/json"
                or request.is_json
            )
            if wants_json:
                from flask import jsonify

                return jsonify({"error": "Forbidden", "required": needed}), 403

            flash(
                "That area is locked for your role. You were redirected to a page you can access.",
                "error",
            )
            home = safe_home_endpoint()
            # Avoid redirect loops
            if request.endpoint == home:
                return redirect(url_for("profile.index"))
            ref = request.referrer
            if (
                request.method in ("POST", "PUT", "PATCH", "DELETE")
                and ref
                and ref.startswith(request.host_url)
                and "/login" not in ref
            ):
                return redirect(ref)
            return redirect(url_for(home))
        return None

    @app.context_processor
    def inject_globals():
        user = session.get("user") or {
            "name": "Guest",
            "role": "Unauthenticated",
            "email": "",
            "initials": "?",
        }

        def modify_query(**new_params):
            """Build current path with updated query string (for pagination links)."""
            args = request.args.to_dict(flat=True)
            for key, value in new_params.items():
                if value is None or value == "":
                    args.pop(key, None)
                else:
                    args[key] = value
            qs = "&".join(f"{k}={v}" for k, v in args.items())
            return f"{request.path}?{qs}" if qs else request.path

        def can(*codes: str) -> bool:
            return has_perm(*codes)

        unread_notifications = 0
        uid = session.get("user_id")
        if uid:
            try:
                from uitop.services.notifications import unread_count

                unread_notifications = unread_count(uid)
            except Exception:
                unread_notifications = 0

        branding = {}
        try:
            from uitop.core.branding import resolve_branding
            from uitop.services.settings_view import get_category

            branding = resolve_branding(get_category("general"))
        except Exception:
            from uitop.core.branding import resolve_branding

            branding = resolve_branding(None)

        return {
            **branding,
            "demo_user": user,
            "current_user": user,
            "is_authenticated": bool(session.get("user_id")),
            "modify_query": modify_query,
            "can": can,
            "is_employee": is_employee_session(),
            "user_permissions": session.get("permissions") or [],
            "unread_notifications": unread_notifications,
        }
