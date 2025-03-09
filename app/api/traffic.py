from flask import Blueprint, jsonify

# Cria um Blueprint para as rotas de tráfego
traffic_bp = Blueprint("traffic", __name__)

@traffic_bp.route("/traffic", methods=["GET"])
def get_traffic():
    return jsonify({"message": "Dados de tráfego"})