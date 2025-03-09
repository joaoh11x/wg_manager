from app.services.wireguard_service import WireGuardService

def test_create_interface():
    service = WireGuardService()
    service.create_interface("wg0", 51820)
    # Adicione asserções para verificar o resultado