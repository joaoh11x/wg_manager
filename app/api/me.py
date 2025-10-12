from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy.orm import sessionmaker

from app.utils.database import DatabaseConnection
from app.models.user import User
from app.models.peer import Peer
from app.services.wireguard_peer_service import WireGuardPeerService
import secrets
import string


me_bp = Blueprint('me', __name__)


def _get_db_session():
    db = DatabaseConnection()
    Session = sessionmaker(bind=db.engine)
    return Session()


@me_bp.route('/me', methods=['GET'])
@jwt_required()
def me_info():
    identity = get_jwt_identity()
    claims = get_jwt()

    session = _get_db_session()
    try:
        user = session.query(User).filter_by(id=int(identity)).first()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        peer = session.query(Peer).filter_by(user_id=user.id).first()

        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': getattr(user, 'role', 'peer'),
                'is_limited': getattr(user, 'is_limited', False),
            },
            'peer': peer.to_dict() if peer else None,
        }), 200
    finally:
        session.close()


@me_bp.route('/me/config', methods=['GET'])
@jwt_required()
def me_config():
    identity = get_jwt_identity()

    session = _get_db_session()
    try:
        user = session.query(User).filter_by(id=int(identity)).first()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        peer = session.query(Peer).filter_by(user_id=user.id).first()
        if not peer:
            return jsonify({"error": "Nenhum peer vinculado a este usuário"}), 404

        # Reutiliza o serviço existente para compor a configuração
        service = WireGuardPeerService()
        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter informações do peer"}), 500

        peer_info = next((p for p in peers_result['peers'] if p['name'] == peer.name), None)
        if not peer_info:
            return jsonify({"error": "Peer não encontrado"}), 404

        interface_name = peer_info['interface']
        mikrotik_ip = service.mikrotik_api.get_mikrotik_ip()
        listen_port = service.mikrotik_api.get_wireguard_interface_port(interface_name)
        server_public_key = service.mikrotik_api.get_wireguard_interface_public_key(interface_name)

        client_dns = peer_info.get('client_dns') or '8.8.8.8'
        config = f"""[Interface]
PrivateKey = {peer_info['private-key']}
Address = {peer_info['allowed_address']}
DNS = {client_dns}

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {mikrotik_ip}:{listen_port}
PersistentKeepalive = 25"""

        return jsonify({
            'success': True,
            'config': config,
            'peer_name': peer.name
        }), 200
    finally:
        session.close()


@me_bp.route('/me/qrcode', methods=['GET'])
@jwt_required()
def me_qrcode():
    # Reutiliza o endpoint existente indiretamente via serviço
    service = WireGuardPeerService()

    identity = get_jwt_identity()
    session = _get_db_session()
    try:
        user = session.query(User).filter_by(id=int(identity)).first()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        peer = session.query(Peer).filter_by(user_id=user.id).first()
        if not peer:
            return jsonify({"error": "Nenhum peer vinculado a este usuário"}), 404

        # Obter informações do peer
        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter informações do peer"}), 500

        peer_info = next((p for p in peers_result['peers'] if p['name'] == peer.name), None)
        if not peer_info:
            return jsonify({"error": "Peer não encontrado"}), 404

        interface_name = peer_info['interface']
        mikrotik_ip = service.mikrotik_api.get_mikrotik_ip()
        listen_port = service.mikrotik_api.get_wireguard_interface_port(interface_name)
        server_public_key = service.mikrotik_api.get_wireguard_interface_public_key(interface_name)

        client_dns = peer_info.get('client_dns') or '8.8.8.8'
        config = f"""[Interface]
PrivateKey = {peer_info['private-key']}
Address = {peer_info['allowed_address']}
DNS = {client_dns}

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {mikrotik_ip}:{listen_port}
PersistentKeepalive = 25"""

        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(config)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")

        img_buffer = io.BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

        return jsonify({
            'success': True,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'peer_name': peer.name
        }), 200
    finally:
        session.close()


@me_bp.route('/me/traffic', methods=['GET'])
@jwt_required()
def me_traffic():
    service = WireGuardPeerService()

    identity = get_jwt_identity()
    session = _get_db_session()
    try:
        user = session.query(User).filter_by(id=int(identity)).first()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        peer = session.query(Peer).filter_by(user_id=user.id).first()
        if not peer:
            return jsonify({"error": "Nenhum peer vinculado a este usuário"}), 404

        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter dados de tráfego"}), 500

        p = next((x for x in peers_result['peers'] if x['name'] == peer.name), None)
        if not p:
            return jsonify({"error": "Peer não encontrado"}), 404

        return jsonify({
            'success': True,
            'peer_name': peer.name,
            'last_handshake': p.get('last_handshake'),
            'rx': p.get('rx'),
            'tx': p.get('tx'),
        }), 200
    finally:
        session.close()


@me_bp.route('/me/config/download', methods=['GET'])
@jwt_required()
def me_config_download():
    service = WireGuardPeerService()

    identity = get_jwt_identity()
    session = _get_db_session()
    try:
        user = session.query(User).filter_by(id=int(identity)).first()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        peer = session.query(Peer).filter_by(user_id=user.id).first()
        if not peer:
            return jsonify({"error": "Nenhum peer vinculado a este usuário"}), 404

        peers_result = service.list_peers()
        if not peers_result['success']:
            return jsonify({"error": "Erro ao obter informações do peer"}), 500

        peer_info = next((p for p in peers_result['peers'] if p['name'] == peer.name), None)
        if not peer_info:
            return jsonify({"error": "Peer não encontrado"}), 404

        interface_name = peer_info['interface']
        mikrotik_ip = service.mikrotik_api.get_mikrotik_ip()
        listen_port = service.mikrotik_api.get_wireguard_interface_port(interface_name)
        server_public_key = service.mikrotik_api.get_wireguard_interface_public_key(interface_name)

        client_dns = peer_info.get('client_dns') or '8.8.8.8'
        config = f"""[Interface]
PrivateKey = {peer_info['private-key']}
Address = {peer_info['allowed_address']}
DNS = {client_dns}

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {mikrotik_ip}:{listen_port}
PersistentKeepalive = 25"""

        import io

        config_file = io.BytesIO()
        config_file.write(config.encode('utf-8'))
        config_file.seek(0)

        return send_file(
            config_file,
            as_attachment=True,
            download_name=f"{peer.name}.conf",
            mimetype='text/plain'
        )
    finally:
        session.close()


@me_bp.route('/me/password/reset', methods=['POST'])
@jwt_required()
def me_password_reset():
    """
    Reseta a senha do usuário autenticado, gerando uma nova senha aleatória.
    Não exige a senha antiga.

    Retorna username e a nova senha em claro para o usuário salvar.
    """
    identity = get_jwt_identity()
    session = _get_db_session()
    try:
        user = session.query(User).filter_by(id=int(identity)).first()
        if not user:
            return jsonify({"success": False, "error": "Usuário não encontrado"}), 404

        # Gera nova senha aleatória
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(10))

        # Atualiza senha (hash)
        user.password = User.get_password_hash(new_password)
        session.add(user)
        session.commit()

        return jsonify({
            "success": True,
            "message": "Senha alterada com sucesso",
            "credentials": {
                "username": user.username,
                "password": new_password
            }
        }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()
