import json
import requests
from typing import Dict, List, Any

BASE_URL = "http://localhost:8001"

def test_workflow_api(user_id: str, message_content: str) -> None:
    """测试 workflow API"""
    print("\n=== 测试 workflow API ===")
    url = f"{BASE_URL}/v1/workflow"
    
    payload = {
        "user_id": user_id,
        "lang": "zh",
        "messages": [
            {"role": "user", "content": message_content}
        ],
        "debug": True,
        "deep_thinking_mode": False,
        "search_before_planning": False
    }
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("请求成功，接收流式响应：")
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        event_type = data.get("event")
                        
                        if event_type == "message":
                            message_data = data.get("data", {})
                            if "delta" in message_data:
                                content = message_data["delta"].get("content", "")
                                reasoning = message_data["delta"].get("reasoning_content", "")
                                
                                if content:
                                    print(f"内容: {content}")
                                if reasoning:
                                    print(f"推理过程: {reasoning}")
                        
                        elif event_type == "start_of_agent":
                            agent_name = data.get("data", {}).get("agent_name", "未知代理")
                            print(f"\n--- {agent_name} 开始工作 ---")
                        
                        elif event_type == "end_of_agent":
                            agent_name = data.get("data", {}).get("agent_name", "未知代理")
                            print(f"--- {agent_name} 工作结束 ---\n")
                        
                        elif event_type == "tool_call":
                            tool_data = data.get("data", {})
                            tool_name = tool_data.get("tool_name", "未知工具")
                            tool_input = tool_data.get("tool_input", "")
                            print(f"\n调用工具: {tool_name}")
                            print(f"工具输入: {tool_input}")
                        
                        elif event_type == "tool_call_result":
                            tool_data = data.get("data", {})
                            tool_name = tool_data.get("tool_name", "未知工具")
                            tool_result = tool_data.get("tool_result", "")
                            print(f"工具 {tool_name} 返回结果: {tool_result}\n")
                        
                        elif event_type in ["start_of_workflow", "end_of_workflow"]:
                            workflow_status = "开始" if event_type == "start_of_workflow" else "结束"
                            print(f"\n=== 工作流 {workflow_status} ===\n")
            else:
                print(f"请求失败: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"发生错误: {str(e)}")

def test_list_agents_api(user_id: str, match: str = "") -> None:
    """测试 list_agents API"""
    print("\n=== 测试 list_agents API ===")
    url = f"{BASE_URL}/v1/list_agents"
    
    payload = {
        "user_id": "",
        "match": match
    }
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("请求成功，接收代理列表：")
                for line in response.iter_lines():
                    if line:
                        agent = json.loads(line.decode('utf-8'))
                        print("\n=== 代理详情 ===")
                        print(f"名称: {agent.get('agent_name', 'Unknown')}")
                        print(f"昵称: {agent.get('nick_name', 'Unknown')}")
                        print(f"用户ID: {agent.get('user_id', 'Unknown')}")
                        print(f"LLM类型: {agent.get('llm_type', 'Unknown')}")
                        
                        # 打印工具列表
                        tools = agent.get('selected_tools', [])
                        if tools:
                            print("\n已选择的工具:")
                            for tool in tools:
                                print(f"- {tool}")
                        
                        # 打印提示词（只显示前200个字符）
                        # prompt = agent.get('prompt', '')
                        # if prompt:
                        #     print("\n提示词预览:")
                        #     print(f"{prompt[:200]}...")
                        print("=" * 50)
            else:
                print(f"请求失败: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"发生错误: {str(e)}")

def test_list_default_agents_api() -> None:
    """测试 list_default_agents API"""
    print("\n=== 测试 list_default_agents API ===")
    url = f"{BASE_URL}/v1/list_default_agents"
    
    try:
        with requests.get(url, stream=True) as response:
            if response.status_code == 200:
                print("请求成功，接收默认代理列表：")
                for line in response.iter_lines():
                    if line:
                        agent = json.loads(line.decode('utf-8'))
                        print("\n=== 代理详情 ===")
                        print(f"名称: {agent.get('agent_name', 'Unknown')}")
                        print(f"昵称: {agent.get('nick_name', 'Unknown')}")
                        print(f"用户ID: {agent.get('user_id', 'Unknown')}")
                        print(f"LLM类型: {agent.get('llm_type', 'Unknown')}")
                        
                        # 打印工具列表
                        tools = agent.get('selected_tools', [])
                        if tools:
                            print("\n已选择的工具:")
                            for tool in tools:
                                print(f"- {tool}")
                        print("=" * 50)
                        
            else:
                print(f"请求失败: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"发生错误: {str(e)}")

def test_list_default_tools_api() -> None:
    """测试 list_default_tools API"""
    print("\n=== 测试 list_default_tools API ===")
    url = f"{BASE_URL}/v1/list_default_tools"
    
    try:
        with requests.get(url, stream=True) as response:
            if response.status_code == 200:
                print("请求成功，接收默认工具列表：")
                for line in response.iter_lines():
                    if line:
                        tool = json.loads(line.decode('utf-8'))
                        print(f"默认工具: {tool}")
            else:
                print(f"请求失败: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"发生错误: {str(e)}")

def test_edit_agent_api(agent_data: Dict[str, Any]) -> None:
    """测试 edit_agent API"""
    print("\n=== 测试 edit_agent API ===")
    url = f"{BASE_URL}/v1/edit_agent"
    
    
    try:
        with requests.post(url, json=agent_data, stream=True) as response:
            if response.status_code == 200:
                print("请求成功，编辑代理响应：")
                print(response.text)
            else:
                print(f"请求失败: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    # 用户ID，实际使用时替换为真实ID
    USER_ID = "test_user_123"
    
    # 测试 workflow API
    # test_workflow_api(USER_ID, "查询北京今天天气")
    
    # 测试 list_agents API
    # test_list_agents_api(USER_ID)
    
    # 测试 list_default_agents API
    # test_list_default_agents_api()
    
    # 测试 list_default_tools API
    # test_list_default_tools_api()
    
    # 测试 edit_agent API，需要提供一个Agent对象
    # 注意：这里使用了一个简单的示例，实际使用时需要根据您的Agent模型结构修改
    tool_input_schema = {
        'description': 'Input for the Tavily tool.',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'The search query'
            }
        },
        'required': ['query'],
        'title': 'TavilyInput',
        'type': 'object'
    }

    tool = {
        "name": "tavily",
        "description": "Tavily tool",
        "inputSchema": tool_input_schema
    }

    agent_data = {
        "user_id": "test_user_123",
        "agent_name": "stock_analyst",
        "nick_name": "stock_analyst",
        "llm_type": "basic",
        "selected_tools": [tool],
        "prompt": "这是一个测试代理"
    }
    test_edit_agent_api(agent_data)