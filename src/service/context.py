import threading
from typing import Optional
from contextvars import ContextVar

# Create context variable to store current user ID
current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)

class UserContext:
    """User context manager"""
    
    @staticmethod
    def set_user_id(user_id: str):
        """Set current user ID"""
        current_user_id.set(user_id)
    
    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get current user ID"""
        return current_user_id.get()
    
    @staticmethod
    def clear():
        """Clear current user ID"""
        current_user_id.set(None)

class UserContextManager:
    """User context manager for use with 'with' statement"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.token = None
    
    def __enter__(self):
        self.token = current_user_id.set(self.user_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            current_user_id.reset(self.token) 