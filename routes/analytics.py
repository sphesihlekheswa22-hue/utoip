"""Analytics routes."""
from flask import Blueprint, render_template

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.get("/")
def index():
    return render_template("analytics/index.html", active="analytics")


@bp.get("/details")
def details():
    return render_template("analytics/details.html", active="analytics")
