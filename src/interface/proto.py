import time
from enum import Enum, unique
from typing import List, Optional
from pydantic import BaseModel, Field


@unique
class Lang(str, Enum):
    EN = "en"
    ZH = "zh"
    JP = "jp"
    SP = 'sp'
    DE = 'de'

@unique
class Role(str, Enum):
    USER = "user"
    MENTOR = "mentor"
    TEACH_ASS = 'teach_ass'
    ASSISTANT = 'assistant'


class Tool(BaseModel):
    name: str
    description: Role

class Agent(BaseModel):
    agent_name: str
    agent_id: str
    llm_type: str
    selected_tools: List[Tool]
    prompt: str

