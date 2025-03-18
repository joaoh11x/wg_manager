import sqlite3

def get_db_connection():
    """
    Retorna uma conexão com o banco de dados SQLite.
    """
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # Retorna resultados como dicionários
    return conn