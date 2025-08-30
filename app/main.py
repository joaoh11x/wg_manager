import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

# Carrega as variáveis de ambiente
load_dotenv()

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import create_app
from app.models.base import Base
from app.models.user import User
from app.models.group import Group
from app.utils.database import DatabaseConnection

# Initialize Flask app
app = create_app()
CORS(app)

def init_db():
    # Initialize database connection
    db = DatabaseConnection()
    
    # Default groups
    default_groups = [
        {"name": "RH", "description": "Departamento de Recursos Humanos"},
        {"name": "Suporte", "description": "Equipe de Suporte Técnico"},
        {"name": "Infra", "description": "Equipe de Infraestrutura"},
        {"name": "Desenvolvimento", "description": "Equipe de Desenvolvimento"},
        {"name": "Vendas", "description": "Departamento de Vendas"},
        {"name": "Administração", "description": "Departamento Administrativo"}
    ]
    
    # Check if tables exist
    inspector = inspect(db.engine)
    if not inspector.has_table('users'):
        print(" Initializing database tables...")
        Base.metadata.create_all(bind=db.engine)
        
        Session = sessionmaker(bind=db.engine)
        session = Session()
        
        try:
            # Create admin user if it doesn't exist
            admin = session.query(User).filter_by(username="admin").first()
            if not admin:
                admin = User(
                    username="admin",
                    password=User.get_password_hash("senha_segura"),
                    avatar=None
                )
                session.add(admin)
                print(" Admin user created successfully!")
            
            # Create default groups if they don't exist
            existing_groups = session.query(Group).count()
            if existing_groups == 0:
                for group_data in default_groups:
                    group = Group(name=group_data["name"], description=group_data["description"])
                    session.add(group)
                print(" Default groups created successfully!")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f" Error initializing database: {e}")
            raise
        finally:
            session.close()

# Configuração do JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))

# Inicializa o JWTManager
jwt = JWTManager(app)

# Initialize database
init_db()

if __name__ == "__main__":
    app.run(debug=True)