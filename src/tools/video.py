import requests
import logging
from pydantic import BaseModel, Field
from typing import ClassVar, Type
from langchain.tools import BaseTool
from src.tools.decorators import create_logged_tool
import webbrowser
import json
logger = logging.getLogger(__name__)
import os
import time
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

    def _run(self, request_id: str, download_local: bool = False) -> str:
        """Check the status of a video generation task."""
        status_url = "https://api.siliconflow.cn/v1/video/status"
        
        payload = {"requestId": request_id}
        headers = {
            "Authorization": f"Bearer {os.getenv('SILICONFLOW_API_KEY')}",
            "Content-Type": "application/json"
        }
        status = 'InProgress'
        while status == 'InProgress':
            response = requests.request("POST", status_url, json=payload, headers=headers)
            response_json = json.loads(response.text)
            status = response_json["status"]
            if status == 'Succeed':
                video_url = response_json["results"]["videos"][0]["url"]
                if download_local:
                    response = requests.get(video_url)
                    with open(f"{request_id}.mp4", "wb") as f:
                        f.write(response.content)
                return video_url
            elif status == 'InProgress':
                time.sleep(1)
            else:
                raise Exception(f"video Obtain failed: {response_json['error']}")
        
    
    async def _arun(self, request_id: str) -> str:
        """Check the status of a video generation task asynchronously."""
        # 简单调用同步方法
        return self._run(request_id)


DownloadVideoTool = create_logged_tool(DownloadVideoTool)
download_video_tool = DownloadVideoTool()


class PlayVideoInput(BaseModel):
    """Input for PlayVideoTool."""
    
    video_url: str = Field(..., description="The URL of the video to play")


class PlayVideoTool(BaseTool):
    name: ClassVar[str] = "play_video"
    args_schema: Type[BaseModel] = PlayVideoInput
    description: ClassVar[str] = "Use this tool to play a video in the default web browser using the video URL obtained from the download_video tool."

    def _run(self, video_url: str) -> str:
        """Play a video in the default web browser."""
        try:
            webbrowser.open(video_url)
            return f"视频已在默认浏览器中打开: {video_url}"
        except Exception as e:
            logger.error(f"打开视频时出错: {str(e)}")
            return f"打开视频时出错: {str(e)}"
    
    async def _arun(self, video_url: str) -> str:
        """Play a video in the default web browser asynchronously."""
        return self._run(video_url)


PlayVideoTool = create_logged_tool(PlayVideoTool)
play_video_tool = PlayVideoTool()