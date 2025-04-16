import json
import requests
from typing import Dict, List, Any

BASE_URL = "http://localhost:8001"

def test_workflow_api(user_id: str, message_content: str) -> None:
    """Test the workflow API"""
    print("\n=== Testing workflow API ===")
    url = f"{BASE_URL}/v1/workflow"
    
    payload = {
        "user_id": user_id,
        "lang": "en",
        "messages": [
            {"role": "user", "content": message_content}
        ],
        "debug": True,
        "deep_thinking_mode": False,
        "search_before_planning": False,
        "task_type": "agent_workflow",
        "coor_agents": ["agent_factory"]
    }
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("Request successful, receiving streaming response:")
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        print(data)

            else:
                print(f"Request failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def test_list_agents_api(user_id: str, match: str = "") -> None:
    """Test the list_agents API"""
    print("\n=== Testing list_agents API ===")
    url = f"{BASE_URL}/v1/list_agents"
    
    payload = {
        "user_id": "",
        "match": match
    }
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("Request successful, receiving agent list:")
                for line in response.iter_lines():
                    if line:
                        agent = json.loads(line.decode('utf-8'))
                        print("\n=== Agent Details ===")
                        print(f"Name: {agent.get('agent_name', 'Unknown')}")
                        print(f"Nickname: {agent.get('nick_name', 'Unknown')}")
                        print(f"User ID: {agent.get('user_id', 'Unknown')}")
                        print(f"LLM Type: {agent.get('llm_type', 'Unknown')}")
                        
                        tools = agent.get('selected_tools', [])
                        if tools:
                            print("\nSelected Tools:")
                            for tool in tools:
                                print(f"- {tool}")

                        print("=" * 50)
            else:
                print(f"Request failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def test_list_default_agents_api() -> None:
    """Test the list_default_agents API"""
    print("\n=== Testing list_default_agents API ===")
    url = f"{BASE_URL}/v1/list_default_agents"
    
    try:
        with requests.get(url, stream=True) as response:
            if response.status_code == 200:
                print("Request successful, receiving default agent list:")
                for line in response.iter_lines():
                    if line:
                        agent = json.loads(line.decode('utf-8'))
                        print("\n=== Agent Details ===")
                        print(f"Name: {agent.get('agent_name', 'Unknown')}")
                        print(f"Nickname: {agent.get('nick_name', 'Unknown')}")
                        print(f"User ID: {agent.get('user_id', 'Unknown')}")
                        print(f"LLM Type: {agent.get('llm_type', 'Unknown')}")
                        
                        # Print tool list
                        tools = agent.get('selected_tools', [])
                        if tools:
                            print("\nSelected Tools:")
                            for tool in tools:
                                print(f"- {tool}")
                        print("=" * 50)
                        
            else:
                print(f"Request failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def test_list_default_tools_api() -> None:
    """Test the list_default_tools API"""
    print("\n=== Testing list_default_tools API ===")
    url = f"{BASE_URL}/v1/list_default_tools"
    
    try:
        with requests.get(url, stream=True) as response:
            if response.status_code == 200:
                print("Request successful, receiving default tool list:")
                for line in response.iter_lines():
                    if line:
                        tool = json.loads(line.decode('utf-8'))
                        print(f"Default tool: {tool}")
            else:
                print(f"Request failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def test_edit_agent_api(agent_data: Dict[str, Any]) -> None:
    """Test the edit_agent API"""
    print("\n=== Testing edit_agent API ===")
    url = f"{BASE_URL}/v1/edit_agent"
    
    
    try:
        with requests.post(url, json=agent_data, stream=True) as response:
            if response.status_code == 200:
                print("Request successful, edit agent response:")
                for line in response.iter_lines():
                    if line:
                        print(json.loads(line.decode('utf-8')))
            else:
                print(f"Request failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    USER_ID = "test_user_123"

    # Test workflow API
    test_workflow_api(USER_ID, "Create a stock analysis agent and query today's NVIDIA stock price")
    
    #Test list_agents API
    test_list_agents_api(USER_ID)
    
    #Test list_default_agents API
    test_list_default_agents_api()
    
    #Test list_default_tools API
    test_list_default_tools_api()
    
    
    #Test edit_agent API, requires providing an Agent object
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
        "agent_name": "stock_analyst_edited",
        "nick_name": "Stock Master",
        "llm_type": "basic",
        "selected_tools": [tool],
        "prompt": "This is a test agent prompt - edited."
    }
    test_edit_agent_api(agent_data)