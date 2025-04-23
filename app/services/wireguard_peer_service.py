import re
from ipaddress import ip_network, ip_address
from cryptography.hazmat.primitives.asymmetric import x25519
import base64
import os
from cryptography.hazmat.primitives import serialization
from app.utils.mikrotik_api import MikroTikAPI

class WireGuardPeerService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()

    def _get_interface_network(self, interface_name):
        """Obtém a rede configurada na interface"""
        ips = self.mikrotik_api.get_interface_ips(interface_name)
        if not ips:
            raise ValueError(f"Interface {interface_name} não possui IP configurado")
        
        interface_ip = ips[0]['address']
        return ip_network(interface_ip, strict=False)

    def _generate_valid_keypair(self):
        """Gera chaves no formato que o MikroTik aceita"""
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        private_key_b64 = base64.b64encode(private_key_bytes).decode('ascii')
        public_key_b64 = base64.b64encode(public_key_bytes).decode('ascii')

        return {
            'private': private_key_b64,
            'public': public_key_b64
        }

    def _get_next_available_ip(self, network):
        """Encontra o próximo IP disponível na rede"""
        used_ips = [
            ip_address(peer['allowed-address'].split('/')[0])
            for peer in self.mikrotik_api.list_wireguard_peers()
            if peer.get('allowed-address')
        ]
        
        for host in network.hosts():
            if host not in used_ips and host != network.network_address:
                return f"{host}/{network.prefixlen}"
        raise ValueError("Não há IPs disponíveis na rede")

    def create_peer(self, name, interface_name, client_dns="8.8.8.8"):
        """Cria um novo peer WireGuard"""
        try:
            # 1. Gerar chaves
            keys = self._generate_valid_keypair()
    
            # 2. Obter rede e IP disponível
            network = self._get_interface_network(interface_name)
            peer_ip = self._get_next_available_ip(network)
    
            # 3. Obter o IP do MikroTik e a porta da interface
            mikrotik_ip = os.getenv("MIKROTIK_HOST")
            listen_port = self.mikrotik_api.get_wireguard_interface_port(interface_name)
    
            # 4. Criar peer no MikroTik - ATUALIZADO para usar endpoint_address
            self.mikrotik_api.create_wireguard_peer_safe(
                name=name,
                interface=interface_name,
                public_key=keys['public'],
                allowed_address=peer_ip,
                endpoint=mikrotik_ip,  # Será convertido para endpoint_address na API
                listen_port=listen_port,
                client_address=peer_ip.split('/')[0],  # Apenas o IP, sem a máscara
                client_dns=client_dns,
                responder=True
            )
    
            return {
                'success': True,
                'peer_name': name,
                'interface': interface_name,
                'peer_ip': peer_ip,
                'private_key': keys['private'],
                'public_key': keys['public'],
                'endpoint': f"{mikrotik_ip}:{listen_port}",
                'client_config': {
                    'endpoint': f"{mikrotik_ip}:{listen_port}",
                    'keepalive': '25',  # Em segundos para o cliente WireGuard
                    'listen_port': listen_port,
                    'dns': client_dns
                }
            }
    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }