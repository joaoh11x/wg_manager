from app.utils.mikrotik_api import MikroTikAPI

class ConfigService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def add_ip_to_interface(self, address, interface, comment=""):
        """Adiciona um IP a uma interface"""
        try:
            self.mikrotik_api.create_ip_address(address, interface, comment)
            return {"success": True, "message": f"IP {address} adicionado à {interface}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_ips(self):
        """Lista todos os IPs configurados"""
        try:
            ips = self.mikrotik_api.list_ip_addresses()
            return {"success": True, "data": ips}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_ip(self, ip_id):
        """Remove um IP pelo ID"""
        try:
            self.mikrotik_api.delete_ip_address(ip_id)
            return {"success": True, "message": "IP removido"}
        except Exception as e:
            return {"success": False, "error": str(e)}