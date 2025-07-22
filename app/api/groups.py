from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.group_service import GroupService

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/groups', methods=['POST'])
@jwt_required()
def create_group():
    """Cria um novo grupo"""
    data = request.json
    
    if not data or 'name' not in data:
        return jsonify({"error": "Nome do grupo é obrigatório"}), 400
    
    name = data['name'].strip()
    if not name:
        return jsonify({"error": "Nome do grupo não pode ser vazio"}), 400
    
    description = data.get('description', '').strip() or None
    
    service = GroupService()
    result = service.create_group(name=name, description=description)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/groups', methods=['GET'])
@jwt_required()
def list_groups():
    """Lista todos os grupos"""
    service = GroupService()
    result = service.list_groups()
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 500

@groups_bp.route('/groups/<int:group_id>', methods=['GET'])
@jwt_required()
def get_group(group_id):
    """Obtém detalhes de um grupo específico"""
    service = GroupService()
    result = service.get_group(group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 404

@groups_bp.route('/groups/<int:group_id>', methods=['PUT'])
@jwt_required()
def update_group(group_id):
    """Atualiza um grupo existente"""
    data = request.json
    
    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400
    
    name = data.get('name')
    description = data.get('description')
    
    # Validar nome se fornecido
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"error": "Nome do grupo não pode ser vazio"}), 400
    
    service = GroupService()
    result = service.update_group(group_id, name=name, description=description)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@jwt_required()
def delete_group(group_id):
    """Remove um grupo"""
    service = GroupService()
    result = service.delete_group(group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/groups/<int:group_id>/peers', methods=['GET'])
@jwt_required()
def get_group_peers(group_id):
    """Lista todos os peers de um grupo"""
    service = GroupService()
    result = service.get_peers_by_group(group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 500

@groups_bp.route('/peers/<int:peer_id>/group', methods=['PUT'])
@jwt_required()
def assign_peer_to_group(peer_id):
    """Vincula um peer a um grupo ou remove a vinculação"""
    data = request.json
    
    if data is None:
        return jsonify({"error": "Dados não fornecidos"}), 400
    
    # group_id pode ser None para remover vinculação
    group_id = data.get('group_id')
    
    service = GroupService()
    result = service.assign_peer_to_group(peer_id, group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/peers/<int:peer_id>/group', methods=['DELETE'])
@jwt_required()
def remove_peer_from_group(peer_id):
    """Remove um peer do grupo atual"""
    service = GroupService()
    result = service.assign_peer_to_group(peer_id, None)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400
