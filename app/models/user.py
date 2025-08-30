from datetime import datetime
from sqlalchemy import Column, Integer, String, LargeBinary, DateTime
from sqlalchemy.orm import relationship
from .base import Base
from ..utils.security import verify_password, get_password_hash
from ..utils.avatar_utils import get_default_avatar

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password = Column(String, nullable=False)
    avatar = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, username: str, password: str, email: str = None, avatar: bytes = None):
        self.username = username
        self.email = email or f"{username}@example.com"
        self.password = self.get_password_hash(password)
        self.avatar = avatar or get_default_avatar()
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def verify_password(self, password: str) -> bool:
        return verify_password(password, self.password)
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        return get_password_hash(password)
