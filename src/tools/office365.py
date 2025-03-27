import logging
from src.config import TAVILY_MAX_RESULTS
from src.tools.decorators import create_logged_tool
from pydantic import BaseModel
from O365 import Account
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
import os

# Initialize Tavily search tool with logging
# LoggedTavilySearch = create_logged_tool(TavilySearchResults)
# tavily_tool = LoggedTavilySearch(name="tavily_search", max_results=TAVILY_MAX_RESULTS)

class O365Toolkit(BaseModel):
    # 定义 Account 字段
    account: Optional[Account] = None
    
    class Config:
        arbitrary_types_allowed = True  # 允许任意类型
    
    def __init__(self, **data):
        super().__init__(**data)
        # 初始化 O365 Account
        self.account = Account((os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET')))
        
    # 其他方法...

# 重建模型
O365Toolkit.model_rebuild()

toolkit = O365Toolkit()
tools = toolkit.get_tools()
print(tools)


