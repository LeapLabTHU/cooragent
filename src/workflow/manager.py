import hashlib
from typing import Optional
from workflow.process import run_agent_workflow

class PolishBundle:
    def __init__(self, cache_size: int = 100):
        self.cache_size = cache_size
        self.cache = {}
        self.store = {}
    
    def run(self, user_id: str,
                task_type: str,
                user_input_messages: list,
                debug: bool = False,
                deep_thinking_mode: bool = False,
                search_before_planning: bool = False,
                coor_agents: Optional[list[str]] = None,
                rounds: int = 1,
                ):
        polish_id = hashlib.sha256(f"{user_id}-{task_type}-{user_input_messages}-{debug}-{deep_thinking_mode}-{search_before_planning}-{coor_agents}".encode()).hexdigest()
        self.cache[polish_id] = []
        for _ in range(rounds):
            run_agent_workflow(user_id, task_type, user_input_messages, debug, deep_thinking_mode, search_before_planning, coor_agents, polish_id)
        return run_agent_workflow(user_id, task_type, user_input_messages, debug, deep_thinking_mode, search_before_planning, coor_agents)
        
        