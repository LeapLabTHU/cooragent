
from typing import Dict
from uuid import uuid4
from datetime import datetime, timedelta
import json

class UserSession:
    def __init__(self, user_id: str, max_history=10):
        self.user_id = user_id
        self.session_id = str(uuid4())
        self.history = []
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.max_history = max_history

    def add_message(self, role: str, content: str):
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # 
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self.last_active = datetime.now()

class SessionManager:
    def __init__(self, session_timeout=300):
        self.sessions: Dict[str, UserSession] = {}
        self.timeout = session_timeout

    def get_session(self, user_id: str) -> UserSession:
        self.cleanup()
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]

    def cleanup(self):
        expired = [
            uid for uid, session in self.sessions.items()
            if (datetime.now() - session.last_active).seconds > self.timeout
        ]
        for uid in expired:
            del self.sessions[uid]