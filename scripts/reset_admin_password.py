import os
import secrets

from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.utils.database import DatabaseConnection


def reset_admin_password(db_path: str, new_password: str) -> None:
    db = DatabaseConnection(db_path)
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
    db_path = os.getenv("DB_PATH", "database.db")

    new_password = os.getenv("NEW_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
    if not new_password:
        new_password = secrets.token_urlsafe(18)
        print("⚠️  NEW_ADMIN_PASSWORD/ADMIN_PASSWORD not provided.")
        print("⚠️  Generated a new admin password (save it now):")
        print(new_password)

    reset_admin_password(db_path=db_path, new_password=new_password)
    print("✅ Admin password updated for user: admin")
