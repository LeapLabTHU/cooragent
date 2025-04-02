from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "code"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic",  # 协调默认使用basic llm
    "planner": "reasoning",  # 计划默认使用basic llm
    "publisher": "basic",  # 决策使用basic llm
    "create_agent": "basic",  # 决策使用basic llm
    "researcher": "basic",  # 简单搜索任务使用basic llm
    "coder": "code",  # 编程任务使用basic llm
    "browser": "basic",  # 浏览器操作使用vision llm
    "reporter": "basic",  # 编写报告使用basic llm
}
