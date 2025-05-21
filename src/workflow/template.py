WORKFLOW_TEMPLATE = {
    "workflow_id": "<user_id>:<polish_id>-<lap>",
    "mode": "agent_workflow",
    "version": 1,
    "lap": 1,
    "user_input_messages": [],
    "deep_thinking_mode": "false",
    "search_before_planning": "false",
    "coor_agents": [],
    "plannig_steps": [],
    "global_variables": {
        "has_lauched":"",
        "user_input":"",
        "history_messages":[]
    },
    "glabal_functions": [
        {"function_name": "is_planner_needed"
    }],
    "memory": {
        "cache": {},
        "vector_store": {},
        "database": {},
        "file_store": {}
    },
    "agent_nodes": {
        "coordinator": {
            "type": "system_agent",
            "name": "coordinator",
            "description": "Coordinator node that communicate with customers."
        },
        "planner": {
            "type": "system_agent",
            "name": "planner",
            "description": "Planner node that plan the task."
        },
        "publisher": {
            "type": "system_agent",
            "name": "publisher",
            "description": "Publisher node that publish the task."
        },
        "agent_factory": {
            "type": "system_agent",
            "name": "agent_factory",
            "description": "Agent factory node that create the agent."
        },
        "researcher": {
            "type": "execution_agent",
            "name": "researcher",
            "agent": {
                "user_id": "test",
                "agent_name": "researcher",
                "nick_name": "researcher",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": ""
            }
        },
        "reporter": {
            "type": "execution_agent",
            "name": "reporter",
            "agent": {
                "user_id": "test",
                "agent_name": "reporter",
                "nick_name": "reporter",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": ""
            }
        },
        "coder": {
            "type": "execution_agent",
            "name": "coder",
            "agent": {
                "user_id": "test",
                "agent_name": "coder",
                "nick_name": "coder",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": ""
            }
        },
        "browser": {
            "type": "execution_agent",
            "name": "browser",
            "agent": {
                "user_id": "test",
                "agent_name": "browser",
                "nick_name": "browser",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": ""
            }
        }
    },
    "graph": [
    ]
}
