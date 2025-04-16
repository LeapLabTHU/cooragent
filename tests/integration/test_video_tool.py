import os
import base64
import json
from src.tools.video import video_tool, download_video_tool, play_video_tool

def test_video_tool():
    # 确保环境变量已设置
    if not os.getenv('SILICONFLOW_API_KEY'):
        print("请先设置 SILICONFLOW_API_KEY 环境变量")
        return

    sample_image_path = "/Users/georgewang/Downloads/walk.png"
    
    # 检查测试图片是否存在
    if not os.path.exists(sample_image_path):
        print(f"测试图片不存在: {sample_image_path}")
        return
    
    #读取并编码图片
    with open(sample_image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # 设置测试参数
    prompt = "一个人在海滩上行走"
    negative_prompt = "模糊, 低质量"
    seed = 42
    
    print("开始测试 VideoTool...")
    
    # 调用 video_tool
    result = video_tool.run({
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image": image_data,
        "seed": seed
    })
    
    print("测试结果:")
    print(result)
    
    # 解析结果获取请求ID
    try:
        response_data = json.loads(result)
        request_id = response_data.get("requestId")
        if request_id:
            print(f"获取到请求ID: {request_id}")
            return request_id
        else:
            print("未能从响应中获取请求ID")
            return None
    except json.JSONDecodeError:
        print("无法解析响应JSON")
        return None

def test_download_video_tool(request_id=None):
    """测试下载视频工具"""
    if not os.getenv('SILICONFLOW_API_KEY'):
        print("请先设置 SILICONFLOW_API_KEY 环境变量")
        return
    
    if not request_id:
        print("请提供有效的请求ID")
        return
    
    print(f"开始测试 DownloadVideoTool，请求ID: {request_id}...")
    
    # 调用 download_video_tool
    result = download_video_tool.run({"request_id": request_id})
    
    print("下载结果:")
    print(result)
    
    # 解析结果
    try:
        response_data = json.loads(result)
        status = response_data.get("status")
        print(f"视频状态: {status}")
        
        if status == "SUCCEEDED":
            video_url = response_data.get("videoUrl")
            if video_url:
                print(f"视频URL: {video_url}")
                return video_url
            else:
                print("未找到视频URL")
        elif status == "FAILED":
            error = response_data.get("error")
            print(f"生成失败: {error}")
        else:
            print(f"视频仍在处理中，当前状态: {status}")
    except json.JSONDecodeError:
        print("无法解析响应JSON")

def test_play_video_tool(video_url=None):
    """测试视频播放工具"""
    if not video_url:
        print("请提供有效的视频URL")
        return
    
    print(f"开始测试 PlayVideoTool，视频URL: {video_url}...")
    
    # 调用 play_video_tool
    result = play_video_tool.run({"video_url": video_url})
    
    print("播放结果:")
    print(result)

if __name__ == "__main__":
    # 方式1: 完整流程测试 - 生成视频，获取URL，播放视频
    request_id = test_video_tool()
    if request_id:
        video_url = test_download_video_tool(request_id)
        if video_url:
            test_play_video_tool(video_url)
    
    # 方式2: 直接检查已知请求ID的状态并播放
    # video_url = test_download_video_tool("6602b9t0xnzi")
    # if video_url:
    #     test_play_video_tool(video_url)
    
    # 方式3: 直接使用已知的视频URL进行播放测试
    # test_play_video_tool("https://example.com/video.mp4")  # 替换为实际的视频URL