"""Settings routes."""
from flask import Blueprint, render_template

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.get("/")
def index():
    return render_template("settings/index.html", active="settings")
