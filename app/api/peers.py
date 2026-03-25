from flask import Blueprint, request, jsonify
from app.services.wireguard_service import WireGuardService

from app.utils.authz import admin_required

peers_bp = Blueprint("peers", __name__)

@peers_bp.route("/peers", methods=["POST"])
@admin_required
def add_peer():
    data = request.get_json(silent=True) or {}
    if not all(k in data for k in ("interface_name", "peer_name", "public_key")):
        return jsonify({"error": "interface_name, peer_name e public_key são obrigatórios"}), 400

    service = WireGuardService()
    service.add_peer(data["interface_name"], data["peer_name"], data["public_key"])
    return jsonify({"message": "Peer added successfully"}), 201