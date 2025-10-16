from app.utils.mikrotik_api import MikroTikAPI
from app.utils.database import DatabaseConnection
from app.models.interface import Interface
from sqlalchemy.orm import sessionmaker

class WireGuardService:
    def __init__(self):
        self.mikrotik_api = MikroTikAPI()
        self.db = DatabaseConnection()
        self.session = sessionmaker(bind=self.db.engine)

    def create_interface(self, name, listen_port):
        """
        Cria uma interface WireGuard no MikroTik e a salva no banco de dados.
        """
        session = self.session()
        try:
            # 1. Criar a interface no MikroTik
            self.mikrotik_api.create_interface(name, listen_port)

            # 2. Salvar a interface no banco de dados
            new_interface = Interface(name=name, listen_port=listen_port)
            session.add(new_interface)
            session.commit()

        except Exception as e:
            session.rollback()
            raise Exception(f"Erro ao criar interface: {e}")
        finally:
            session.close()
        
    def delete_interface(self, name):
        """
        Deleta uma interface WireGuard no MikroTik e no banco de dados.
        """
        session = self.session()
        try:
            # 1. Deletar a interface no MikroTik
            self.mikrotik_api.delete_interface(name)

            # 2. Deletar a interface no banco de dados
            interface_to_delete = session.query(Interface).filter_by(name=name).first()
            if interface_to_delete:
                session.delete(interface_to_delete)
                session.commit()

        except Exception as e:
            session.rollback()
            raise Exception(f"Erro ao deletar interface: {e}")
        finally:
            session.close()
    
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
        Atualiza uma interface WireGuard no MikroTik e no banco de dados.
        """
        session = self.session()
        try:
            # 1. Atualizar no MikroTik
            self.mikrotik_api.update_interface(name, listen_port, new_name)

            # 2. Atualizar no banco de dados
            interface_to_update = session.query(Interface).filter_by(name=name).first()
            if interface_to_update:
                interface_to_update.name = new_name
                interface_to_update.listen_port = listen_port
                session.commit()

        except Exception as e:
            session.rollback()
            raise Exception(f"Erro ao atualizar interface: {e}")
        finally:
            session.close()

    def enable_interface(self, name):
        """
        Habilita uma interface WireGuard no MikroTik.
        """
        try:
            return self.mikrotik_api.enable_interface(name)
        except Exception as e:
            raise Exception(f"Erro ao habilitar interface: {str(e)}")
            
    def disable_interface(self, name):
        """        
        Desabilita uma interface WireGuard no MikroTik.
        """
        try:
            return self.mikrotik_api.disable_interface(name)
        except Exception as e:
            raise Exception(f"Erro ao desabilitar interface: {str(e)}")

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