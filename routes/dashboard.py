"""Dashboard routes."""
from flask import Blueprint, redirect, render_template, url_for

from uitop.core.ui_rbac import is_employee_session
from uitop.services.dashboard import build_dashboard

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
def index():
    if is_employee_session():
        return redirect(url_for("employee.index"))
    data = build_dashboard()
    return render_template("dashboard/dashboard.html", active="dashboard", dash=data)
