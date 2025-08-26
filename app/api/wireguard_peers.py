from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from app.services.wireguard_peer_service import WireGuardPeerService
import datetime
import qrcode
import io
import base64
from PIL import Image

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

@peers_bp.route('/wireguard/peers/<peer_name>/config', methods=['GET'])
@jwt_required()
def get_peer_config(peer_name):
    """Obtém a configuração do cliente para um peer específico"""
    service = WireGuardPeerService()
    try:
        # Obter informações do peer
        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter informações do peer"}), 500
            
        peer = next((p for p in peers_result['peers'] if p['name'] == peer_name), None)
        if not peer:
            return jsonify({"error": "Peer não encontrado"}), 404
            
        # Obter informações da interface
        interface_name = peer['interface']
        mikrotik_ip = service.mikrotik_api.get_mikrotik_ip()
        listen_port = service.mikrotik_api.get_wireguard_interface_port(interface_name)
        server_public_key = service.mikrotik_api.get_wireguard_interface_public_key(interface_name)
        
        # Gerar configuração do cliente
        config = f"""[Interface]
PrivateKey = {peer['private-key']}
Address = {peer['allowed_address']}
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {mikrotik_ip}:{listen_port}
PersistentKeepalive = 25"""
        
        return jsonify({
            'success': True,
            'config': config,
            'peer_name': peer_name
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@peers_bp.route('/wireguard/peers/<peer_name>/config/download', methods=['GET'])
@jwt_required()
def download_peer_config(peer_name):
    """Download da configuração do cliente como arquivo .conf"""
    service = WireGuardPeerService()
    try:
        # Obter informações do peer
        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter informações do peer"}), 500
            
        peer = next((p for p in peers_result['peers'] if p['name'] == peer_name), None)
        if not peer:
            return jsonify({"error": "Peer não encontrado"}), 404
            
        # Obter informações da interface
        interface_name = peer['interface']
        mikrotik_ip = service.mikrotik_api.get_mikrotik_ip()
        listen_port = service.mikrotik_api.get_wireguard_interface_port(interface_name)
        server_public_key = service.mikrotik_api.get_wireguard_interface_public_key(interface_name)
        
        # Gerar configuração do cliente
        config = f"""[Interface]
PrivateKey = {peer['private-key']}
Address = {peer['allowed_address']}
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {mikrotik_ip}:{listen_port}
PersistentKeepalive = 25"""
        
        # Criar arquivo temporário em memória
        config_file = io.BytesIO()
        config_file.write(config.encode('utf-8'))
        config_file.seek(0)
        
        return send_file(
            config_file,
            as_attachment=True,
            download_name=f"{peer_name}.conf",
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@peers_bp.route('/wireguard/peers/<peer_name>/qrcode', methods=['GET'])
@jwt_required()
def get_peer_qrcode(peer_name):
    """Gera QR Code da configuração do peer"""
    service = WireGuardPeerService()
    try:
        # Obter informações do peer
        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter informações do peer"}), 500
            
        peer = next((p for p in peers_result['peers'] if p['name'] == peer_name), None)
        if not peer:
            return jsonify({"error": "Peer não encontrado"}), 404
            
        # Obter informações da interface
        interface_name = peer['interface']
        mikrotik_ip = service.mikrotik_api.get_mikrotik_ip()
        listen_port = service.mikrotik_api.get_wireguard_interface_port(interface_name)
        server_public_key = service.mikrotik_api.get_wireguard_interface_public_key(interface_name)
        
        # Gerar configuração do cliente
        config = f"""[Interface]
PrivateKey = {peer['private-key']}
Address = {peer['allowed_address']}
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {mikrotik_ip}:{listen_port}
PersistentKeepalive = 25"""
        
        # Gerar QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(config)
        qr.make(fit=True)
        
        # Criar imagem do QR Code
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        img_buffer = io.BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'peer_name': peer_name
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
