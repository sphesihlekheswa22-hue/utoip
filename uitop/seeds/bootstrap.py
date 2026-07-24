"""Database seeding for roles, permissions, departments, and admin user."""
from __future__ import annotations

from datetime import datetime, timezone

from uitop.core.permissions import ALL_PERMISSIONS, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from uitop.core.security import hash_password
from uitop.extensions import db
from uitop.models.department import Department
from uitop.models.inventory import Computer, NetworkDevice, Printer, Server
from uitop.models.role import Permission, Role
from uitop.models.user import User


DEFAULT_ADMIN_EMAIL = "admin@umzinyathi.gov.za"
DEFAULT_ADMIN_PASSWORD = "Admin@UITOP2026"
DEFAULT_ADMIN_NAME = "Thandi Nkosi"

DEFAULT_DEPARTMENTS = [
    ("IT Operations", "IT", "Municipal ICT operations"),
    ("Corporate Services", "CORP", "Corporate services"),
    ("Finance", "FIN", "Budget and finance"),
    ("Technical Services", "TECH", "Technical services"),
]


def seed_permissions() -> dict[str, Permission]:
    by_code: dict[str, Permission] = {}
    for code, description in ALL_PERMISSIONS:
        perm = Permission.query.filter_by(code=code).first()
        if perm is None:
            perm = Permission(code=code, description=description)
            db.session.add(perm)
        else:
            perm.description = description
        by_code[code] = perm
    db.session.flush()
    return by_code


def seed_roles(permissions: dict[str, Permission]) -> dict[str, Role]:
    by_name: dict[str, Role] = {}
    for name, codes in ROLE_PERMISSIONS.items():
        role = Role.query.filter_by(name=name).first()
        if role is None:
            role = Role(
                name=name,
                description=ROLE_DESCRIPTIONS.get(name),
                is_system=True,
            )
            db.session.add(role)
        else:
            role.description = ROLE_DESCRIPTIONS.get(name, role.description)
            role.is_system = True
        role.permissions = [permissions[c] for c in codes if c in permissions]
        by_name[name] = role
    db.session.flush()
    return by_name


def seed_departments() -> list[Department]:
    created = []
    for name, code, description in DEFAULT_DEPARTMENTS:
        dept = Department.query.filter_by(name=name).first()
        if dept is None:
            dept = Department(name=name, code=code, description=description)
            db.session.add(dept)
            created.append(dept)
    db.session.flush()
    return created


def seed_admin(roles: dict[str, Role], email: str | None = None, password: str | None = None) -> User:
    email = (email or DEFAULT_ADMIN_EMAIL).strip().lower()
    password = password or DEFAULT_ADMIN_PASSWORD
    user = User.query.filter_by(email=email).first()
    it_dept = Department.query.filter_by(code="IT").first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=DEFAULT_ADMIN_NAME,
            is_active=True,
            is_super_admin=True,
            department_id=it_dept.id if it_dept else None,
        )
        db.session.add(user)
    else:
        user.is_super_admin = True
        user.is_active = True
        if it_dept:
            user.department_id = it_dept.id
    if roles.get("super_admin") and roles["super_admin"] not in user.roles:
        user.roles = list({*user.roles, roles["super_admin"]})
    db.session.flush()
    return user


