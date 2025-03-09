import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)