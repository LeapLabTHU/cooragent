# 创建全局MCP管理器类
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class MCPManager:
    _instance = None
    _agents = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_agent(cls, agent_name, agent, mcp_obj):
        """register the agent to the global manager"""
        _agent = {
            "runtime": agent,
            "mcp_obj": mcp_obj
        }
        cls._agents[agent_name] = _agent
        logging.info(f"Successfully registered Agent: {agent_name}")
        return
    
    @classmethod
    def get_agents(cls):
        agent_list = []
        for name in cls._agents.keys():
            agent_list.append(cls._agents[name])
        return agent_list

    @classmethod
    def get_agent(cls, agent_name):
        """get the registered agent"""
        return cls._agents.get(agent_name)

    @classmethod
    def list_agents(cls):
        """list all the registered agents"""
        return list(cls._agents.keys())