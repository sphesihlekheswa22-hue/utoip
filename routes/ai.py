"""Routes for ai module."""
from flask import Blueprint, render_template, redirect, url_for, flash

bp = Blueprint("ai", __name__, url_prefix="/ai")


@bp.get('/')
def index():
    return render_template("ai/index.html", active="ai")


@bp.get('/<int:item_id>/history')
def history(item_id):
    return render_template("ai/history.html", active="ai", item_id=item_id)
