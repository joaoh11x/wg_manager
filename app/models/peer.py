from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base  # Base comum para todos os modelos

class Peer(Base):
    __tablename__ = "peers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    public_key = Column(String, nullable=False, unique=True)
    ip_address = Column(String, nullable=False, unique=True)
    interface_id = Column(Integer, ForeignKey("interfaces.id"))

    interface = relationship("Interface", back_populates="peers")