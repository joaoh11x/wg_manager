from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.utils.database import DatabaseConnection
from app.utils.avatar_utils import process_avatar, avatar_to_base64, get_default_avatar

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
        
        # Use default avatar if user doesn't have one
        avatar_data = user.avatar if user.avatar else get_default_avatar()
        
        response_data = {
            "username": user.display_name or user.username,
            "email": getattr(user, 'email', f"{user.username}@example.com"),
            "avatar": avatar_to_base64(avatar_data),
            "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@profile_bp.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile (display_name, email, etc.)
    Note: username (login) cannot be changed, only display_name
    """
    current_username = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    db = DatabaseConnection()
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        user = session.query(User).filter_by(username=current_username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update display_name if provided (this is what the frontend sends as 'username')
        if 'username' in data:
            new_display_name = data['username'].strip()
            if not new_display_name:
                return jsonify({"error": "Display name cannot be empty"}), 400
            
            user.display_name = new_display_name
        
        # Update email if provided
        if 'email' in data:
            new_email = data['email'].strip()
            if new_email:
                # Check if email is already taken by another user
                existing_user = session.query(User).filter_by(email=new_email).first()
                if existing_user and existing_user.id != user.id:
                    return jsonify({"error": "Email already taken"}), 409
                
                user.email = new_email
        
        session.commit()
        
        # Use default avatar if user doesn't have one
        avatar_data = user.avatar if user.avatar else get_default_avatar()
        
        return jsonify({
            "message": "Profile updated successfully",
            "username": user.display_name or user.username,
            "email": user.email,
            "avatar": avatar_to_base64(avatar_data)
        }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
