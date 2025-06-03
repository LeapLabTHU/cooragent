import requests
import json
import re
from pydantic import BaseModel, Field
from typing import ClassVar, Type
from langchain.tools import BaseTool
from ..service.decorators import create_logged_tool
from src.llm.llm import get_llm_by_type
from src.service.env import USE_BROWSER
import logging

logger = logging.getLogger(__name__)

class BrowserInput(BaseModel):
    """Input for Browser Tool."""
    url: str = Field(..., description="Web page URL")
    test_mode: bool = Field(default=False, description="Whether it's test mode")

class BrowserTool(BaseTool):
    name: ClassVar[str] = "browser"
    args_schema: Type[BaseModel] = BrowserInput
    description: ClassVar[str] = (
        "Browser page browsing tool for getting web page HTML content and intelligent summarization. Input web page URL, return structured summary of web page content."
    )
    
    def _check_browser_enabled(self) -> bool:
        """Check if browser tool is enabled via environment variable"""
        return USE_BROWSER
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text content from HTML"""
        try:
            # Remove script and style tags and their content
            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Decode HTML entities
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&amp;', '&')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            
            # Clean up extra whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Limit text length to avoid being too long
            if len(text) > 8000:
                text = text[:8000] + "..."
                
            return text
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            return html_content[:1000] + "..." if len(html_content) > 1000 else html_content
    
    def _summarize_content(self, url: str, text_content: str) -> str:
        """Use LLM to summarize web page content"""
        try:
            llm = get_llm_by_type("basic")
            
            prompt = f"""Please analyze the following web page content and provide a structured summary.

Web page URL: {url}

Web page content:
{text_content}

Please provide a summary in the following format:

## Basic Web Page Information
- Website Name: [Website Name]
- Page Title: [Page Title]
- Page Type: [Search Results Page/News Page/Product Page/Other]

## Main Content Summary
[Summarize the main content of the page in 2-3 sentences]

## Key Information
[List 3-5 key information points, if it's a search results page, please list the main search results]

## Related Links or Resources
[If there are important links or resources, please list them]

Please reply in Chinese, keep it concise and clear."""

            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            logger.error(f"Error during LLM summarization: {e}")
            return f"Web page content retrieved successfully, but error occurred during summarization: {str(e)}\n\nOriginal content preview:\n{text_content[:500]}..."

    def _run(self, url: str, test_mode: bool = False) -> str:
        """Browser page browsing, returns web page HTML content"""
        
        # Check if browser tool is enabled
        if not self._check_browser_enabled():
            logger.warning("Browser tool is disabled via environment variable USE_BROWSER")
            return json.dumps({
                "summary": "Browser tool is currently disabled. Please enable USE_BROWSER environment variable to use this feature.",
                "success": False,
                "url": url,
                "error": "Browser tool disabled"
            }, ensure_ascii=False)
        
        try:
            # Build query parameters
            query_params = {
                "url": url,
                "duration": 30,
                "interval": 1.5,
                "scroll_amount": 1,
                "return_html": "true"
            }
            print("Request URL", url)
            # Send request to scroll API
            response = requests.get("http://106.13.116.188:30004/scroll", params=query_params)
            
            response_text = response.text
            
            # Check if response is valid JSON
            try:
                # Try to parse as JSON
                data = json.loads(response_text)
                
                # If it's JSON and contains success flag
                if isinstance(data, dict):
                    if test_mode:
                        logger.info(f"Successfully parsed as JSON: {data}")
                    
                    # Get HTML content
                    html_content = ""
                    if "html" in data and "success" in data:
                        html_content = data.get("html", "")
                        success = data.get("success", False)
                    else:
                        html_content = data.get("html_content", "") or data.get("content", "") or json.dumps(data)
                        success = True
                    
                    # If successfully got HTML content, summarize it
                    if success and html_content:
                        # Extract text content
                        text_content = self._extract_text_from_html(html_content)
                        
                        # Use LLM to summarize content
                        summary = self._summarize_content(url, text_content)
                        
                        return json.dumps({
                            "summary": summary,
                            "success": True,
                            "url": url
                        }, ensure_ascii=False)
                    else:
                        return json.dumps({
                            "summary": "Unable to get web page content",
                            "success": False,
                            "url": url
                        }, ensure_ascii=False)
            except json.JSONDecodeError:
                if test_mode:
                    logger.info("Response is not JSON format, trying to extract HTML content")
                
                # Try to extract JSON from response
                json_match = re.search(r'(\{.*"success":\s*(true|false).*\})', response_text)
                if json_match:
                    try:
                        json_str = json_match.group(1)
                        if test_mode:
                            logger.info(f"JSON string extracted from response: {json_str}")
                        
                        data = json.loads(json_str)
                        html_content = data.get("html", "")
                        if html_content:
                            text_content = self._extract_text_from_html(html_content)
                            summary = self._summarize_content(url, text_content)
                            return json.dumps({
                                "summary": summary,
                                "success": True,
                                "url": url
                            }, ensure_ascii=False)
                    except:
                        if test_mode:
                            logger.warning("Extracted JSON cannot be parsed")
                
                # If response contains HTML tags
                if "<html" in response_text:
                    if test_mode:
                        logger.info("Response contains HTML tags")
                    
                    text_content = self._extract_text_from_html(response_text)
                    summary = self._summarize_content(url, text_content)
                    return json.dumps({
                        "summary": summary,
                        "success": True,
                        "url": url
                    }, ensure_ascii=False)
                
                # Other cases, try to summarize response content
                summary = self._summarize_content(url, response_text)
                return json.dumps({
                    "summary": summary,
                    "success": response.status_code == 200,
                    "url": url
                }, ensure_ascii=False)
                
        except Exception as e:
            if test_mode:
                logger.error(f"Exception occurred: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            return json.dumps({
                "summary": f"Error occurred while accessing web page: {str(e)}",
                "success": False,
                "url": url,
                "error": str(e)
            }, ensure_ascii=False)

    async def _arun(self, url: str, test_mode: bool = False) -> str:
        """Async version of browser tool"""
        return self._run(url, test_mode)

BrowserTool = create_logged_tool(BrowserTool)
browser_tool = BrowserTool()
