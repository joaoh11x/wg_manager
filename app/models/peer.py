from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base 

class Peer(Base):
    __tablename__ = "peers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    public_key = Column(String, nullable=False, unique=True)
    ip_address = Column(String, nullable=False, unique=True)
    interface_id = Column(Integer, ForeignKey("interfaces.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

    interface = relationship("Interface", back_populates="peers", lazy="select")
    group = relationship("Group", back_populates="peers", lazy="select")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'public_key': self.public_key,
            'ip_address': self.ip_address,
            'interface_id': self.interface_id,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None
        }