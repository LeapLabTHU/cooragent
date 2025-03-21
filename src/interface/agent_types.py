from pydantic import BaseModel, ConfigDict
from typing import List
from .mcp_types import Tool, Prompt


class Prompt(BaseModel):
    """Definition for a prompt the client can call."""
    name: str
    """The name of the prompt."""
    description: str
    """The description of the prompt."""
    arguments: List[str]
    """The arguments of the prompt."""
    content: str
    """The content of the prompt."""
    model_config = ConfigDict(extra="allow")    
    
class Agent(BaseModel):
    """Definition for an agent the client can call."""
    agent_name: str
    """The name of the agent."""
    agent_id: str
    """The id of the agent."""
    llm_type: str
    """The type of LLM to use for the agent."""
    selected_tools: List[Tool]
    """The tools that the agent can use."""
    prompt: Prompt
    """The prompt to use for the agent."""
    model_config = ConfigDict(extra="allow")
