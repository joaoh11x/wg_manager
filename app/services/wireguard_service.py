from app.utils.mikrotik_api import MikroTikAPI

class WireGuardService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def create_interface(self, name, listen_port):
        """
        Cria uma interface WireGuard no MikroTik.
        """
        try:
            self.mikrotik_api.create_interface(name, listen_port)
        except Exception as e:
            raise Exception(f"Erro ao criar interface no MikroTik: {e}")
        
    def delete_interface(self, name):
        """
        Deleta uma interface WireGuard no MikroTik.
        """
        try:
            self.mikrotik_api.delete_interface(name)
        except Exception as e:
            raise Exception(f"Erro ao deletar interface no MikroTik: {e}")
    
    def list_interfaces(self):
        """
        Lista todas as interfaces WireGuard no MikroTik.
        """
        try:
            return self.mikrotik_api.list_interfaces()
        except Exception as e:
            raise Exception(f"Erro ao listar interfaces no MikroTik: {e}")
        
    def update_interface(self, name, listen_port, new_name):
        """
        Atualiza uma interface WireGuard no MikroTik.
        """
        try:
            self.mikrotik_api.update_interface(name, listen_port, new_name)
        except Exception as e:
            raise Exception(f"Erro ao atualizar interface no MikroTik: {e}")

    def get_interface_stats(self, interface_name):
        """
        Retorna estatísticas da interface WireGuard (RX, TX, handshakes dos peers).
        """
        peers = self.mikrotik_api.list_wireguard_peers()
        stats = {
            "interface": interface_name,
            "peers": []
        }
        for peer in peers:
            if peer.get("interface") == interface_name:
                stats["peers"].append({
                    "name": peer.get("name", ""),
                    "public_key": peer.get("public-key", ""),
                    "rx": peer.get("rx", 0),
                    "tx": peer.get("tx", 0),
                    "last_handshake": peer.get("last-handshake", "")
                })
        return stats