import pytest
from fastapi.testclient import TestClient
from src.service.app import Server
from src.interface.agent_types import AgentRequest, listAgentRequest
import requests
import json

@pytest.fixture
def client():
    server = Server()
    return TestClient(server.app)

def test_create_agents():
    """测试创建代理 API"""
    url = f"http://localhost:8001/v1/create_agents"
    
    # 构建请求数据
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "我需要一个能够搜索网络的助手"
            }
        ]
    }
    
    # 发送请求
    response = requests.post(url, json=payload, stream=True)
    
    # 打印状态码
    print(f"状态码: {response.status_code}")
    
    # 读取流式响应
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"收到数据: {decoded_line}")
                # 尝试解析 JSON
                try:
                    agent_data = json.loads(decoded_line)
                    print(f"代理名称: {agent_data.get('agent_name', 'N/A')}")
                except json.JSONDecodeError:
                    print("无法解析为 JSON")

def test_list_agents():
    """测试列出代理 API"""
    url = f"http://localhost:8001/v1/list_agents"
    
    # 构建请求数据
    payload = {
        "user_id": "test_user",
        "match": "test"
    }
    
    # 发送请求
    response = requests.post(url, json=payload, stream=True)
    
    # 打印状态码
    print(f"状态码: {response.status_code}")
    
    # 读取流式响应
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"收到数据: {decoded_line}")
                # 尝试解析 JSON
                try:
                    agent_data = json.loads(decoded_line)
                    print(f"代理名称: {agent_data.get('agent_name', 'N/A')}")
                except json.JSONDecodeError:
                    print("无法解析为 JSON")

def test_invalid_create_agents_request():
    """测试无效的创建代理请求"""
    client = TestClient(Server().app)
    
    # 发送空请求
    response = client.post("/v1/create_agents", json={})
    assert response.status_code == 422

def test_invalid_list_agents_request():
    """测试无效的列出代理请求"""
    client = TestClient(Server().app)
    
    # 发送空请求
    response = client.post("/v1/list_agents", json={})
    assert response.status_code == 422

if __name__ == "__main__":
    print("测试创建代理 API...")
    test_create_agents()
    
    print("\n测试列出代理 API...")
    test_list_agents() 