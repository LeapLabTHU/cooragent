import logging
from langchain_community.tools.tavily_search import TavilySearchResults
from .decorators import create_logged_tool

TAVILY_MAX_RESULTS = 5
logger = logging.getLogger(__name__)

# Initialize Tavily search tool with logging
LoggedTavilySearch = create_logged_tool(TavilySearchResults)
tavily_tool = LoggedTavilySearch(name="tavily_search", max_results=TAVILY_MAX_RESULTS)
