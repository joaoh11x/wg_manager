from flask import Flask

def create_app():
    """
    Cria e configura uma instância do Flask.
    """
    app = Flask(__name__)

    # Registra as rotas da API
    from . import peers, interfaces, traffic  # Importa os Blueprints
    app.register_blueprint(peers.peers_bp)
    app.register_blueprint(interfaces.interfaces_bp)
    app.register_blueprint(traffic.traffic_bp)

    return app