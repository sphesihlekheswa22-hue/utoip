"""Auth routes — session login backed by JWT auth service."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.services import auth as auth_service

bp = Blueprint("auth", __name__)

PUBLIC_ENDPOINTS = {
    "auth.root",
    "auth.login",
    "auth.register",
    "auth.forgot_password",
    "auth.reset_password",
    "auth.verify_otp",
    "auth.mfa",
    "static",
    # Agent bootstrap on other PCs (no login)
    "computers.download_agent_script",
    "computers.download_install_ps1",
    "computers.download_agent_exe",
    # Site connector bootstrap on LAN PCs (no login)
    "network.download_site_connector_script",
    "network.download_site_connector_ps1",
}


def _initials(full_name: str) -> str:
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def establish_session(user_dict: dict, tokens: dict) -> None:
    session.clear()
    session.permanent = True
    roles = user_dict.get("roles") or []
    role_keys = [str(r.get("name")) for r in roles if isinstance(r, dict) and r.get("name")]
    if user_dict.get("is_super_admin"):
        role_label = "Super Admin"
    elif role_keys:
        from uitop.services.users_view import ROLE_LABELS

        role_label = ROLE_LABELS.get(role_keys[0], role_keys[0].replace("_", " ").title())
    else:
        role_label = "User"
    permissions = list(user_dict.get("permissions") or [])
    session["user_id"] = user_dict["id"]
    session["role_keys"] = role_keys
    session["user"] = {
        "id": user_dict["id"],
        "email": user_dict["email"],
        "name": user_dict["full_name"],
        "role": role_label,
        "role_keys": role_keys,
        "initials": _initials(user_dict.get("full_name") or ""),
        "is_super_admin": bool(user_dict.get("is_super_admin")),
        "permissions": permissions,
    }
    session["permissions"] = permissions
    session["access_token"] = tokens.get("access_token")
    session["refresh_token"] = tokens.get("refresh_token")


@bp.get("/")
def root():
    if session.get("user_id"):
        from uitop.core.ui_rbac import safe_home_endpoint

        return redirect(url_for(safe_home_endpoint()))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") and request.method == "GET":
        from uitop.core.ui_rbac import safe_home_endpoint

        return redirect(url_for(safe_home_endpoint()))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if not email or not password:
            flash("Enter your email and password.", "error")
            return render_template("auth/login.html", email=email), 400

        try:
            result = auth_service.login(email, password)
            establish_session(result["user"], result["tokens"])
            from uitop.core.ui_rbac import safe_home_endpoint

            next_url = request.args.get("next") or url_for(safe_home_endpoint())
            if not str(next_url).startswith("/"):
                next_url = url_for(safe_home_endpoint())
            return redirect(next_url)
        except APIError as err:
            flash(err.message, "error")
            return render_template("auth/login.html", email=email), err.status_code

    return render_template("auth/login.html", email="")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    user_id = session.get("user_id")
    refresh = session.get("refresh_token")
    try:
        auth_service.logout(refresh_token=refresh, user_id=user_id)
    except Exception:  # noqa: BLE001
        pass
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        flash("Self-registration is disabled. Contact your UITOP administrator.", "error")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("If that account exists, a reset link will be sent.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot-password.html")


@bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        return redirect(url_for("auth.login"))
    return render_template("auth/reset-password.html")


@bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        flash("Complete sign-in with your password first.", "error")
        return redirect(url_for("auth.login"))
    return render_template("auth/verify-otp.html")


@bp.route("/mfa", methods=["GET", "POST"])
def mfa():
    if request.method == "POST":
        flash("Complete sign-in with your password first.", "error")
        return redirect(url_for("auth.login"))
    return render_template("auth/mfa.html")
