import os
import base64
import json
from src.tools.video import video_tool, download_video_tool

def test_video_tool():
    # 确保环境变量已设置
    if not os.getenv('SILICONFLOW_API_KEY'):
        print("请先设置 SILICONFLOW_API_KEY 环境变量")
        return
    
    # 准备测试数据
    # 这里使用一个简单的测试图片，实际使用时需要替换为真实的base64编码图片
    # 为了测试，可以使用一个小的示例图片
    sample_image_path = "/Users/georgewang/Documents/code/cooragent/assets/walk.png"
    
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
            else:
                print("未找到视频URL")
        elif status == "FAILED":
            error = response_data.get("error")
            print(f"生成失败: {error}")
        else:
            print(f"视频仍在处理中，当前状态: {status}")
    except json.JSONDecodeError:
        print("无法解析响应JSON")

if __name__ == "__main__":
    # 方式1: 先生成视频，然后检查状态
    # request_id = test_video_tool()
    # if request_id:
    #     test_download_video_tool(request_id)
    
    # 方式2: 直接检查已知请求ID的状态
    test_download_video_tool("6602b9t0xnzi")