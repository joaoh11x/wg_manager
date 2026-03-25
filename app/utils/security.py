# app/utils/security.py
from passlib.context import CryptContext

# Configuração do contexto de hash de senha.
# pbkdf2_sha256 não possui o limite de 72 bytes do bcrypt.
# bcrypt fica como fallback para verificar hashes antigos, se existirem.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Gera um hash seguro para a senha.
    """
    if password is None:
        raise TypeError("password cannot be None")

    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto puro corresponde ao hash armazenado.
    """
    if plain_password is None:
        return False

    return pwd_context.verify(plain_password, hashed_password)