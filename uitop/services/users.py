"""User and role management services."""
from __future__ import annotations

from uitop.core.errors import ConflictError, NotFoundError, ValidationError
from uitop.core.security import hash_password
from uitop.extensions import db
from uitop.models.department import Department
from uitop.models.role import Permission, Role
from uitop.models.user import User
from uitop.services.audit import log_audit


def get_user_or_404(user_id: int) -> User:
    user = User.query.get(user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def create_user(
    *,
    email: str,
    password: str,
    full_name: str,
    role_names: list[str] | None = None,
    department_id: int | None = None,
    is_super_admin: bool = False,
    actor_id: int | None = None,
) -> User:
    email = (email or "").strip().lower()
    if not email or not password or not full_name:
        raise ValidationError("email, password, and full_name are required")
    if User.query.filter_by(email=email).first():
        raise ConflictError("Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        department_id=department_id,
        is_super_admin=is_super_admin,
    )
    if role_names:
        roles = Role.query.filter(Role.name.in_(role_names)).all()
        found = {r.name for r in roles}
        missing = set(role_names) - found
        if missing:
            raise ValidationError("Unknown role(s)", details={"missing": sorted(missing)})
        user.roles = roles

    db.session.add(user)
    db.session.commit()
    log_audit("users.create", actor_user_id=actor_id, resource_type="user", resource_id=user.id)
    return user


def update_user(user_id: int, data: dict, actor_id: int | None = None) -> User:
    user = get_user_or_404(user_id)
    if "full_name" in data and data["full_name"]:
        user.full_name = data["full_name"].strip()
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = bool(data["is_active"])
    if "department_id" in data:
        user.department_id = data["department_id"]
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data["password"])
    if "role_names" in data and data["role_names"] is not None:
        roles = Role.query.filter(Role.name.in_(data["role_names"])).all()
        found = {r.name for r in roles}
        missing = set(data["role_names"]) - found
        if missing:
            raise ValidationError("Unknown role(s)", details={"missing": sorted(missing)})
        user.roles = roles
    db.session.commit()
    log_audit("users.update", actor_user_id=actor_id, resource_type="user", resource_id=user.id)
    return user


def assign_roles(user_id: int, role_names: list[str], actor_id: int | None = None) -> User:
    return update_user(user_id, {"role_names": role_names}, actor_id=actor_id)


def list_roles() -> list[Role]:
    return Role.query.order_by(Role.name).all()


def get_role_or_404(role_id: int) -> Role:
    role = Role.query.get(role_id)
    if role is None:
        raise NotFoundError("Role not found")
    return role


def create_role(name: str, description: str | None, permission_codes: list[str] | None, actor_id: int | None = None) -> Role:
    name = (name or "").strip().lower().replace(" ", "_")
    if not name:
        raise ValidationError("name is required")
    if Role.query.filter_by(name=name).first():
        raise ConflictError("Role already exists")
    role = Role(name=name, description=description, is_system=False)
    if permission_codes:
        perms = Permission.query.filter(Permission.code.in_(permission_codes)).all()
        found = {p.code for p in perms}
        missing = set(permission_codes) - found
        if missing:
            raise ValidationError("Unknown permission(s)", details={"missing": sorted(missing)})
        role.permissions = perms
    db.session.add(role)
    db.session.commit()
    log_audit("roles.create", actor_user_id=actor_id, resource_type="role", resource_id=role.id)
    return role


def update_role_permissions(role_id: int, permission_codes: list[str], actor_id: int | None = None) -> Role:
    role = get_role_or_404(role_id)
    perms = Permission.query.filter(Permission.code.in_(permission_codes)).all()
    found = {p.code for p in perms}
    missing = set(permission_codes) - found
    if missing:
        raise ValidationError("Unknown permission(s)", details={"missing": sorted(missing)})
    role.permissions = perms
    db.session.commit()
    log_audit("roles.update_permissions", actor_user_id=actor_id, resource_type="role", resource_id=role.id)
    return role


def list_departments() -> list[Department]:
    return Department.query.order_by(Department.name).all()


def create_department(name: str, code: str | None = None, description: str | None = None, actor_id: int | None = None) -> Department:
    name = (name or "").strip()
    if not name:
        raise ValidationError("name is required")
    if Department.query.filter_by(name=name).first():
        raise ConflictError("Department already exists")
    dept = Department(name=name, code=code, description=description)
    db.session.add(dept)
    db.session.commit()
    log_audit("departments.create", actor_user_id=actor_id, resource_type="department", resource_id=dept.id)
    return dept
