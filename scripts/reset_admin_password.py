import os
import secrets
import sys
from pathlib import Path

from sqlalchemy.orm import sessionmaker

# Allow running this script directly: ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.user import User
from app.utils.database import DatabaseConnection


def reset_admin_password(database_url: str, new_password: str) -> None:
    db = DatabaseConnection(database_url)
    Session = sessionmaker(bind=db.engine)
    session = Session()

    try:
        admin = session.query(User).filter_by(username="admin").first()
        if admin is None:
            admin = User(
                username="admin",
                password=new_password,
                avatar=None,
                role="admin",
                is_limited=False,
                must_change_password=False,
            )
            session.add(admin)
        else:
            admin.password = User.get_password_hash(new_password)
            admin.role = getattr(admin, "role", "admin") or "admin"
            admin.is_limited = bool(getattr(admin, "is_limited", False))
            admin.must_change_password = False

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URI")
    if not database_url:
        raise SystemExit(
            "DATABASE_URL não configurada. Ex.: postgresql+psycopg://user:pass@localhost:5432/wireguard_manager"
        )

    new_password = os.getenv("NEW_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    if not new_password:
        new_password = secrets.token_urlsafe(18)
        print("⚠️  NEW_ADMIN_PASSWORD/ADMIN_PASSWORD not provided.")
        print("⚠️  Generated a new admin password (save it now):")
        print(new_password)

    reset_admin_password(database_url=database_url, new_password=new_password)
    print("✅ Admin password updated for user: admin")
