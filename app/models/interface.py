from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base  # Base comum para todos os modelos

class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    listen_port = Column(Integer, nullable=False)

    # Relacionamento com a tabela de peers
    peers = relationship("Peer", back_populates="interface")