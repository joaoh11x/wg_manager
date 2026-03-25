from flask import Blueprint, request, jsonify

from app.utils.authz import admin_required
from app.services.group_service import GroupService

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/groups', methods=['POST'])
@admin_required
def create_group():
    """Cria um novo grupo"""
    data = request.json
    
    if not data or 'name' not in data:
        return jsonify({"error": "Nome do grupo é obrigatório"}), 400

    # Validar nome como string não vazia
    raw_name = data.get('name')
    if not isinstance(raw_name, str):
        return jsonify({"error": "Nome do grupo deve ser um texto"}), 400
    name = raw_name.strip()
    if not name:
        return jsonify({"error": "Nome do grupo não pode ser vazio"}), 400

    # description pode vir como null (None) do front-end; tratar com segurança
    raw_description = data.get('description')
    if isinstance(raw_description, str):
        description = raw_description.strip() or None
    else:
        description = None
    
    service = GroupService()
    result = service.create_group(name=name, description=description)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/groups', methods=['GET'])
@admin_required
def list_groups():
    """Lista todos os grupos"""
    service = GroupService()
    result = service.list_groups()
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 500

@groups_bp.route('/groups/<int:group_id>', methods=['GET'])
@admin_required
def get_group(group_id):
    """Obtém detalhes de um grupo específico"""
    service = GroupService()
    result = service.get_group(group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 404

@groups_bp.route('/groups/<int:group_id>', methods=['PUT'])
@admin_required
def update_group(group_id):
    """Atualiza um grupo existente"""
    data = request.json
    
    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400
    
    name = data.get('name')
    description = data.get('description')
    
    if name is not None:
        if not isinstance(name, str):
            return jsonify({"error": "Nome do grupo deve ser um texto"}), 400
        name = name.strip()
        if not name:
            return jsonify({"error": "Nome do grupo não pode ser vazio"}), 400

    if description is not None and not isinstance(description, str):
        description = None
    elif isinstance(description, str):
        description = description.strip() or None
    
    service = GroupService()
    result = service.update_group(group_id, name=name, description=description)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@admin_required
def delete_group(group_id):
    """Remove um grupo"""
    service = GroupService()
    result = service.delete_group(group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400

@groups_bp.route('/groups/<int:group_id>/peers', methods=['GET'])
@admin_required
def get_group_peers(group_id):
    """Lista todos os peers de um grupo"""
    service = GroupService()
    result = service.get_peers_by_group(group_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 500

@groups_bp.route('/peers/<int:peer_id>/group', methods=['PUT'])
@admin_required
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
@admin_required
def remove_peer_from_group(peer_id):
    """Remove um peer do grupo atual"""
    service = GroupService()
    result = service.assign_peer_to_group(peer_id, None)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({"error": result['error']}), 400
