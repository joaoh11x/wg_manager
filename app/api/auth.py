import base64
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.utils.database import DatabaseConnection
from app.utils.avatar_utils import avatar_to_base64

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
    db = DatabaseConnection()
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        user = session.query(User).filter_by(username=username).first()
        
        # Verifica se o usuário existe e a senha está correta
        if user and user.verify_password(password):
            # Gera um token JWT
            access_token = create_access_token(identity=username)
            
            # Converte o avatar para base64 se existir
            avatar_base64 = None
            if user.avatar:
                avatar_base64 = f"data:image/png;base64,{base64.b64encode(user.avatar).decode('utf-8')}"
            
            return jsonify({
                "access_token": access_token,
                "user": {
                    "username": user.username,
                    "avatar": avatar_base64,
                    "email": user.email if hasattr(user, 'email') else f"{user.username}@example.com"
                }
            }), 200
        else:
            return jsonify({"error": "Usuário ou senha inválidos"}), 401
    finally:
        session.close()