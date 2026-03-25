from flask import Blueprint, request, jsonify

from app.utils.authz import admin_required
from app.services.firewall_service import FirewallService

firewall_bp = Blueprint('firewall', __name__)

@firewall_bp.route('/firewall/wireguard', methods=['POST'])
@admin_required
def create_wireguard_rules():
    """Cria regras para tráfego WireGuard"""
    data = request.json
    
    # Validação básica
    if not data or 'port' not in data:
        return jsonify({"error": "Porta WireGuard é obrigatória"}), 400
    
    service = FirewallService()
    result = service.create_wireguard_allow_rule(
        port=data['port'],
        network=data.get('network')
    )
    
    status_code = 201 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@firewall_bp.route('/firewall/rules', methods=['GET'])
@admin_required
def list_firewall_rules():
    """Lista todas as regras de firewall"""
    service = FirewallService()
    result = service.list_rules()
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@firewall_bp.route('/firewall/rules/<string:rule_id>', methods=['DELETE'])
@admin_required
def delete_firewall_rule(rule_id):
    """Remove uma regra de firewall"""
    service = FirewallService()
    result = service.delete_rule(rule_id)
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code