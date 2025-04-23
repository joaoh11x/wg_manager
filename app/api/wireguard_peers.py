from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.wireguard_peer_service import WireGuardPeerService

peers_bp = Blueprint('wireguard_peers', __name__)

@peers_bp.route('/wireguard/peers', methods=['POST'])
@jwt_required()
def create_peer():
    data = request.json
    
    if not data or 'name' not in data or 'interface' not in data:
        return jsonify({"error": "Nome e interface são obrigatórios"}), 400
    
    client_dns = data.get('client_dns', '8.8.8.8')  # DNS opcional, padrão 8.8.8.8
    
    service = WireGuardPeerService()
    result = service.create_peer(
        name=data['name'],
        interface_name=data['interface'],
        client_dns=client_dns
    )
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify({"error": result['error']}), 400

@peers_bp.route('/wireguard/peers', methods=['GET'])
@jwt_required()
def list_peers():
    interface = request.args.get('interface')
    service = WireGuardPeerService()
    try:
        peers = service.list_peers(interface_name=interface)
        return jsonify(peers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@peers_bp.route('/wireguard/peers/<peer_name>', methods=['DELETE'])
@jwt_required()
def delete_peer(peer_name):
    service = WireGuardPeerService()
    try:
        service.delete_peer(peer_name)
        return jsonify({"message": f"Peer {peer_name} removido"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400