from typing import Dict, Set
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ToolUsageTracker:
    """Singleton class for tracking user tool usage"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._user_tool_usage: Dict[str, Dict[str, datetime]] = {}
        self._initialized = True
        
        # Tool usage timeout (seconds)
        self.tool_usage_timeout = 300  # 5 minutes
    
    def record_tool_usage(self, user_id: str, tool_name: str):
        """Record user tool usage"""
        if user_id not in self._user_tool_usage:
            self._user_tool_usage[user_id] = {}
        
        self._user_tool_usage[user_id][tool_name] = datetime.now()
        logger.debug(f"Recorded user {user_id} using tool {tool_name}")

    def get_active_tools(self, user_id: str) -> Set[str]:
        """Get tools currently being used by the user"""
        if user_id not in self._user_tool_usage:
            return set()
        
        current_time = datetime.now()
        active_tools = set()
        
        # Clean up expired tool usage records
        expired_tools = []
        for tool_name, last_used in self._user_tool_usage[user_id].items():
            if current_time - last_used <= timedelta(seconds=self.tool_usage_timeout):
                active_tools.add(tool_name)
            else:
                expired_tools.append(tool_name)
        
        # Remove expired records
        for tool_name in expired_tools:
            del self._user_tool_usage[user_id][tool_name]
        
        return active_tools
    
    def is_tool_active(self, user_id: str, tool_name: str) -> bool:
        """Check if user is currently using the specified tool"""
        active_tools = self.get_active_tools(user_id)
        return tool_name in active_tools
    
    def clear_user_tools(self, user_id: str):
        """Clear all tool usage records for the user"""
        if user_id in self._user_tool_usage:
            del self._user_tool_usage[user_id]
    
    def cleanup_expired_records(self):
        """Clean up all expired tool usage records"""
        current_time = datetime.now()
        users_to_remove = []
        
        for user_id, tools in self._user_tool_usage.items():
            expired_tools = []
            for tool_name, last_used in tools.items():
                if current_time - last_used > timedelta(seconds=self.tool_usage_timeout):
                    expired_tools.append(tool_name)
            
            for tool_name in expired_tools:
                del tools[tool_name]
            
            if not tools:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self._user_tool_usage[user_id]

# Global tool usage tracker instance
tool_tracker = ToolUsageTracker() 
