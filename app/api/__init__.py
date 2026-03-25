import os

from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.extensions import jwt
from app.utils.database import apply_sqlite_migrations


def create_app():
    # Root do repositório (…/wg_manager)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
        static_url_path="/static",
    )

    # Carrega configurações centralizadas
    app.config.from_object(Config)

    frontend_origin = app.config.get("FRONTEND_ORIGIN", "http://localhost:3000")
    CORS(
        app,
        resources={
            r"/*": {
                "origins": [frontend_origin],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "Cache-Control",
                    "X-Requested-With",
                ],
                "expose_headers": ["Content-Type"],
                "supports_credentials": True,
                "max_age": 3600,
            }
        },
    )

    # Inicializa JWT (antes estava no main.py)
    jwt.init_app(app)

    # Migrações simples de SQLite (adiciona colunas se faltarem)
    apply_sqlite_migrations()

    # Registra blueprints
    from . import (
        peers,
        interfaces,
        traffic,
        auth,
        ip_addresses,
        firewall,
        acl,
        nat,
        wireguard_peers,
        groups,
        profile,
        system,
        me,
    )

    from app.web import web_bp

    app.register_blueprint(peers.peers_bp)
    app.register_blueprint(interfaces.interfaces_bp)
    app.register_blueprint(traffic.traffic_bp)
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(ip_addresses.ip_bp)
    app.register_blueprint(firewall.firewall_bp)
    app.register_blueprint(acl.acl_bp)
    app.register_blueprint(nat.nat_bp)
    app.register_blueprint(wireguard_peers.peers_bp)
    app.register_blueprint(groups.groups_bp)
    app.register_blueprint(profile.profile_bp)
    app.register_blueprint(system.system_bp)
    app.register_blueprint(me.me_bp)
    app.register_blueprint(web_bp)

    return app