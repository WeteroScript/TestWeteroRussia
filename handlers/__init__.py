# handlers/__init__.py

from .handlers import register_handlers
from .admin import register_admin_handlers
from .business import register_business_handlers
from .user import register_user_handlers

__all__ = [
    'register_handlers',
    'register_admin_handlers', 
    'register_business_handlers',
    'register_user_handlers'
]
