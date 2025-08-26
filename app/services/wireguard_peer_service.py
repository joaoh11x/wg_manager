import re
from ipaddress import ip_network, ip_address
from cryptography.hazmat.primitives.asymmetric import x25519
import base64
import os
from cryptography.hazmat.primitives import serialization
from app.utils.mikrotik_api import MikroTikAPI
from app.utils.database import DatabaseConnection
from app.models.interface import Interface
from app.models.group import Group
from app.models.peer import Peer
from sqlalchemy.orm import sessionmaker

class WireGuardPeerService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()
        self.db = DatabaseConnection()
        self.session = sessionmaker(bind=self.db.engine)

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
    
        # Verificação para validação das chaves
        if (len(private_key_b64) != 44 or 
            len(public_key_b64) != 44 or
            not private_key_b64.endswith('=') or
            not public_key_b64.endswith('=')):
            raise ValueError("Formato de chave inválido gerado")
        
        # Verifica se a chave não é uma sequência repetitiva
        if private_key_b64 == 'A' * 44:
            raise ValueError("Chave privada inválida gerada")
    
        return {
            'private': private_key_b64,
            'public': public_key_b64
        }

    def _get_next_available_ip(self, network, interface_name):
        # 1. Obter IP do servidor (da própria interface WireGuard)
        interface_ips = self.mikrotik_api.get_interface_ips(interface_name)
        if not interface_ips:
            raise ValueError(f"Interface {interface_name} não possui IP configurado")

        server_ip = ip_address(interface_ips[0]['address'].split('/')[0])

        # 2. Obter IPs usados pelos peers
        used_ips = [
            ip_address(peer['allowed-address'].split('/')[0])
            for peer in self.mikrotik_api.list_wireguard_peers()
            if peer.get('allowed-address')
        ]

        # 3. Procurar próximo IP disponível
        for host in network.hosts():
            if (host not in used_ips and 
                host != network.network_address and
                host != server_ip):
                return f"{host}/32"

        raise ValueError("Não há IPs disponíveis na rede")

    def create_peer(self, name, interface_name, client_dns="8.8.8.8", group_id=None):
        """Cria um novo peer WireGuard"""
        try:
            # 1. Gerar chaves
            keys = self._generate_valid_keypair()

            # 2. Obter rede e IP disponível
            network = self._get_interface_network(interface_name)
            peer_ip = self._get_next_available_ip(network, interface_name)

            # 3. Obter o IP do MikroTik e a porta da interface
            mikrotik_ip = os.getenv("MIKROTIK_HOST")
            listen_port = self.mikrotik_api.get_wireguard_interface_port(interface_name)

            # 4. Criar peer no MikroTik
            self.mikrotik_api.create_wireguard_peer_safe(
                name=name,
                interface=interface_name,
                public_key=keys['public'],
                private_key=keys['private'],
                allowed_address=peer_ip,
                endpoint=mikrotik_ip,
                listen_port=listen_port,
                client_address=peer_ip.split('/')[0],
                client_dns=client_dns,
                responder=True
            )

            # 5. Atualizar o peer com a chave privada (etapa adicional)
            self._update_peer_private_key(name, interface_name, keys['private'])

            # 6. Se um group_id foi fornecido, salvar essa informação no banco de dados
            if group_id is not None:
                self._save_peer_group_info(name, interface_name, group_id)

            return {
                'success': True,
                'peer_name': name,
                'interface': interface_name,
                'peer_ip': peer_ip,
                'private_key': keys['private'],
                'public_key': keys['public'],
                'endpoint': f"{mikrotik_ip}:{listen_port}",
                'group_id': group_id
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _update_peer_private_key(self, peer_name, interface_name, private_key):
        """Atualiza a chave privada do peer após criação"""
        peers = self.mikrotik_api.api.get_resource('/interface/wireguard/peers')
        peer = peers.get(name=peer_name, interface=interface_name)

        if not peer:
            raise ValueError("Peer não encontrado para atualização")

        peers.set(id=peer[0]['id'], private_key=private_key)
        
    def _save_peer_group_info(self, peer_name, interface_name, group_id):
        """Salva informações do grupo do peer no banco de dados"""
        session = self.session()
        try:
            # Verificar se o peer já existe no banco
            existing_peer = session.query(Peer).filter_by(name=peer_name).first()
            
            if existing_peer:
                # Atualizar grupo do peer existente
                existing_peer.group_id = group_id
            else:
                # Obter informações do peer do MikroTik para criar registro no banco
                raw_peers = self.mikrotik_api.list_wireguard_peers()
                peer_data = next((p for p in raw_peers if p.get('name') == peer_name), None)
                
                if peer_data:
                    # Criar novo registro no banco de dados
                    new_peer = Peer(
                        name=peer_name,
                        email=f"{peer_name}@temp.local",  # Email temporário
                        public_key=peer_data.get('public-key', ''),
                        ip_address=peer_data.get('allowed-address', '').split('/')[0],
                        group_id=group_id
                    )
                    session.add(new_peer)
            
            session.commit()
        except Exception as e:
            session.rollback()
            # Não falhar a criação do peer se houve problema ao salvar o grupo
            print(f"Aviso: Não foi possível salvar informações do grupo: {e}")
        finally:
            session.close()
        
    def list_peers(self, interface_name=None):
        """Lista todos os peers WireGuard ou filtra por interface"""
        try:
            # Obter todos os peers do MikroTik
            raw_peers = self.mikrotik_api.list_wireguard_peers()

            # Filtrar por interface se especificado
            if interface_name:
                raw_peers = [peer for peer in raw_peers if peer.get('interface') == interface_name]

            # Formatar os dados de retorno
            formatted_peers = []
            for peer in raw_peers:
                formatted_peer = {
                    'name': peer.get('name', ''),
                    'interface': peer.get('interface', ''),
                    'public_key': peer.get('public-key', ''),
                    'private-key': peer.get('private-key', ''),
                    'allowed_address': peer.get('allowed-address', ''),
                    'endpoint': f"{peer.get('endpoint-address', '')}:{peer.get('endpoint-port', '')}" 
                               if peer.get('endpoint-address') else '',
                    'last_handshake': peer.get('last-handshake', ''),
                    'rx': peer.get('rx', ''),
                    'tx': peer.get('tx', ''),
                    'persistent_keepalive': peer.get('persistent-keepalive', ''),
                    'enabled': peer.get('disabled', 'false') == 'false'  # MikroTik usa 'disabled', invertemos para 'enabled'
                }
                formatted_peers.append(formatted_peer)

            return {
                'success': True,
                'peers': formatted_peers,
                'count': len(formatted_peers)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'peers': [],
                'count': 0
            }
    
    def delete_peer(self, peer_name):
        """Remove um peer WireGuard pelo nome"""
        try:
            # Verificar se o peer existe
            peers = self.mikrotik_api.list_wireguard_peers()
            peer_exists = any(peer.get('name') == peer_name for peer in peers)
            
            if not peer_exists:
                raise ValueError(f"Peer {peer_name} não encontrado")
                
            # Remover o peer
            self.mikrotik_api.delete_wireguard_peer(peer_name)
            
            return {
                'success': True,
                'message': f"Peer {peer_name} removido com sucesso"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def toggle_peer_status(self, peer_name, enabled):
        """Ativa ou desativa um peer WireGuard"""
        try:
            peers_resource = self.mikrotik_api.api.get_resource('/interface/wireguard/peers')
            peer = peers_resource.get(name=peer_name)
            
            if not peer:
                raise ValueError(f"Peer {peer_name} não encontrado")
            
            # MikroTik usa 'disabled' (true/false), então invertemos
            disabled_value = 'false' if enabled else 'true'
            peers_resource.set(id=peer[0]['id'], disabled=disabled_value)
            
            return {
                'success': True,
                'message': f"Peer {peer_name} {'ativado' if enabled else 'desativado'} com sucesso",
                'enabled': enabled
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }