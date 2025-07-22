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