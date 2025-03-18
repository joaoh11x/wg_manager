import sqlite3
from app.utils.security import hash_password

# Conecta ao banco de dados
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Busca todos os usuários
cursor.execute("SELECT id, username, password FROM users")
users = cursor.fetchall()

# Atualiza as senhas para hashes seguros
for user in users:
    user_id, username, password = user
    if not password.startswith("$2b$"):  # Verifica se a senha não está criptografada
        hashed_password = hash_password(password)
        cursor.execute("""
        UPDATE users
        SET password = ?
        WHERE id = ?
        """, (hashed_password, user_id))

# Salva as alterações
conn.commit()
conn.close()