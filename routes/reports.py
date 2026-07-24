"""Reports routes."""
from flask import Blueprint, render_template

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.get("/")
def index():
    return render_template("reports/index.html", active="reports")


@bp.route("/create", methods=["GET", "POST"])
def create():
    return render_template("reports/create.html", active="reports")


@bp.get("/<int:item_id>")
def details(item_id):
    return render_template("reports/details.html", active="reports", item_id=item_id)
