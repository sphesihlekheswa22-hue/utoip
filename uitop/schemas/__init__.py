"""JSON response helpers."""
from __future__ import annotations

from flask import jsonify


def success(data=None, meta=None, status: int = 200):
    body = {"data": data, "meta": meta or {}}
    return jsonify(body), status


def created(data=None, meta=None):
    return success(data=data, meta=meta, status=201)
