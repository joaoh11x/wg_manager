import os
import sys
import secrets
from getpass import getpass
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
        env_password = os.getenv("ADMIN_PASSWORD")
        if env_password:
            admin_password = env_password
        else:
            pw1 = getpass("Enter admin password (leave blank to auto-generate): ")
            if not pw1:
                admin_password = secrets.token_urlsafe(18)
                print("⚠️  Generated admin password (save it now):")
                print(admin_password)
            else:
                pw2 = getpass("Confirm admin password: ")
                if pw1 != pw2:
                    raise ValueError("Passwords do not match")
                admin_password = pw1

        admin = User(
            username="admin",
            password=admin_password,
            avatar=None,
            role='admin',
            is_limited=False,
        )
        session.add(admin)
        session.commit()
        print("✅ Database initialized successfully!")
        print(f"👤 Admin user created with username: admin")
        if env_password:
            print("🔑 Admin password set via ADMIN_PASSWORD env var")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Initializing database...")
    init_db()
