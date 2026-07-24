"""API error types and Flask handlers."""
from __future__ import annotations

from flask import Flask, jsonify, request


class APIError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, details=None, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code

    def to_dict(self):
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class UnauthorizedError(APIError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(APIError):
    status_code = 403
    code = "forbidden"


class NotFoundError(APIError):
    status_code = 404
    code = "not_found"


class ValidationError(APIError):
    status_code = 422
    code = "validation_error"


class ConflictError(APIError):
    status_code = 409
    code = "conflict"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(404)
    def handle_404(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "not_found", "message": "Resource not found", "details": None}}), 404
        return err

    @app.errorhandler(405)
    def handle_405(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "method_not_allowed", "message": "Method not allowed", "details": None}}), 405
        return err

    @app.errorhandler(500)
    def handle_500(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "server_error", "message": "Internal server error", "details": None}}), 500
        return err
