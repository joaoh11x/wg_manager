from flask import Flask

def create_app():
    app = Flask(__name__)

    from . import (
        peers,
        interfaces,
        traffic,
        auth,
        ip_addresses,
        firewall,
        acl,
        nat,
        wireguard_peers
    )

    app.register_blueprint(peers.peers_bp)
    app.register_blueprint(interfaces.interfaces_bp)
    app.register_blueprint(traffic.traffic_bp)
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(ip_addresses.ip_bp)
    app.register_blueprint(firewall.firewall_bp)
    app.register_blueprint(acl.acl_bp)
    app.register_blueprint(nat.nat_bp)
    app.register_blueprint(wireguard_peers.peers_bp)

    return app