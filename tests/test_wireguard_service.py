from app.services.wireguard_service import WireGuardService


class _FakeMikroTikAPI:
    def __init__(self):
        self.created = []

    def create_interface(self, name, listen_port):
        self.created.append((name, listen_port))


def test_create_interface():
    from app.utils.database import DatabaseConnection
    from app.models.base import Base
    from app.models.interface import Interface

    fake_api = _FakeMikroTikAPI()
    db = DatabaseConnection(":memory:")
    Base.metadata.create_all(bind=db.engine)

    service = WireGuardService(mikrotik_api=fake_api, db=db)
    service.create_interface("wg0", 51820)

    assert fake_api.created == [("wg0", 51820)]

    session = service.session()
    try:
        iface = session.query(Interface).filter_by(name="wg0").first()
        assert iface is not None
        assert iface.listen_port == 51820
    finally:
        session.close()