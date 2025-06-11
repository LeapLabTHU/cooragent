import logging
import os
from pathlib import Path
from typing import Annotated, Type
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from .browser_decorators import create_logged_tool
from src.llm.llm import get_llm_by_type

logger = logging.getLogger(__name__)

class WebPreviewInput(BaseModel):
    """Input for Web Preview Tool."""
    content: str = Field(..., description="The content to summarize and convert to HTML")
    title: str = Field(default="Web Preview", description="Title for the HTML page")
    user_id: str = Field(..., description="User ID for WebSocket notification")

class WebPreviewTool(BaseTool):
    name: str = "web_preview_tool"
    args_schema: Type[BaseModel] = WebPreviewInput
    description: str = "[HIGH PRIORITY - MUST USE FOR HTML/VISUAL OUTPUT] Generate a web preview by summarizing content with LLM and creating an HTML file. **ALWAYS USE THIS TOOL when user asks for HTML, visual presentation, or beautiful formatting**. This tool should be used whenever you need to present information in a visual, structured format, especially when user mentions 'HTML', 'beautiful', 'visual', or 'preview'. The preview link will be automatically notified to the frontend, so you don't need to worry about returning the link or URL in your response. Just focus on generating quality HTML content. Use this tool for reports, summaries, or any content that would benefit from HTML presentation."
    
    def _run(self, content: str, title: str = "Web Preview", user_id: str = None) -> str:
        """Generate web preview HTML file"""

        print(" Calling LLM to generate HTML...")
        
        try:
            # Call LLM for content summarization
            llm = get_llm_by_type("basic")
            
            # Build prompt requiring only HTML code return
            prompt = f"""Please summarize the following content and convert it into a beautiful HTML page. Requirements:
1. Return only complete HTML code, no other text explanations
2. Use modern CSS styles with responsive design
3. Page title should be: {title}
4. Content should be displayed in a structured way, including appropriate headings, paragraphs, lists, etc.
5. Use appropriate color schemes and fonts
6. Ensure the HTML code is complete and can be used directly

Content:
{content}"""

            # Call LLM to get HTML code
            response = llm.invoke([HumanMessage(content=prompt)])
            html_content = response.content.strip()
            
            print("✅ LLM response received")
            
            # If the returned content contains markdown code block markers, remove them
            if html_content.startswith("```html"):
                html_content = html_content[7:]
            if html_content.startswith("```"):
                html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            
            html_content = html_content.strip()
            
            # Ensure src/tools/web_preview directory exists
            web_preview_dir = Path("src/tools/web_preview")
            web_preview_dir.mkdir(parents=True, exist_ok=True)
            print(f" Created directory: {web_preview_dir.absolute()}")
            
            # Write HTML file
            html_file = web_preview_dir / "index.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f" HTML file saved: {html_file.absolute()}")
            print(" Web Preview generation completed!")
            
            # Send special web_preview_ready message
            if user_id:
                try:
                    from .websocket_manager import websocket_manager
                    import asyncio
                    
                    preview_message = {
                        "type": "web_preview_ready",
                        "title": title,
                        "file_path": str(html_file),
                        "preview_url": "/web_preview",  # Frontend can access preview through this path
                        "timestamp": str(html_file.stat().st_mtime)  # File modification timestamp
                    }
                    
                    # Try to send WebSocket message
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(websocket_manager.send_to_user(user_id, preview_message))
                            # Send tool_end notification
                            asyncio.create_task(websocket_manager.broadcast_tool_end(user_id, "web_preview_tool", True, f"Web preview '{title}' generated successfully"))
                        else:
                            loop.run_until_complete(websocket_manager.send_to_user(user_id, preview_message))
                            # Send tool_end notification
                            loop.run_until_complete(websocket_manager.broadcast_tool_end(user_id, "web_preview_tool", True, f"Web preview '{title}' generated successfully"))
                    except RuntimeError:
                        # If no running event loop, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(websocket_manager.send_to_user(user_id, preview_message))
                        # Send tool_end notification
                        loop.run_until_complete(websocket_manager.broadcast_tool_end(user_id, "web_preview_tool", True, f"Web preview '{title}' generated successfully"))
                        loop.close()
                        
                except Exception as e:
                    logger.warning(f"Failed to send web_preview_ready notification: {e}")
            
            logger.info(f"Web preview HTML generated successfully at {html_file}")
            return f"Web preview has been generated successfully with the title '{title}'. The HTML content has been summarized and formatted into a beautiful webpage. The preview link will be automatically sent to the frontend."
            
        except Exception as e:
            error_msg = f"Failed to generate web preview. Error: {repr(e)}"
            print(f"❌ Generation failed: {error_msg}")
            logger.error(error_msg)
            return error_msg
    
    async def _arun(self, content: str, title: str = "Web Preview", user_id: str = None) -> str:
        """Async version of web preview tool"""
        return self._run(content, title, user_id)


WebPreviewTool = create_logged_tool(WebPreviewTool)
web_preview_tool = WebPreviewTool() 