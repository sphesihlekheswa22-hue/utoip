"""API v1 blueprint registration."""
from flask import Blueprint, Flask

from uitop.api.v1 import agents, audit, auth, departments, inventory, roles, users


def register_api_v1(app: Flask) -> None:
    api = Blueprint("api_v1", __name__, url_prefix="/api/v1")
    api.register_blueprint(auth.bp)
    api.register_blueprint(users.bp)
    api.register_blueprint(roles.bp)
    api.register_blueprint(departments.bp)
    api.register_blueprint(audit.bp)
    api.register_blueprint(agents.bp)
    api.register_blueprint(inventory.bp)
    app.register_blueprint(api)


__all__ = ["register_api_v1"]
