import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do .env
load_dotenv()


class Config:
    # Integrações
    MIKROTIK_HOST = os.getenv("MIKROTIK_HOST")
    MIKROTIK_USER = os.getenv("MIKROTIK_USER")
    MIKROTIK_PASS = os.getenv("MIKROTIK_PASS")
    MIKROTIK_DATABASE = os.getenv("DATABASE_URI")

    # Flask/JWT
    _env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "").lower()
    _is_production = _env in {"prod", "production"}

    _provided_secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY")
    if not _provided_secret and _is_production:
        raise RuntimeError("Missing SECRET_KEY/JWT_SECRET_KEY in production environment")

    # In non-production environments, avoid an insecure constant fallback.
    SECRET_KEY = _provided_secret or secrets.token_urlsafe(32)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
    )

    # CORS
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")