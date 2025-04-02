# 创建全局MCP管理器类
class MCPManager:
    _instance = None
    _agents = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_agent(cls, agent_name, agent):
        """将agent注册到全局管理器"""
        cls._agents[agent_name] = agent
        print(f"已成功注册Agent: {agent_name}")
        return agent

    @classmethod
    def get_agent(cls, agent_name):
        """获取已注册的agent"""
        return cls._agents.get(agent_name)

    @classmethod
    def list_agents(cls):
        """列出所有已注册的agents"""
        return list(cls._agents.keys())