from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "code"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic", 
    "planner": "reasoning",  
    "publisher": "basic",  
    "agent_factory": "basic",  
    "researcher": "basic",  
    "coder": "code",  
    "browser": "basic",  
    "reporter": "basic",  
}


