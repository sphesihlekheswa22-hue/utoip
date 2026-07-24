"""Routes for monitoring module."""
from flask import Blueprint, render_template, redirect, url_for, flash

bp = Blueprint("monitoring", __name__, url_prefix="/monitoring")


@bp.get('/')
def index():
    return render_template("monitoring/index.html", active="monitoring")


@bp.get('/<int:item_id>')
def details(item_id):
    return render_template("monitoring/details.html", active="monitoring", item_id=item_id)


@bp.get('/<int:item_id>/history')
def history(item_id):
    return render_template("monitoring/history.html", active="monitoring", item_id=item_id)
