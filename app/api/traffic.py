from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

# Cria um Blueprint para as rotas de tráfego
traffic_bp = Blueprint("traffic", __name__)

@traffic_bp.route("/traffic", methods=["GET"])
@jwt_required()
def get_traffic():
    return jsonify({"message": "Dados de tráfego"})