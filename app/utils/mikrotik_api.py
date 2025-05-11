import os
from dotenv import load_dotenv
from routeros_api import RouterOsApiPool

class MikroTikAPI:
    def __init__(self):
        self.connection = RouterOsApiPool(
            host=os.getenv("MIKROTIK_HOST"),  # Endereço IP do MikroTik
            username=os.getenv("MIKROTIK_USER"),  # Nome de usuário do MikroTik
            password=os.getenv("MIKROTIK_PASS"),  # Senha do MikroTik
            plaintext_login=True  # Use False se estiver usando SSL/TLS
        )
        self.api = self.connection.get_api()

    def create_interface(self, name, listen_port):
        """
        Cria uma interface WireGuard no MikroTik.
        """
        try:
            self.api.get_resource("/interface/wireguard").add(
                name=name,
                listen_port=str(listen_port)
            )
        except Exception as e:
            raise Exception(f"Erro ao criar interface: {e}")
        
    
    def delete_interface(self, name):
        """
        Deleta uma interface WireGuard no MikroTik.
        """
        try:
            # Obtém a interface pelo nome
            interfaces = self.api.get_resource("/interface/wireguard")
            interface_list = interfaces.get(name=name)
            
            if interface_list:  # Verifica se a lista não está vazia
                interface = interface_list[0]  # Acessa o primeiro elemento da lista
                # Deleta a interface usando o ID
                interfaces.remove(id=interface["id"])
            else:
                raise Exception(f"Interface '{name}' não encontrada")
        except Exception as e:
            raise Exception(f"Erro ao deletar interface: {e}")
        
    def list_interfaces(self):
        """
        Lista todas as interfaces WireGuard no MikroTik.
        """
        try:
            interfaces = self.api.get_resource("/interface/wireguard")
            return interfaces.get()
        except Exception as e:
            raise Exception(f"Erro ao listar interfaces: {e}")
    
    def update_interface(self, name, listen_port, new_name):
        """
        Atualiza uma interface WireGuard no MikroTik.
        """
        try:
            # Obtém a interface pelo nome
            interfaces = self.api.get_resource("/interface/wireguard")
            interface_list = interfaces.get(name=name)
            
            if interface_list:  # Verifica se a lista não está vazia
                interface = interface_list[0]  # Acessa o primeiro elemento da lista
                # Atualiza a interface usando o ID
                interfaces.set(id=interface["id"], listen_port=str(listen_port), name=new_name)
            else:
                raise Exception(f"Interface '{name}' não encontrada")
        except Exception as e:
            raise Exception(f"Erro ao atualizar interface: {e}")
        
    def create_ip_address(self, address, interface, comment=""):
        """Adiciona um IP a uma interface (IP > Address)"""
        try:
            self.api.get_resource('/ip/address').add(
                address=address,
                interface=interface,
                comment=comment
            )
            return True
        except Exception as e:
            if "already exists" in str(e):
                raise Exception(f"IP {address} já existe na interface {interface}")
            raise Exception(f"Falha ao adicionar IP: {e}")
    
    def list_ip_addresses(self):
        """Lista todos os IPs configurados"""
        try:
            return self.api.get_resource('/ip/address').get()
        except Exception as e:
            raise Exception(f"Erro ao listar IPs: {e}")
    
    def delete_ip_address(self, ip_id):
        """Remove um IP pelo ID"""
        try:
            self.api.get_resource('/ip/address').remove(id=ip_id)
            return True
        except Exception as e:
            raise Exception(f"Erro ao remover IP: {e}")
        
    def create_firewall_rule(self, chain, action, protocol=None, dst_port=None, src_address=None, comment=""):
        """Cria uma regra de firewall"""
        try:
            params = {
                'chain': chain,
                'action': action,
                'comment': comment
            }
            
            if protocol:
                params['protocol'] = protocol
            if dst_port:
                params['dst-port'] = str(dst_port)
            if src_address:
                params['src-address'] = src_address
                
            self.api.get_resource('/ip/firewall/filter').add(**params)
            return True
        except Exception as e:
            raise Exception(f"Erro ao criar regra: {e}")
    
    def list_firewall_rules(self):
        """Lista todas as regras de firewall"""
        try:
            return self.api.get_resource('/ip/firewall/filter').get()
        except Exception as e:
            raise Exception(f"Erro ao listar regras: {e}")
    
    def delete_firewall_rule(self, rule_id):
        """Remove uma regra pelo ID"""
        try:
            self.api.get_resource('/ip/firewall/filter').remove(id=rule_id)
            return True
        except Exception as e:
            raise Exception(f"Erro ao deletar regra: {e}")
        
    def create_forward_rule(self, src_address, dst_address, action='accept', comment=""):
        """Cria regra de forward entre redes"""
        try:
            self.api.get_resource('/ip/firewall/filter').add(
                chain='forward',
                src_address=src_address,
                dst_address=dst_address,
                action=action,
                comment=comment
            )
            return True
        except Exception as e:
            raise Exception(f"Erro ao criar regra de forward: {e}")
    
    def get_forward_rules(self):
        """Lista todas as regras de forward"""
        try:
            return self.api.get_resource('/ip/firewall/filter').get(chain='forward')
        except Exception as e:
            raise Exception(f"Erro ao listar regras de forward: {e}")
        
    def create_nat_rule(self, chain, src_address=None, action='masquerade', comment=""):
        """Cria regra NAT"""
        try:
            params = {
                'chain': chain,
                'action': action,
                'comment': comment
            }
            if src_address:
                params['src-address'] = src_address

            self.api.get_resource('/ip/firewall/nat').add(**params)
            return True
        except Exception as e:
            raise Exception(f"Erro ao criar regra NAT: {e}")

    def list_nat_rules(self):
        """Lista todas as regras NAT"""
        try:
            return self.api.get_resource('/ip/firewall/nat').get()
        except Exception as e:
            raise Exception(f"Erro ao listar regras NAT: {e}")

    def delete_nat_rule(self, rule_id):
        """Remove uma regra NAT pelo ID"""
        try:
            self.api.get_resource('/ip/firewall/nat').remove(id=rule_id)
            return True
        except Exception as e:
            raise Exception(f"Erro ao remover regra NAT: {e}")
        
    def get_interface_ips(self, interface_name):
        """Lista IPs de uma interface específica"""
        return self.api.get_resource('/ip/address').get(interface=interface_name)

    def list_wireguard_peers(self):
        """Lista todos os peers WireGuard"""
        return self.api.get_resource('/interface/wireguard/peers').get()

    def create_wireguard_peer_safe(self, name, interface, public_key, private_key, allowed_address, endpoint, listen_port, client_address, client_dns=None, responder=True):
        """Cria peer com validação extra e configurações adicionais"""
        if not isinstance(public_key, str) or len(public_key) != 44 or not public_key.endswith('='):
            raise ValueError("Chave pública deve ser uma string Base64 de 44 caracteres")
    
        try:
            peer_resource = self.api.get_resource('/interface/wireguard/peers')
            
            peer_params = {
                'name': name,
                'interface': interface,
                'public-key': public_key,
                'private-key': private_key,
                'allowed-address': allowed_address,
                'endpoint-address': endpoint,
                'endpoint-port': str(listen_port),
                'client-address': client_address,
                'client-endpoint': endpoint,
                'client-keepalive': '00:00:05',
                'client-listen-port': str(listen_port),
                'persistent-keepalive': '00:00:05',
                'responder': 'yes' if responder else 'no'
            }
            
            # Adiciona DNS apenas se fornecido
            if client_dns:
                peer_params['client-dns'] = client_dns
                
            # Cria o peer
            peer_resource.add(**peer_params)
    
        except Exception as e:
            if "invalid public key" in str(e).lower():
                raise ValueError("MikroTik rejeitou a chave. Formato incorreto.")
            raise Exception(f"Erro na API: {str(e)}")

    def delete_wireguard_peer(self, peer_name):
        peers = self.api.get_resource('/interface/wireguard/peers')
        peer = peers.get(name=peer_name)
        if peer:
            peers.remove(id=peer[0]['id'])    

    def get_wireguard_interface_port(self, interface_name):
        """Obtém a porta configurada na interface WireGuard"""
        try:
            interfaces = self.api.get_resource('/interface/wireguard').get(name=interface_name)
            if not interfaces:
                raise ValueError(f"Interface {interface_name} não encontrada")
            return interfaces[0].get('listen-port', '13231')  # Porta padrão do WireGuard se não especificada
        except Exception as e:
            raise Exception(f"Erro ao obter porta da interface: {str(e)}")
        
    def get_wireguard_peers_stats(self, interface_name=None):
        """Obtém apenas estatísticas dos peers (mais leve que listar tudo)"""
        peers = self.api.get_resource('/interface/wireguard/peers')
        if interface_name:
            return peers.get(interface=interface_name)
        return peers.get()
    