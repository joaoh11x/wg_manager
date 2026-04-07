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
    cpf = Column(String, nullable=True, unique=True)
    interface_id = Column(Integer, ForeignKey("interfaces.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)

    interface = relationship("Interface", back_populates="peers", lazy="select")
    group = relationship("Group", back_populates="peers", lazy="select")
    user = relationship("User", backref="peer", uselist=False, lazy="select")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'public_key': self.public_key,
            'ip_address': self.ip_address,
            'cpf': self.cpf,
            'interface_id': self.interface_id,
            'interface_name': self.interface.name if self.interface else None,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'role': getattr(self.user, 'role', 'peer'),
                'is_limited': getattr(self.user, 'is_limited', True)
            } if self.user else None
        }