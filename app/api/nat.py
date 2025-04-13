from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.nat_service import NATService

nat_bp = Blueprint('nat', __name__)

@nat_bp.route('/nat/wireguard', methods=['POST'])
@jwt_required()
def create_wireguard_nat():
    """Cria regra NAT para WireGuard"""
    data = request.json
    
    if not data or 'src_network' not in data:
        return jsonify({"error": "Parâmetro 'src_network' é obrigatório"}), 400
    
    service = NATService()
    result = service.create_wireguard_nat(data['src_network'])
    
    status_code = 201 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@nat_bp.route('/nat/rules', methods=['GET'])
@jwt_required()
def list_nat_rules():
    """Lista todas as regras NAT"""
    service = NATService()
    result = service.list_nat_rules()
    status_code = 200 if result['status'] == 'success' else 500
    return jsonify(result), status_code

@nat_bp.route('/nat/rules/<string:rule_id>', methods=['DELETE'])
@jwt_required()
def delete_nat_rule(rule_id):
    """Remove uma regra NAT"""
    service = NATService()
    result = service.delete_nat_rule(rule_id)
    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code