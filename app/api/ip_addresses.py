from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.config_service import ConfigService

ip_bp = Blueprint("ip_addresses", __name__)

@ip_bp.route("/ips", methods=["POST"])
@jwt_required()
def add_ip():
    """Adiciona um IP a uma interface"""
    data = request.json
    if not data or "address" not in data or "interface" not in data:
        return jsonify({"error": "Endereço IP e interface são obrigatórios"}), 400

    service = ConfigService()
    result = service.add_ip_to_interface(
        address=data["address"],
        interface=data["interface"],
        comment=data.get("comment", "")
    )
    
    return jsonify(result), 201 if result["success"] else 400

@ip_bp.route("/ips", methods=["GET"])
@jwt_required()
def list_ips():
    """Lista todos os IPs configurados"""
    service = ConfigService()
    result = service.get_all_ips()
    return jsonify(result), 200 if result["success"] else 500

@ip_bp.route("/ips/<string:ip_id>", methods=["DELETE"])
@jwt_required()
def remove_ip(ip_id):
    """Remove um IP pelo ID"""
    service = ConfigService()
    result = service.remove_ip(ip_id)
    return jsonify(result), 200 if result["success"] else 400