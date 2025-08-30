from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.utils.database import DatabaseConnection
from app.utils.avatar_utils import process_avatar, avatar_to_base64

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/api/profile/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """
    Upload or update user's avatar
    """
    if 'avatar' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Validação de tipo e tamanho
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    max_file_size = 2 * 1024 * 1024  # 2MB

    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if file_ext not in allowed_extensions:
        return jsonify({"error": "Tipo de arquivo não permitido. Apenas png, jpg, jpeg, gif."}), 400

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    if file_length > max_file_size:
        return jsonify({"error": "Arquivo muito grande. Máximo permitido: 2MB."}), 400

    # Processa a imagem
    avatar_data = process_avatar(file)
    if not avatar_data:
        return jsonify({"error": "Invalid image file"}), 400
    
    # Get current user
    current_username = get_jwt_identity()
    db = DatabaseConnection()
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        user = session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Update avatar
        user.avatar = avatar_data
        session.commit()
        
        return jsonify({
            "message": "Avatar updated successfully",
            "avatar": avatar_to_base64(avatar_data)
        }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@profile_bp.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get user profile including avatar
    """
    current_username = get_jwt_identity()
    db = DatabaseConnection()
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        user = session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({
            "username": user.username,
            "email": getattr(user, 'email', f"{user.username}@example.com"),
            "avatar": avatar_to_base64(user.avatar) if user.avatar else None,
            "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
