from sqlalchemy import Column, Integer, String, LargeBinary
from sqlalchemy.orm import relationship
from .base import Base
from ..utils.security import verify_password, get_password_hash

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    avatar = Column(LargeBinary, nullable=True)
    
    def verify_password(self, password: str) -> bool:
        return verify_password(password, self.password)
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return get_password_hash(password)
