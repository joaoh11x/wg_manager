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