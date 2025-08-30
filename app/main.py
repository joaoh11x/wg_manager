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

# Configuração CORS para permitir todas as origens e cabeçalhos necessários
CORS(app, 
     resources={
         r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type"],
             "supports_credentials": True,
             "max_age": 3600
         }
     })

def init_db():
    # Initialize database connection
    db = DatabaseConnection()
    
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
                admin_password = os.getenv("ADMIN_PASSWORD")
                if not admin_password or len(admin_password) < 12:
                    print(" Error: ADMIN_PASSWORD must be set in .env and have at least 12 characters.")
                    raise ValueError("ADMIN_PASSWORD must be set and strong.")
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    password=admin_password
                )
                session.add(admin)
                print(" Admin user created successfully!")
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