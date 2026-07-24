"""Dashboard routes."""
from flask import Blueprint, render_template

from uitop.services.dashboard import build_dashboard

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
def index():
    data = build_dashboard()
    return render_template("dashboard/dashboard.html", active="dashboard", dash=data)
