"""Flask CLI commands for seeding and admin creation."""
from __future__ import annotations

import click
from flask import Flask

from uitop.core.security import hash_password
from uitop.extensions import db
from uitop.models.role import Role
from uitop.models.user import User
from uitop.seeds.bootstrap import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, run_seed


def register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    @click.option("--admin-email", default=None, help="Override admin email")
    @click.option("--admin-password", default=None, help="Override admin password")
    @click.option("--no-inventory", is_flag=True, help="Skip sample inventory rows")
    def seed_command(admin_email, admin_password, no_inventory):
        """Seed permissions, roles, departments, and admin user."""
        result = run_seed(
            admin_email=admin_email,
            admin_password=admin_password,
            sample_inventory=not no_inventory,
        )
        click.echo("Seed complete:")
        for key, value in result.items():
            click.echo(f"  {key}: {value}")
        click.echo(f"  demo password (if new admin): {admin_password or DEFAULT_ADMIN_PASSWORD}")

    @app.cli.command("create-admin")
    @click.option("--email", default=DEFAULT_ADMIN_EMAIL, show_default=True)
    @click.option("--password", default=DEFAULT_ADMIN_PASSWORD, show_default=True)
    @click.option("--name", default="Platform Admin", show_default=True)
    def create_admin_command(email, password, name):
        """Create or promote a super-admin user."""
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name=name,
                is_active=True,
                is_super_admin=True,
            )
            db.session.add(user)
            click.echo(f"Created admin {email}")
        else:
            user.password_hash = hash_password(password)
            user.full_name = name
            user.is_active = True
            user.is_super_admin = True
            click.echo(f"Updated admin {email}")

        role = Role.query.filter_by(name="super_admin").first()
        if role and role not in user.roles:
            user.roles.append(role)
        db.session.commit()
        click.echo("Done.")
