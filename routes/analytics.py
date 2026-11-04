"""Legacy /analytics → Analysis hub."""
from flask import Blueprint, redirect, url_for

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.get("/")
def index():
    return redirect(url_for("analysis.index"))


@bp.get("/details")
def details():
    return redirect(url_for("analysis.index", view="executive"))
