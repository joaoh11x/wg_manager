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