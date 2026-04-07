import os
import secrets

from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.utils.database import DatabaseConnection


def init_db_if_missing(database_url: str | None = None) -> None:
    db_url = database_url or os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URI")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Ex.: postgresql+psycopg://user:pass@postgres:5432/wireguard_manager"
        )

    db = DatabaseConnection(db_url)
    Base.metadata.create_all(bind=db.engine)

    Session = sessionmaker(bind=db.engine)
    session = Session()
    try:
        admin_password = os.getenv("ADMIN_PASSWORD")
        generated_password = False
        if not admin_password:
            admin_password = secrets.token_urlsafe(18)
            generated_password = True

        admin = session.query(User).filter_by(username="admin").first()
        if admin is None:
            admin = User(
                username="admin",
                password=admin_password,
                avatar=None,
                role="admin",
                is_limited=False,
                must_change_password=False,
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
        else:
            print("✅ Database schema ensured; admin already exists")
    finally:
        session.close()


if __name__ == "__main__":
    init_db_if_missing()
