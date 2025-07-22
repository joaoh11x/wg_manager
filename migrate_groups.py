"""
Script de migração para adicionar grupos aos peers
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.database import DatabaseConnection
from app.models.base import Base
# Import all models to ensure they are registered
from app.models.interface import Interface
from app.models.group import Group
from app.models.peer import Peer
from sqlalchemy import text

def migrate_database():
    """Executa a migração do banco de dados para adicionar suporte a grupos"""
    db = DatabaseConnection()
    
    try:
        print("Iniciando migração do banco de dados...")
        
        # Criar todas as tabelas (incluindo a nova tabela groups)
        Base.metadata.create_all(db.engine)
        print("✓ Tabelas criadas/atualizadas")
        
        # Verificar se a coluna group_id já existe na tabela peers
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(peers)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'group_id' not in columns:
                # Adicionar a coluna group_id na tabela peers
                conn.execute(text("ALTER TABLE peers ADD COLUMN group_id INTEGER"))
                print("✓ Coluna group_id adicionada à tabela peers")
            else:
                print("✓ Coluna group_id já existe na tabela peers")
        
        # Criar alguns grupos padrão
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=db.engine)
        session = Session()
        
        try:
            # Verificar se já existem grupos
            existing_groups = session.query(Group).count()
            
            if existing_groups == 0:
                default_groups = [
                    {"name": "RH", "description": "Departamento de Recursos Humanos"},
                    {"name": "Suporte", "description": "Equipe de Suporte Técnico"},
                    {"name": "Infra", "description": "Equipe de Infraestrutura"},
                    {"name": "Desenvolvimento", "description": "Equipe de Desenvolvimento"},
                    {"name": "Vendas", "description": "Departamento de Vendas"},
                    {"name": "Administração", "description": "Departamento Administrativo"}
                ]
                
                for group_data in default_groups:
                    group = Group(name=group_data["name"], description=group_data["description"])
                    session.add(group)
                
                session.commit()
                print("✓ Grupos padrão criados")
            else:
                print("✓ Grupos já existem no banco de dados")
                
        except Exception as e:
            session.rollback()
            print(f"Erro ao criar grupos padrão: {e}")
        finally:
            session.close()
        
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        return False
    
    return True

if __name__ == "__main__":
    migrate_database()
