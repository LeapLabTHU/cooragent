#!/usr/bin/env python3
"""
Web Preview Tool - used to manage and preview the index.html file in the current folder
The port can be set through the environment variable WEB_PREVIEW_PORT, the default is 8080
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebPreviewServer:
    """Web Preview Server"""
    
    def __init__(self, port: Optional[int] = None, host: str = "0.0.0.0"):
        self.host = host
        self.port = port or int(os.getenv("WEB_PREVIEW_PORT", "8080"))
        self.current_dir = Path.cwd()
        self.index_file = self.current_dir / "index.html"
        
        # Create FastAPI application
        self.app = FastAPI(
            title="Web Preview Server",
            description="Used to preview the index.html file in the current folder",
            version="1.0.0"
        )
        
        self._setup_routes()
        self._setup_static_files()
    
    def _setup_routes(self):
        """Set routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def serve_index():
            """Provide index.html file"""
            if not self.index_file.exists():
                return HTMLResponse(
                    content=self._generate_default_page(),
                    status_code=200
                )
            
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return HTMLResponse(content=content)
            except Exception as e:
                logger.error(f"Failed to read index.html: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to read index.html: {str(e)}")
        
        @self.app.get("/status")
        async def get_status():
            """Get service status"""
            return {
                "status": "running",
                "port": self.port,
                "current_directory": str(self.current_dir),
                "index_file_exists": self.index_file.exists(),
                "index_file_path": str(self.index_file)
            }
        
        @self.app.get("/reload")
        async def reload_page():
            """Reload page (return the latest index.html content)"""
            if not self.index_file.exists():
                return {"message": "index.html does not exist", "exists": False}
            
            try:
                # 获取文件修改时间
                mtime = self.index_file.stat().st_mtime
                return {
                    "message": "Page reloaded",
                    "exists": True,
                    "last_modified": mtime
                }
            except Exception as e:
                logger.error(f"Failed to reload: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to reload: {str(e)}")
    
    def _setup_static_files(self):
        """Set static file service"""
        # Use the current directory as the static file directory to provide CSS, JS, images, etc.
        self.app.mount("/static", StaticFiles(directory=str(self.current_dir)), name="static")
    
    def _generate_default_page(self) -> str:
        """Generate default page (when index.html does not exist)"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Preview - index.html does not exist</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .warning {{
            color: #e74c3c;
            font-size: 18px;
            margin-bottom: 20px;
        }}
        .info {{
            color: #666;
            line-height: 1.6;
        }}
        .path {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            margin: 10px 0;
        }}
        .status {{
            margin-top: 30px;
            padding: 20px;
            background: #e8f4fd;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 Web Preview Server</h1>
        <div class="warning">⚠️ index.html file does not exist</div>
        <div class="info">
            <p>Current working directory:</p>
            <div class="path">{self.current_dir}</div>
            <p>Please create the <code>index.html</code> file in the current directory, then refresh the page.</p>
        </div>
        <div class="status">
            <h3>Service status</h3>
            <ul>
                <li>Server running on: <strong>http://{self.host}:{self.port}</strong></li>
                <li>Status check: <a href="/status">/status</a></li>
                <li>Reload: <a href="/reload">/reload</a></li>
            </ul>
        </div>
    </div>
    <script>
        // Check if the file exists every 5 seconds
        setInterval(async () => {{
            try {{
                const response = await fetch('/status');
                const data = await response.json();
                if (data.index_file_exists) {{
                    location.reload();
                }}
            }} catch (e) {{
                console.log('Failed to check file status:', e);
            }}
        }}, 5000);
    </script>
</body>
</html>
        """
    
    def run(self):
        """Start server"""
        logger.info(f"Starting Web Preview Server...")
        logger.info(f"Service address: http://{self.host}:{self.port}")
        logger.info(f"Current directory: {self.current_dir}")
        logger.info(f"index.html exists: {self.index_file.exists()}")
        
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
        except KeyboardInterrupt:
            logger.info("服务器已停止")
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            sys.exit(1)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web Preview Server - Preview the index.html file in the current folder")
    parser.add_argument("--port", type=int, help="Service port (default: 8080 or environment variable WEB_PREVIEW_PORT)")
    parser.add_argument("--host", default="0.0.0.0", help="Service host (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    # Create and start server
    server = WebPreviewServer(port=args.port, host=args.host)
    server.run()


if __name__ == "__main__":
    main() 