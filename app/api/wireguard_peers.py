from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
import qrcode
import io
import base64
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
    
    if not data or 'name' not in data or 'interface' not in data or 'email' not in data:
        return jsonify({"error": "Nome, email e interface são obrigatórios"}), 400
    
    client_dns = data.get('client_dns', '8.8.8.8')  # DNS opcional, padrão 8.8.8.8
    group_id = data.get('group_id')  # Grupo opcional
    
    # Validar group_id se fornecido
    if group_id is not None:
        try:
            group_id = int(group_id)
        except (ValueError, TypeError):
            return jsonify({"error": "ID do grupo deve ser um número válido"}), 400
    
    service = WireGuardPeerService()
    # Passando o email para o serviço
    result = service.create_peer(
        name=data['name'],
        email=data['email'], 
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

@peers_bp.route('/wireguard/peers/<peer_name>/group', methods=['PUT'])
@jwt_required()
def update_peer_group(peer_name):
    """
    Atualiza ou remove o grupo de um peer
    
    Parâmetros:
    - peer_name: Nome do peer a ser atualizado
    
    Corpo da requisição (JSON):
    {
        "group_id": 1  // ID do grupo ou null para remover do grupo atual
    }
    
    Retorna:
    - 200: Grupo atualizado com sucesso
    - 400: Requisição inválida
    - 404: Peer não encontrado
    - 500: Erro interno do servidor
    """
    data = request.get_json(silent=True) or {}
    
    if 'group_id' not in data:
        return jsonify({
            "success": False,
            "error": "O campo 'group_id' é obrigatório. Use null para remover o peer de todos os grupos."
        }), 400
    
    try:
        # Permite group_id ser None (para remoção) ou um número inteiro
        group_id = None if data['group_id'] is None else int(data['group_id'])
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "O ID do grupo deve ser um número inteiro válido ou null"
        }), 400
    
    try:
        service = WireGuardPeerService()
        result = service.update_peer_group(peer_name=peer_name, group_id=group_id)
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": result.get('message', 'Grupo atualizado com sucesso'),
                "peer": result.get('peer')
            }), 200
        else:
            status_code = 404 if 'não encontrado' in result.get('error', '').lower() else 400
            return jsonify({
                "success": False,
                "error": result.get('error', 'Erro ao atualizar o grupo do peer')
            }), status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Erro interno ao processar a requisição: {str(e)}"
        }), 500
    
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
