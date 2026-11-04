"""Users — Identity & User Management Center."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.extensions import db
from uitop.models.auth import RefreshToken
from uitop.models.department import Department
from uitop.models.role import Role
from uitop.services import users as users_svc
from uitop.services import users_view as uv
from uitop.services.audit import log_audit

bp = Blueprint("users", __name__, url_prefix="/users")

ALLOWED_VIEWS = {
    "dashboard",
    "directory",
    "departments",
    "roles",
    "permissions",
    "teams",
    "sessions",
    "assignments",
    "audit",
    "invitations",
}

PROFILE_VIEWS = {
    "overview",
    "assets",
    "tickets",
    "software",
    "permissions",
    "sessions",
    "activity",
    "documents",
    "history",
}


@bp.get("/")
def index():
    view = request.args.get("view", "dashboard")
    if view not in ALLOWED_VIEWS:
        view = "dashboard"
    # Alias
    if request.args.get("view") == "users":
        view = "directory"
    payload = uv.build_module_payload()
    return render_template(
        "users/index.html",
        active="users",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    roles = Role.query.order_by(Role.name).all()
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        try:
            role_names = request.form.getlist("roles")
            user = users_svc.create_user(
                email=request.form.get("email"),
                password=request.form.get("password"),
                full_name=request.form.get("full_name"),
                role_names=role_names or None,
                department_id=request.form.get("department_id", type=int) or None,
                actor_id=session.get("user_id"),
            )
            flash(f"User {user.email} created.", "success")
            return redirect(url_for("users.details", item_id=user.id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "users/create.html",
        active="users",
        roles=roles,
        departments=departments,
    )


@bp.get("/<int:item_id>")
def details(item_id: int):
    view = request.args.get("view", "overview")
    if view not in PROFILE_VIEWS:
        view = "overview"
    profile = uv.build_user_profile(item_id)
    if not profile:
        abort(404)
    return render_template(
        "users/details.html",
        active="users",
        item_id=item_id,
        view=view,
        profile=profile,
        user=profile["user"],
        roles=Role.query.order_by(Role.name).all(),
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id: int):
    try:
        user = users_svc.get_user_or_404(item_id)
    except APIError:
        abort(404)
    roles = Role.query.order_by(Role.name).all()
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        try:
            payload = {
                "full_name": request.form.get("full_name"),
                "is_active": request.form.get("is_active") == "1",
                "department_id": request.form.get("department_id", type=int) or None,
                "role_names": request.form.getlist("roles"),
            }
            password = request.form.get("password")
            if password:
                payload["password"] = password
            users_svc.update_user(item_id, payload, actor_id=session.get("user_id"))
            flash("User updated.", "success")
            return redirect(url_for("users.details", item_id=item_id))
        except APIError as err:
            flash(err.message, "error")
    return render_template(
        "users/edit.html",
        active="users",
        user=uv.serialize_user(user),
        item_id=item_id,
        roles=roles,
        departments=departments,
    )


@bp.post("/<int:item_id>/roles")
def assign_roles(item_id: int):
    try:
        users_svc.assign_roles(
            item_id,
            request.form.getlist("roles"),
            actor_id=session.get("user_id"),
        )
        flash("Roles updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("users.details", item_id=item_id, view="permissions"))


@bp.post("/<int:item_id>/sessions/<int:token_id>/revoke")
def revoke_session(item_id: int, token_id: int):
    token = RefreshToken.query.filter_by(id=token_id, user_id=item_id).first()
    if token is None:
        flash("Session not found.", "error")
    else:
        from datetime import datetime, timezone

        token.revoked_at = datetime.now(timezone.utc)
        db.session.commit()
        log_audit(
            "users.session_revoke",
            actor_user_id=session.get("user_id"),
            resource_type="user",
            resource_id=item_id,
        )
        flash("Session terminated.", "success")
    return redirect(url_for("users.details", item_id=item_id, view="sessions"))


@bp.get("/<int:item_id>/profile")
def profile(item_id: int):
    return redirect(url_for("users.details", item_id=item_id, view="overview"))


@bp.get("/<int:item_id>/permissions")
def permissions(item_id: int):
    return redirect(url_for("users.details", item_id=item_id, view="permissions"))


@bp.get("/<int:item_id>/activity")
def activity(item_id: int):
    return redirect(url_for("users.details", item_id=item_id, view="activity"))


@bp.get("/<int:item_id>/sessions")
def sessions(item_id: int):
    return redirect(url_for("users.details", item_id=item_id, view="sessions"))
