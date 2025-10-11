import os
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
    SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET_KEY", "change-me"))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
    )

    # CORS
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")