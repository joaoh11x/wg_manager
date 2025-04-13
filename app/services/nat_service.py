from app.utils.mikrotik_api import MikroTikAPI

class NATService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def create_wireguard_nat(self, src_network):
        """Cria regra de NAT para rede WireGuard"""
        try:
            self.mikrotik_api.create_nat_rule(
                chain='srcnat',
                src_address=src_network,
                action='masquerade',
                comment="WireGuard NAT Rule"
            )
            return {"status": "success", "message": f"Regra NAT criada para {src_network}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_nat_rules(self):
        """Lista todas as regras NAT"""
        try:
            rules = self.mikrotik_api.list_nat_rules()
            return {"status": "success", "data": rules}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_nat_rule(self, rule_id):
        """Remove uma regra NAT"""
        try:
            self.mikrotik_api.delete_nat_rule(rule_id)
            return {"status": "success", "message": "Regra NAT removida"}
        except Exception as e:
            return {"status": "error", "message": str(e)}