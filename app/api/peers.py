from flask import Blueprint, request, jsonify
from app.services.wireguard_service import WireGuardService

peers_bp = Blueprint("peers", __name__)

@peers_bp.route("/peers", methods=["POST"])
def add_peer():
    data = request.json
    service = WireGuardService()
    service.add_peer(data["interface_name"], data["peer_name"], data["public_key"])
    return jsonify({"message": "Peer added successfully"}), 201