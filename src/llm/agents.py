from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "code"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic", 
    "planner": "reasoning",  
    "publisher": "reasoning",
    "agent_factory": "reasoning",
    "researcher": "basic",  
    "coder": "code",  
    "browser": "basic",  
    "reporter": "basic",  
}
