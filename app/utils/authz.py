from __future__ import annotations

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, jwt_required


def admin_required(fn):
    """Require a valid JWT and an `admin` role claim."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt() or {}
        if claims.get("role") != "admin":
            return jsonify({"error": "Acesso negado"}), 403
        return fn(*args, **kwargs)

    return wrapper
