from app.utils.database import DatabaseConnection
from app.models.group import Group
from app.models.peer import Peer
from app.models.interface import Interface  # Importar interface também
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

class GroupService:
    def __init__(self):
        self.db = DatabaseConnection()
        self.session = sessionmaker(bind=self.db.engine)

    def create_group(self, name, description=None):
        """Cria um novo grupo"""
        session = self.session()
        try:
            # Verificar se o grupo já existe
            existing_group = session.query(Group).filter_by(name=name).first()
            if existing_group:
                return {
                    'success': False,
                    'error': f'Grupo com nome "{name}" já existe'
                }

            # Criar novo grupo
            new_group = Group(
                name=name,
                description=description
            )
            
            session.add(new_group)
            session.commit()
            
            return {
                'success': True,
                'group': new_group.to_dict(),
                'message': f'Grupo "{name}" criado com sucesso'
            }
            
        except IntegrityError:
            session.rollback()
            return {
                'success': False,
                'error': 'Erro de integridade: grupo já existe ou nome inválido'
            }
        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

    def list_groups(self):
        """Lista todos os grupos"""
        session = self.session()
        try:
            groups = session.query(Group).all()
            return {
                'success': True,
                'groups': [group.to_dict() for group in groups],
                'count': len(groups)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'groups': [],
                'count': 0
            }
        finally:
            session.close()

    def get_group(self, group_id):
        """Obtém um grupo específico pelo ID"""
        session = self.session()
        try:
            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                return {
                    'success': False,
                    'error': 'Grupo não encontrado'
                }
            
            # Obter peers do grupo
            peers = session.query(Peer).filter_by(group_id=group_id).all()
            group_data = group.to_dict()
            group_data['peers'] = [peer.to_dict() for peer in peers]
            
            return {
                'success': True,
                'group': group_data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

    def update_group(self, group_id, name=None, description=None):
        """Atualiza um grupo existente"""
        session = self.session()
        try:
            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                return {
                    'success': False,
                    'error': 'Grupo não encontrado'
                }

            # Verificar se o novo nome já existe (se fornecido)
            if name and name != group.name:
                existing = session.query(Group).filter_by(name=name).first()
                if existing:
                    return {
                        'success': False,
                        'error': f'Grupo com nome "{name}" já existe'
                    }
                group.name = name

            if description is not None:
                group.description = description

            session.commit()
            
            return {
                'success': True,
                'group': group.to_dict(),
                'message': f'Grupo atualizado com sucesso'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

    def delete_group(self, group_id):
        """Remove um grupo (apenas se não tiver peers vinculados)"""
        session = self.session()
        try:
            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                return {
                    'success': False,
                    'error': 'Grupo não encontrado'
                }

            # Verificar se há peers vinculados ao grupo
            peers_count = session.query(Peer).filter_by(group_id=group_id).count()
            if peers_count > 0:
                return {
                    'success': False,
                    'error': f'Não é possível remover o grupo. Existem {peers_count} peer(s) vinculado(s). Mova os peers para outro grupo primeiro.'
                }

            session.delete(group)
            session.commit()
            
            return {
                'success': True,
                'message': f'Grupo "{group.name}" removido com sucesso'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

    def assign_peer_to_group(self, peer_id, group_id):
        """Vincula um peer a um grupo"""
        session = self.session()
        try:
            # Verificar se o peer existe
            peer = session.query(Peer).filter_by(id=peer_id).first()
            if not peer:
                return {
                    'success': False,
                    'error': 'Peer não encontrado'
                }

            # Verificar se o grupo existe (se group_id não for None)
            if group_id is not None:
                group = session.query(Group).filter_by(id=group_id).first()
                if not group:
                    return {
                        'success': False,
                        'error': 'Grupo não encontrado'
                    }

            # Atualizar o peer
            peer.group_id = group_id
            session.commit()
            
            group_name = group.name if group_id else None
            return {
                'success': True,
                'message': f'Peer "{peer.name}" {"vinculado ao grupo " + group_name if group_name else "removido do grupo"}',
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

    def get_peers_by_group(self, group_id):
        """Lista todos os peers de um grupo específico"""
        session = self.session()
        try:
            peers = session.query(Peer).filter_by(group_id=group_id).all()
            return {
                'success': True,
                'peers': [peer.to_dict() for peer in peers],
                'count': len(peers)
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
