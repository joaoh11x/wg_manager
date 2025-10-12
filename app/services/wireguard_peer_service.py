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
from app.models.user import User


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

        # Validações simples — base64 de 32 bytes vira 44 chars com padding "==".
        if len(private_key_b64) != 44 or len(public_key_b64) != 44:
            raise ValueError("Formato de chave inválido gerado")

        # Evita chaves triviais
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

        # 3. Procurar próximo IP disponível (hosts() já pula network & broadcast)
        for host in network.hosts():
            if (host not in used_ips and host != server_ip):
                return f"{host}/32"

        raise ValueError("Não há IPs disponíveis na rede")

    def create_peer(self, name, email, interface_name, client_dns="8.8.8.8", group_id=None):
        """Cria um novo peer WireGuard"""
        session = self.session()
        try:
            # 1. Verificar se a interface existe no banco de dados
            interface = session.query(Interface).filter_by(name=interface_name).first()
            if not interface:
                raise ValueError(f"Interface '{interface_name}' não encontrada no banco de dados.")

            # 2. Gerar chaves
            keys = self._generate_valid_keypair()

            # 3. Obter rede e IP disponível
            network = self._get_interface_network(interface_name)
            peer_ip = self._get_next_available_ip(network, interface_name)

            # 4. Obter o IP do MikroTik e a porta da interface
            mikrotik_ip = os.getenv("MIKROTIK_HOST")
            listen_port = self.mikrotik_api.get_wireguard_interface_port(interface_name)

            # 5. Criar peer no MikroTik
            # Observação: assumo que create_wireguard_peer_safe aceita esses parâmetros
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

            # 6. Salvar o peer no banco de dados e criar usuário associado (tentativa de sincronização)
            try:
                # Cria ou atualiza Peer
                peer_record = self._save_peer_to_db(
                    session,
                    name=name,
                    email=email,
                    public_key=keys['public'],
                    ip_address=peer_ip.split('/')[0],
                    interface_id=interface.id,
                    group_id=group_id
                )

                # Criar usuário vinculado ao Peer se não existir
                # Regras: username baseado no nome do peer; email do peer; senha randômica simples gerada
                existing_user = None
                if peer_record and getattr(peer_record, 'user_id', None):
                    existing_user = session.query(User).filter_by(id=peer_record.user_id).first()

                if not existing_user:
                    base_username = name.strip().lower().replace(' ', '.')
                    candidate = base_username or f"peer{peer_record.id if peer_record else ''}"
                    username = candidate
                    suffix = 1
                    while session.query(User).filter_by(username=username).first() is not None:
                        suffix += 1
                        username = f"{candidate}{suffix}"

                    # senha inicial
                    import secrets
                    import string
                    alphabet = string.ascii_letters + string.digits
                    raw_password = ''.join(secrets.choice(alphabet) for _ in range(10))

                    user = User(
                        username=username,
                        password=raw_password,
                        email=email,
                        display_name=name,
                        role='peer',
                        is_limited=True,
                    )
                    session.add(user)
                    session.flush()  # obtém user.id

                    # vincular
                    if peer_record:
                        peer_record.user_id = user.id
                        session.add(peer_record)

                    session.commit()
                    created_user_credentials = {
                        'username': username,
                        'password': raw_password,
                        'role': 'peer',
                        'is_limited': True,
                        'user_id': user.id,
                    }
                else:
                    created_user_credentials = None
            except Exception as db_exc:
                # Não interromper a criação no MikroTik se o DB falhar — informar no retorno.
                return {
                    'success': False,
                    'error': f"Peer criado no MikroTik, mas falha ao salvar no banco: {db_exc}"
                }

            # 7. Atualizar o peer com a chave privada (etapa adicional se necessário)
            try:
                self._update_peer_private_key(name, interface_name, keys['private'])
            except Exception:
                # Não falhar o fluxo só por conta da atualização opcional da chave
                pass

            return {
                'success': True,
                'peer_name': name,
                'interface': interface_name,
                'peer_ip': peer_ip,
                'private_key': keys['private'],
                'public_key': keys['public'],
                'endpoint': f"{mikrotik_ip}:{listen_port}",
                'group_id': group_id,
                'user': created_user_credentials
            }

        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

    def _update_peer_private_key(self, peer_name, interface_name, private_key):
        """Atualiza a chave privada do peer após criação"""
        peers_resource = self.mikrotik_api.api.get_resource('/interface/wireguard/peers')
        found = peers_resource.get(name=peer_name, interface=interface_name)

        if not found:
            raise ValueError("Peer não encontrado para atualização")

        peers_resource.set(id=found[0]['id'], private_key=private_key)

    def _save_peer_to_db(self, session, name, email, public_key, ip_address, interface_id, group_id):
        
        try:
            # 1) Tentar encontrar por nome
            existing_peer = session.query(Peer).filter_by(name=name).first()

            # 2) Se não encontrou por nome, tentar casar por public_key/ip vindo do MikroTik
            if not existing_peer:
                raw_peers = self.mikrotik_api.list_wireguard_peers()
                peer_data = next((p for p in raw_peers if p.get('name') == name), None)

                # se não houver peer_data, ainda assim tentamos por public_key/ip passados
                public_from_mk = peer_data.get('public-key') if peer_data else None
                ip_from_mk = (peer_data.get('allowed-address', '').split('/')[0]
                              if peer_data and peer_data.get('allowed-address') else None)

                # tentar por public_key (prioridade)
                if public_key:
                    existing_peer = session.query(Peer).filter_by(public_key=public_key).first()

                # tentar por public_from_mk caso public_key não tenha achado
                if not existing_peer and public_from_mk:
                    existing_peer = session.query(Peer).filter_by(public_key=public_from_mk).first()

                # tentar por ip_address
                if not existing_peer and (ip_address or ip_from_mk):
                    search_ip = ip_address or ip_from_mk
                    existing_peer = session.query(Peer).filter_by(ip_address=search_ip).first()

            # 3) Se existente, atualizar campos
            if existing_peer:
                existing_peer.name = name
                existing_peer.email = email
                existing_peer.public_key = public_key or existing_peer.public_key
                existing_peer.ip_address = ip_address or existing_peer.ip_address
                existing_peer.interface_id = interface_id
                existing_peer.group_id = group_id
                session.add(existing_peer)
                peer_obj = existing_peer
            else:
                # 4) Criar novo registro
                new_peer = Peer(
                    name=name,
                    email=email,
                    public_key=public_key or '',
                    ip_address=ip_address or '',
                    interface_id=interface_id,
                    group_id=group_id
                )
                session.add(new_peer)
                peer_obj = new_peer

            session.commit()
            return peer_obj
        except Exception as e:
            session.rollback()
            # Log de aviso e repassa a exceção para o chamador decidir
            print(f"Aviso: Não foi possível salvar o peer no banco de dados: {e}")
            raise

    def list_peers(self, interface_name=None):
        """Lista todos os peers WireGuard ou filtra por interface"""
        session = self.session()
        try:
            # Obter todos os peers do MikroTik
            raw_peers = self.mikrotik_api.list_wireguard_peers()

            # Filtrar por interface se especificado
            if interface_name:
                raw_peers = [peer for peer in raw_peers if peer.get('interface') == interface_name]

            # Obter informações do nosso banco de dados
            peer_names = [p.get('name') for p in raw_peers if p.get('name')]
            db_peers = {}
            if peer_names:
                db_peers = {p.name: p for p in session.query(Peer).filter(Peer.name.in_(peer_names)).all()}

            # Formatar os dados de retorno
            formatted_peers = []
            for peer in raw_peers:
                peer_name = peer.get('name', '')
                db_peer_info = db_peers.get(peer_name)

                formatted_peer = {
                    'name': peer_name,
                    'interface': peer.get('interface', ''),
                    'public_key': peer.get('public-key', ''),
                    'email': db_peer_info.email if db_peer_info else None,
                    'group': {
                        'id': db_peer_info.group_id,
                        'name': db_peer_info.group.name if db_peer_info and db_peer_info.group else None
                    } if db_peer_info else None,
                    'private-key': peer.get('private-key', ''),
                    'allowed_address': peer.get('allowed-address', ''),
                    'client_dns': peer.get('client-dns', ''),
                    'endpoint': f"{peer.get('endpoint-address', '')}:{peer.get('endpoint-port', '')}"
                               if peer.get('endpoint-address') else '',
                    'last_handshake': peer.get('last-handshake', ''),
                    'rx': peer.get('rx', ''),
                    'tx': peer.get('tx', ''),
                    'persistent_keepalive': peer.get('persistent-keepalive', ''),
                    'enabled': peer.get('disabled', 'false') == 'false'
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
        finally:
            session.close()

    def delete_peer(self, peer_name):
        """Remove um peer WireGuard pelo nome"""
        session = self.session()
        try:
            # Verificar se o peer existe
            peers = self.mikrotik_api.list_wireguard_peers()
            peer_exists = any(peer.get('name') == peer_name for peer in peers)

            if not peer_exists:
                raise ValueError(f"Peer {peer_name} não encontrado")

            # Remover o peer do MikroTik
            self.mikrotik_api.delete_wireguard_peer(peer_name)

            # Remover o peer do banco de dados se existir
            peer = session.query(Peer).filter_by(name=peer_name).first()
            if peer:
                # Remover usuário vinculado, se houver
                try:
                    if getattr(peer, 'user_id', None):
                        from app.models.user import User
                        user = session.query(User).filter_by(id=peer.user_id).first()
                        if user:
                            session.delete(user)
                    session.delete(peer)
                    session.commit()
                except Exception:
                    session.rollback()
                    # Tenta ao menos remover o peer se falhou a remoção do usuário
                    session.delete(peer)
                    session.commit()

            return {
                'success': True,
                'message': f"Peer {peer_name} removido com sucesso"
            }

        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

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

    def update_peer_group(self, peer_name, group_id):
        """Atualiza o grupo de um peer"""
        session = self.session()
        try:
            # 1) Tentar encontrar por nome
            peer = session.query(Peer).filter_by(name=peer_name).first()

            # 2) Se não houver, buscar dados no MikroTik e tentar casar por chaves únicas
            peer_data = None
            if not peer:
                raw_peers = self.mikrotik_api.list_wireguard_peers()
                peer_data = next((p for p in raw_peers if p.get('name') == peer_name), None)
                if not peer_data:
                    raise ValueError(f"Peer {peer_name} não encontrado no MikroTik")

                public_key = peer_data.get('public-key')
                ip_addr = peer_data.get('allowed-address', '').split('/')[0] if peer_data.get('allowed-address') else None

                if public_key:
                    peer = session.query(Peer).filter_by(public_key=public_key).first()

                if not peer and ip_addr:
                    peer = session.query(Peer).filter_by(ip_address=ip_addr).first()

                # 3) Se ainda não existir no banco, criar novo registro
                if not peer:
                    # Evitar criar registros sem nenhum identificador único
                    if not public_key and not ip_addr:
                        raise ValueError(
                            "Não foi possível obter public_key ou ip_address do peer no MikroTik para sincronizar com o banco de dados"
                        )
                    peer = Peer(
                        name=peer_name,
                        email=f"{peer_name}@temp.local",
                        public_key=public_key or '',
                        ip_address=ip_addr or '',
                    )
                    session.add(peer)

            # Se group_id for None, remove o grupo atual
            if group_id is None:
                peer.group_id = None
            else:
                # Verificar se o grupo existe
                group = session.query(Group).filter_by(id=group_id).first()
                if not group:
                    raise ValueError(f"Grupo com ID {group_id} não encontrado")
                peer.group_id = group_id

            session.commit()

            session.refresh(peer)

            return {
                'success': True,
                'message': f"Grupo do peer {peer_name} atualizado com sucesso",
                'peer': peer.to_dict()
            }

        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            session.close()
