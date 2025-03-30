# 全局字典，用于存储所有注册的代理
from typing import Dict, Any, Callable, Optional
from functools import wraps

register_mcp_agents: Dict[str, Any] = {}

def register_mcp(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        agent_instance = await func(*args, **kwargs)
        if not isinstance(agent_instance, str):
            # 注册所有代理到全局字典
            for agent_name in dir(agent_instance):
                if not agent_name.startswith('_'):
                    agent_obj = getattr(agent_instance, agent_name)
                    if callable(getattr(agent_obj, 'send', None)):
                        register_mcp_agents[agent_name] = agent_obj
        return agent_instance
    return wrapper