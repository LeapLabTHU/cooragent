import logging
from src.tools.decorators import create_logged_tool
from pydantic import BaseModel
from O365 import Account
from typing import Optional
from dotenv import load_dotenv

TAVILY_MAX_RESULTS = 5
load_dotenv()

logger = logging.getLogger(__name__)
import os


class O365Toolkit(BaseModel):
    # 定义 Account 字段
    account: Optional[Account] = None
    
    class Config:
        arbitrary_types_allowed = True 
    
    def __init__(self, **data):
        super().__init__(**data)
        self.account = Account((os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET')))
        

O365Toolkit.model_rebuild()

toolkit = O365Toolkit()
tools = toolkit.get_tools()
print(tools)


