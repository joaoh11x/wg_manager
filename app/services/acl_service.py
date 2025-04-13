from app.utils.mikrotik_api import MikroTikAPI

class ACLService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def create_vpn_lan_rules(self, vpn_network, lan_network):
        """Cria regras bidirecionais VPN-LAN"""
        try:
            # VPN -> LAN
            self.mikrotik_api.create_forward_rule(
                src_address=vpn_network,
                dst_address=lan_network,
                comment="Allow VPN to LAN traffic"
            )
            
            # LAN -> VPN
            self.mikrotik_api.create_forward_rule(
                src_address=lan_network,
                dst_address=vpn_network,
                comment="Allow LAN to VPN traffic"
            )
            
            return {
                "status": "success",
                "message": f"Regras criadas: {vpn_network} ↔ {lan_network}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_forward_rules(self):
        """Lista todas as regras de forward"""
        try:
            rules = self.mikrotik_api.get_forward_rules()
            return {"status": "success", "data": rules}
        except Exception as e:
            return {"status": "error", "message": str(e)}