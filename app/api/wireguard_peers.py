from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.wireguard_peer_service import WireGuardPeerService
import datetime

peers_bp = Blueprint('wireguard_peers', __name__)

@peers_bp.route('/wireguard/peers', methods=['POST'])
@jwt_required()
def create_peer():
    data = request.json
    
    if not data or 'name' not in data or 'interface' not in data:
        return jsonify({"error": "Nome e interface são obrigatórios"}), 400
    
    client_dns = data.get('client_dns', '8.8.8.8')  # DNS opcional, padrão 8.8.8.8
    group_id = data.get('group_id')  # Grupo opcional
    
    # Validar group_id se fornecido
    if group_id is not None:
        try:
            group_id = int(group_id)
        except (ValueError, TypeError):
            return jsonify({"error": "ID do grupo deve ser um número válido"}), 400
    
    service = WireGuardPeerService()
    result = service.create_peer(
        name=data['name'],
        interface_name=data['interface'],
        client_dns=client_dns,
        group_id=group_id
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
    
@peers_bp.route('/wireguard/peers/stats', methods=['GET'])
@jwt_required()
def get_peers_stats():
    interface = request.args.get('interface')
    service = WireGuardPeerService()
    try:
        # Obter estatísticas atualizadas
        raw_peers = service.mikrotik_api.list_wireguard_peers()
        
        # Filtrar por interface se especificado
        if interface:
            raw_peers = [peer for peer in raw_peers if peer.get('interface') == interface]

        # Formatar apenas os dados necessários para atualização
        stats = []
        for peer in raw_peers:
            stats.append({
                'name': peer.get('name', ''),
                'interface': peer.get('interface', ''),
                'last_handshake': peer.get('last-handshake', ''),
                'rx': peer.get('rx', ''),
                'tx': peer.get('tx', ''),
                'public_key': peer.get('public-key', '')[:10] + '...'  # Chave abreviada para identificação
            })
        
        return jsonify({
            'success': True,
            'stats': stats,
            'count': len(stats),
            'timestamp': datetime.datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': [],
            'count': 0
        }), 500