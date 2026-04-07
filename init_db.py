import os
import sys
import secrets
from getpass import getpass
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

def init_db():
    db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URI")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Ex.: postgresql+psycopg://user:pass@localhost:5432/wireguard_manager"
        )

    # Create database tables (idempotent)
    db = DatabaseConnection(db_url)
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

        admin = session.query(User).filter_by(username="admin").first()
        if admin is None:
            admin = User(
                username="admin",
                password=admin_password,
                avatar=None,
                role='admin',
                is_limited=False,
                must_change_password=False,
            )
            session.add(admin)
            session.commit()
            print("✅ Database initialized successfully!")
            print("👤 Admin user created with username: admin")
        else:
            # Only update password if you explicitly provided/typed one.
            admin.password = User.get_password_hash(admin_password)
            admin.role = "admin"
            admin.is_limited = False
            admin.must_change_password = False
            session.commit()
            print("✅ Database schema ensured; admin user updated")
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
