import sqlite3
from sqlalchemy import create_engine
import os

def get_db_connection():
    """
    Retorna uma conexão com o banco de dados SQLite.
    """
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # Retorna resultados como dicionários
    return conn

class DatabaseConnection:
    """
    Classe para gerenciar conexões SQLAlchemy com o banco de dados.
    """
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    def get_engine(self):
        """Retorna o engine SQLAlchemy"""
        return self.engine


def apply_sqlite_migrations(db_path: str = "database.db"):

    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # users: role (TEXT), is_limited (INTEGER/BOOLEAN)
        cur.execute("PRAGMA table_info(users)")
        user_cols = {row[1] for row in cur.fetchall()}  # colname at index 1
        if 'role' not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'peer'")
        if 'is_limited' not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN is_limited INTEGER NOT NULL DEFAULT 0")

        # peers: user_id (INTEGER UNIQUE)
        cur.execute("PRAGMA table_info(peers)")
        peer_cols = {row[1] for row in cur.fetchall()}
        if 'user_id' not in peer_cols:
            try:
                cur.execute("ALTER TABLE peers ADD COLUMN user_id INTEGER UNIQUE")
            except sqlite3.OperationalError:
                # Older SQLite may not support adding UNIQUE via ALTER; fallback to non-unique
                cur.execute("ALTER TABLE peers ADD COLUMN user_id INTEGER")

        conn.commit()
    finally:
        conn.close()