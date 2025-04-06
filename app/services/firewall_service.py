from app.utils.mikrotik_api import MikroTikAPI

class FirewallService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def create_wireguard_allow_rule(self, port, network=None):
        """Cria regras para liberar tráfego WireGuard"""
        try:
            # Regra para permitir porta WireGuard (UDP)
            self.mikrotik_api.create_firewall_rule(
                chain='input',
                action='accept',
                protocol='udp',
                dst_port=port,
                comment="Permite Entrada WireGuard"
            )
            
            # Regra para permitir tráfego da rede WireGuard
            if network:
                self.mikrotik_api.create_firewall_rule(
                    chain='input',
                    action='accept',
                    src_address=network,
                    comment="Permite tráfego de rede WireGuard"
                )
            
            return {"status": "success", "message": "Regras criadas com sucesso"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_rules(self):
        """Lista todas as regras de firewall"""
        try:
            rules = self.mikrotik_api.list_firewall_rules()
            return {"status": "success", "data": rules}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_rule(self, rule_id):
        """Remove uma regra específica"""
        try:
            self.mikrotik_api.delete_firewall_rule(rule_id)
            return {"status": "success", "message": "Regra removida"}
        except Exception as e:
            return {"status": "error", "message": str(e)}