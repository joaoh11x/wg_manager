import sys
import os
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

# Carrega as variáveis de ambiente
load_dotenv()

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import create_app

app = create_app()

# Configuração do JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))

# Inicializa o JWTManager
jwt = JWTManager(app)

if __name__ == "__main__":
    app.run(debug=True)