def seed_sample_inventory() -> None:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    if Computer.query.count() == 0:
        db.session.add_all(
            [
                Computer(
                    hostname="PC-FIN-014",
                    asset_tag="UMZ-PC-014",
                    ip_address="10.10.20.14",
                    mac_address="A4:4C:C8:1F:9B:22",
                    os_name="Windows 11",
                    os_version="23H2",
                    manufacturer="Dell",
                    model="OptiPlex 7010",
                    status="online",
                    agent_id="seed-agent-fin014",
                    agent_version="1.0.0",
                    last_seen_at=now - timedelta(minutes=2),
                    ram_gb=16,
                    disk_gb=512,
                    cpu_model="Intel i7",
                    cpu_cores=8,
                ),
                Computer(
                    hostname="PC-IT-002",
                    asset_tag="UMZ-PC-002",
                    ip_address="10.10.10.2",
                    mac_address="AA:BB:CC:DD:EE:02",
                    os_name="Windows 11",
                    os_version="23H2",
                    manufacturer="HP",
                    model="EliteDesk 800",
                    status="online",
                    agent_id="seed-agent-it002",
                    agent_version="1.0.0",
                    last_seen_at=now - timedelta(minutes=1),
                    ram_gb=32,
                    disk_gb=1024,
                    cpu_model="Intel i9",
                    cpu_cores=12,
                ),
                Computer(
                    hostname="LAP-CORP-08",
                    asset_tag="UMZ-LT-008",
                    ip_address="10.10.30.8",
                    mac_address="11:22:33:44:55:08",
                    os_name="Windows 11",
                    manufacturer="Lenovo",
                    model="ThinkPad T14",
                    status="offline",
                    agent_id="seed-agent-corp08",
                    agent_version="0.9.5",
                    last_seen_at=now - timedelta(hours=6),
                    ram_gb=16,
                    disk_gb=512,
                ),
            ]
        )
    if Server.query.count() == 0:
        db.session.add_all(
            [
                Server(
                    hostname="SRV-DC-01",
                    asset_tag="UMZ-SRV-01",
                    ip_address="10.10.1.10",
                    os_name="Windows Server 2022",
                    role="Domain Controller",
                    status="online",
                    agent_id="seed-srv-dc01",
                    agent_version="1.0.0",
                    last_seen_at=now - timedelta(minutes=1),
                ),
                Server(
                    hostname="SRV-FILE-01",
                    asset_tag="UMZ-SRV-02",
                    ip_address="10.10.1.20",
                    os_name="Windows Server 2019",
                    role="File Server",
                    status="online",
                    agent_id="seed-srv-file01",
                    agent_version="1.0.0",
                    last_seen_at=now - timedelta(minutes=3),
                ),
            ]
        )
    if NetworkDevice.query.count() == 0:
        db.session.add_all(
            [
                NetworkDevice(
                    hostname="SW-CORE-01",
                    ip_address="10.10.0.1",
                    mac_address="00:1A:2B:3C:4D:01",
                    device_type="switch",
                    vendor="Cisco",
                    status="online",
                    last_seen_at=now - timedelta(seconds=45),
                ),
                NetworkDevice(
                    hostname="FW-EDGE-01",
                    ip_address="10.10.0.2",
                    mac_address="00:1A:2B:3C:4D:02",
                    device_type="firewall",
                    vendor="Fortinet",
                    status="online",
                    last_seen_at=now - timedelta(minutes=1),
                ),
            ]
        )
    if Printer.query.count() == 0:
        db.session.add_all(
            [
                Printer(
                    name="PRT-FIN-01",
                    ip_address="10.10.40.11",
                    model="HP LaserJet MFP M528",
                    location="Finance Wing",
                    status="online",
                    last_seen_at=now - timedelta(minutes=2),
                ),
                Printer(
                    name="PRT-CORP-02",
                    ip_address="10.10.40.22",
                    model="Brother MFC-L8900CDW",
                    location="Corporate Services",
                    status="warning",
                    last_seen_at=now - timedelta(minutes=5),
                ),
            ]
        )
    db.session.flush()


def run_seed(*, admin_email: str | None = None, admin_password: str | None = None, sample_inventory: bool = True) -> dict:
    permissions = seed_permissions()
    roles = seed_roles(permissions)
    seed_departments()
    admin = seed_admin(roles, email=admin_email, password=admin_password)
    if sample_inventory:
        seed_sample_inventory()
        from uitop.services.assets import seed_asset_catalog, seed_assets_from_inventory

        seed_asset_catalog()
        seed_assets_from_inventory()
        from uitop.services.helpdesk import seed_sample_tickets

        seed_sample_tickets()
        from uitop.services.files_view import seed_sample_repository

        seed_sample_repository(actor_id=admin.id)
    db.session.commit()
    from uitop.models.assets import Asset
    from uitop.models.helpdesk import Ticket
    from uitop.models.files import RepoFile

    return {
        "permissions": len(permissions),
        "roles": len(roles),
        "admin_email": admin.email,
        "departments": Department.query.count(),
        "computers": Computer.query.count(),
        "servers": Server.query.count(),
        "network_devices": NetworkDevice.query.count(),
        "printers": Printer.query.count(),
        "assets": Asset.query.count(),
        "tickets": Ticket.query.count(),
        "repo_files": RepoFile.query.count(),
    }
