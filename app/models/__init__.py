# Import all models to ensure they are registered with SQLAlchemy
from app.models.base import Base
from app.models.interface import Interface
from app.models.group import Group
from app.models.peer import Peer
from app.models.user import User

# Make sure all models are available when importing from models
__all__ = ['Base', 'Interface', 'Group', 'Peer', 'User']