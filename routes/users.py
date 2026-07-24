"""Users module — live DB user management."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from uitop.core.errors import APIError
from uitop.models.audit import AuditLog
from uitop.models.department import Department
from uitop.models.role import Role
from uitop.models.user import User
from uitop.services import users as users_svc
from uitop.services.computers_view import relative_time

bp = Blueprint("users", __name__, url_prefix="/users")


def _serialize(user: User) -> dict:
    roles = user.role_names()
    if user.is_super_admin:
        role_label = "Super Admin"
    elif roles:
        role_label = roles[0].replace("_", " ").title()
    else:
        role_label = "User"
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "roles": roles,
        "role_label": role_label,
        "department": user.department.name if user.department else "—",
        "department_id": user.department_id,
        "is_active": user.is_active,
        "status": "Active" if user.is_active else "Disabled",
        "is_super_admin": user.is_super_admin,
        "mfa_enabled": user.mfa_enabled,
        "last_login": relative_time(user.last_login_at) if user.last_login_at else "Never",
        "permissions": user.permission_codes(),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@bp.get("/")
def index():
    rows = [_serialize(u) for u in User.query.order_by(User.full_name).all()]
    kpis = {
        "total": len(rows),
        "active": sum(1 for r in rows if r["is_active"]),
        "admins": sum(1 for r in rows if r["is_super_admin"] or "admin" in r["roles"] or "super_admin" in r["roles"]),
        "disabled": sum(1 for r in rows if not r["is_active"]),
        "mfa": sum(1 for r in rows if r["mfa_enabled"]),
    }
    return render_template("users/index.html", active="users", users=rows, kpis=kpis)


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
def details(item_id):
    try:
        user = users_svc.get_user_or_404(item_id)
    except APIError:
        abort(404)
    data = _serialize(user)
    activity = (
        AuditLog.query.filter_by(actor_user_id=user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "users/details.html",
        active="users",
        user=data,
        item_id=item_id,
        activity=[a.to_dict() for a in activity],
        roles=Role.query.order_by(Role.name).all(),
    )


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
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
        user=_serialize(user),
        item_id=item_id,
        roles=roles,
        departments=departments,
    )


@bp.post("/<int:item_id>/roles")
def assign_roles(item_id):
    try:
        users_svc.assign_roles(
            item_id,
            request.form.getlist("roles"),
            actor_id=session.get("user_id"),
        )
        flash("Roles updated.", "success")
    except APIError as err:
        flash(err.message, "error")
    return redirect(url_for("users.details", item_id=item_id))


@bp.get("/<int:item_id>/profile")
def profile(item_id):
    return redirect(url_for("users.details", item_id=item_id))


@bp.get("/<int:item_id>/permissions")
def permissions(item_id):
    return redirect(url_for("users.details", item_id=item_id) + "#permissions")


@bp.get("/<int:item_id>/activity")
def activity(item_id):
    return redirect(url_for("users.details", item_id=item_id) + "#activity")


@bp.get("/<int:item_id>/sessions")
def sessions(item_id):
    return redirect(url_for("users.details", item_id=item_id))
