import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from app.models.base import Base
from app.models.user import User
from app.models.peer import Peer 
from app.models.group import Group
from app.models.interface import Interface
from app.utils.database import DatabaseConnection

# Database path
DB_PATH = "database.db"

def init_db():
    # Remove existing database if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # Create database and tables
    db = DatabaseConnection(DB_PATH)
    Base.metadata.create_all(bind=db.engine)
    
    # Create a session
    Session = sessionmaker(bind=db.engine)
    session = Session()
    
    try:
        # Create admin user
        admin = User(
            username="admin",
            password="senha_segura",
            avatar=None,
            role='admin',
            is_limited=False,
        )
        session.add(admin)
        session.commit()
        print("✅ Database initialized successfully!")
        print(f"👤 Admin user created with username: admin")
        print(f"🔑 Password: senha_segura")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Initializing database...")
    init_db()
