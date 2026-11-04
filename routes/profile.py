"""My Profile — current user's account hub (not admin CRUD)."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from uitop.core.security import hash_password, verify_password
from uitop.extensions import db
from uitop.models.user import User
from uitop.services.users_view import build_user_profile

bp = Blueprint("profile", __name__, url_prefix="/profile")


def _current_user() -> User | None:
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


def _refresh_session_user(user: User) -> None:
    """Keep topbar / context processor in sync after profile edits."""
    from routes.auth import _initials

    roles = user.role_names()
    if user.is_super_admin:
        role_label = "Super Admin"
    elif roles:
        role_label = str(roles[0]).replace("_", " ").title()
    else:
        role_label = "User"
    permissions = user.permission_codes()
    session["user"] = {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "role": role_label,
        "initials": _initials(user.full_name or ""),
        "is_super_admin": bool(user.is_super_admin),
        "permissions": permissions,
    }
    session["permissions"] = permissions


@bp.get("/")
def index():
    user = _current_user()
    if user is None:
        return redirect(url_for("auth.login"))
    profile = build_user_profile(user.id)
    return render_template(
        "profile/index.html",
        active="profile",
        profile=profile,
        user=profile.get("user") or user.to_dict(),
        me=user,
    )


@bp.route("/edit", methods=["GET", "POST"])
def edit():
    user = _current_user()
    if user is None:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()

        if not full_name:
            flash("Display name is required.", "error")
            return redirect(url_for("profile.edit"))
        if not email or "@" not in email:
            flash("Enter a valid email address.", "error")
            return redirect(url_for("profile.edit"))

        conflict = User.query.filter(User.email == email, User.id != user.id).first()
        if conflict:
            flash("That email is already used by another account.", "error")
            return redirect(url_for("profile.edit"))

        user.full_name = full_name
        user.email = email
        db.session.commit()
        _refresh_session_user(user)
        flash("Profile updated.", "success")
        return redirect(url_for("profile.index"))

    return render_template(
        "profile/edit.html",
        active="profile",
        me=user,
        user=user.to_dict(),
    )


@bp.route("/security", methods=["GET", "POST"])
def security():
    user = _current_user()
    if user is None:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new_pw = request.form.get("new_password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not verify_password(user.password_hash, current):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("profile.security"))
        if len(new_pw) < 8:
            flash("New password must be at least 8 characters.", "error")
            return redirect(url_for("profile.security"))
        if new_pw != confirm:
            flash("New password and confirmation do not match.", "error")
            return redirect(url_for("profile.security"))

        user.password_hash = hash_password(new_pw)
        db.session.commit()
        flash("Password changed successfully.", "success")
        return redirect(url_for("profile.index"))

    return render_template(
        "profile/security.html",
        active="profile",
        me=user,
        user=user.to_dict(),
    )
