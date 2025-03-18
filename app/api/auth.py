from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.utils.security import verify_password
from app.utils.database import get_db_connection

# Cria um Blueprint para as rotas de autenticação
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Autentica um usuário e retorna um token JWT.
    """
    data = request.json

    # Valida os dados recebidos
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400

    username = data["username"]
    password = data["password"]

    # Busca o usuário no banco de dados
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    # Verifica se o usuário existe e a senha está correta
    if user and verify_password(password, user["password"]):
        # Gera um token JWT
        access_token = create_access_token(identity=username)
        return jsonify({"access_token": access_token}), 200
    else:
        return jsonify({"error": "Usuário ou senha inválidos"}), 401