import requests
import logging
from pydantic import BaseModel, Field
from typing import ClassVar, Type
from langchain.tools import BaseTool
from src.tools.decorators import create_logged_tool

logger = logging.getLogger(__name__)
import os

url = "https://api.siliconflow.cn/v1/video/submit"


class VideoToolInput(BaseModel):
    """Input for VideoTool."""

    prompt: str = Field(..., description="The prompt for video generation")
    negative_prompt: str = Field(..., description="The negative prompt for video generation")
    image: str = Field(..., description="The image data for video generation")
    seed: int = Field(..., description="The seed for video generation")


class VideoTool(BaseTool):
    name: ClassVar[str] = "video"
    args_schema: Type[BaseModel] = VideoToolInput
    description: ClassVar[str] = (
        "Use this tool to generate a video based on provided prompts and image."
    )

    def _run(self, prompt: str, negative_prompt: str, image: str, seed: int) -> str:
        """Run the video generation task."""
        payload = {
            "model": "Wan-AI/Wan2.1-I2V-14B-720P",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": "1280x720",
            "image": image, 
            "seed": seed
        }
        headers = {
            "Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}",
            "Content-Type": "application/json"
        }   
        response = requests.request("POST", url, json=payload, headers=headers)
        return response.text



VideoTool = create_logged_tool(VideoTool)
video_tool = VideoTool()


class VideoStatusInput(BaseModel):
    """Input for DownloadVideoTool."""
    
    request_id: str = Field(..., description="The request ID of the video generation task")


class DownloadVideoTool(BaseTool):
    name: ClassVar[str] = "download_video"
    args_schema: Type[BaseModel] = VideoStatusInput
    description: ClassVar[str] = "Use this tool to check the status and download a video that was generated using the video tool."

    def _run(self, request_id: str) -> str:
        """Check the status of a video generation task."""
        status_url = "https://api.siliconflow.cn/v1/video/status"
        
        payload = {"requestId": request_id}
        headers = {
            "Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        response = requests.request("POST", status_url, json=payload, headers=headers)
        return response.text
    
    async def _arun(self, request_id: str) -> str:
        """Check the status of a video generation task asynchronously."""
        # 简单调用同步方法
        return self._run(request_id)


DownloadVideoTool = create_logged_tool(DownloadVideoTool)
download_video_tool = DownloadVideoTool()