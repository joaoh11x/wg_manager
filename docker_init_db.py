import os
import secrets

from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.utils.database import DatabaseConnection


def init_db_if_missing(db_path: str = "database.db") -> None:
    if os.path.exists(db_path):
        return

    db = DatabaseConnection(db_path)
    Base.metadata.create_all(bind=db.engine)

    Session = sessionmaker(bind=db.engine)
    session = Session()
    try:
        admin_password = os.getenv("ADMIN_PASSWORD")
        generated_password = False
        if not admin_password:
            admin_password = secrets.token_urlsafe(18)
            generated_password = True

        admin = User(
            username="admin",
            password=admin_password,
            avatar=None,
            role="admin",
            is_limited=False,
        )
        session.add(admin)
        session.commit()

        print("✅ Database initialized successfully!")
        print("👤 Admin user created with username: admin")
        if generated_password:
            print("⚠️  Generated ADMIN_PASSWORD (save it now):")
            print(admin_password)
        else:
            print("🔑 Admin password set via ADMIN_PASSWORD env var")
    finally:
        session.close()


if __name__ == "__main__":
    init_db_if_missing(os.getenv("DB_PATH", "database.db"))
