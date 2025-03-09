import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

class Config:
    MIKROTIK_HOST = os.getenv("MIKROTIK_HOST")
    MIKROTIK_USER = os.getenv("MIKROTIK_USER")
    MIKROTIK_PASS = os.getenv("MIKROTIK_PASS")
    MIKROTIK_DATABASE = os.getenv("DATABASE_URI")