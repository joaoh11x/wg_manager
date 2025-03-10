from flask import Blueprint, request, jsonify
from app.services.wireguard_service import WireGuardService

# Cria um Blueprint para as rotas de interfaces
interfaces_bp = Blueprint("interfaces", __name__)

@interfaces_bp.route("/interfaces", methods=["POST"])
def create_interface():
    """
    Rota para criar uma nova interface WireGuard.
    """
    data = request.json

    # Valida os dados recebidos
    if not data or "name" not in data or "listen_port" not in data:
        return jsonify({"error": "Nome e porta são obrigatórios"}), 400

    name = data["name"]
    listen_port = data["listen_port"]

    # Cria a interface usando o serviço
    service = WireGuardService()
    try:
        service.create_interface(name, listen_port)
        return jsonify({"message": f"Interface '{name}' criada com sucesso"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@interfaces_bp.route("/interfaces/<string:name>", methods=["DELETE"])
def delete_interface(name):
    """
    Rota para deletar uma interface WireGuard.
    """
    service = WireGuardService()  # Cria uma instância do serviço
    try:
        service.delete_interface(name)  # Chama o método da instância
        return jsonify({"message": f"Interface '{name}' deletada com sucesso"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@interfaces_bp.route("/interfaces", methods=["GET"])
def list_interfaces():
    """
    Rota para listar todas as interfaces WireGuard.
    """
    service = WireGuardService()
    try:
        interfaces = service.list_interfaces()
        return jsonify(interfaces), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@interfaces_bp.route("/interfaces/<string:name>", methods=["PUT"])
def update_interface(name):
    """
    Rota para atualizar uma interface WireGuard.
    """
    data = request.json

    # Valida os dados recebidos
    if not data or "listen_port" not in data:
        return jsonify({"error": "Porta é obrigatória"}), 400

    listen_port = data["listen_port"]
    new_name = data.get("name", name)

    # Atualiza a interface usando o serviço
    service = WireGuardService()
    try:
        service.update_interface(name, listen_port, new_name)
        return jsonify({"message": f"Interface '{name}' atualizada com sucesso"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
