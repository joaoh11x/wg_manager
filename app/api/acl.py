from flask import Blueprint, request, jsonify

from app.utils.authz import admin_required
from app.services.acl_service import ACLService

"""ACL - Access Control List"""
acl_bp = Blueprint('acl', __name__)

@acl_bp.route('/acl/vpn-lan', methods=['POST'])
@admin_required
def create_vpn_lan_rules():
    """Cria regras de forward entre VPN e LAN"""
    data = request.json
    
    # Validação
    if not data or 'vpn_network' not in data or 'lan_network' not in data:
        return jsonify({
            "error": "Parâmetros 'vpn_network' e 'lan_network' são obrigatórios"
        }), 400
    
    service = ACLService()
    result = service.create_vpn_lan_rules(
        vpn_network=data['vpn_network'],
        lan_network=data['lan_network']
    )
    
    status_code = 201 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@acl_bp.route('/acl/forward-rules', methods=['GET'])
@admin_required
def list_forward_rules():
    """Lista regras de forward"""
    service = ACLService()
    result = service.list_forward_rules()
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code