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
    "nodes": {
        "coordinator": {
            "component_type": "agent",
            "label": "coordinator",
            "name": "coordinator",
            "description": "Coordinator node that communicate with customers.",
            "config": {
                "type": "system_agent",
                "name": "coordinator",
            },
        },
        "planner": {
            "component_type": "agent",
            "label": "planner",
            "name": "planner",
            "description": "Planner node that plan the task.",
            "config": {
                "type": "system_agent",
                "name": "planner",
            },
        },
        "publisher": {
            "component_type": "condtion",
            "label": "publisher_condition",
            "name": "publisher",
            "description": "Publisher node that publish the task.",
            "config": {
                "type": "system_agent",
                "name": "publisher",
            },
        },
        "agent_factory": {
            "component_type": "agent",
            "label": "system_agent",
            "type": "system_agent",
            "name": "agent_factory",
            "description": "Agent factory node that create the agent.",
            "config": {
                "type": "system_agent",
                "name": "agent_factory",
            },
        },
        "researcher": {
            "component_type": "agent",
            "label": "researcher",
            "type": "execution_agent",
            "name": "researcher",
            "config": {
                "type": "execution_agent",
                "name": "researcher",
                "user_id": "test",
                "name": "researcher",
                "nick_name": "researcher",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": "",
            },
        },
        "reporter": {
            "component_type": "agent",
            "label": "reporter",
            "type": "execution_agent",
            "name": "reporter",
            "config": {
                "user_id": "test",
                "name": "reporter",
                "nick_name": "reporter",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": ""
            },
        },
        "coder": {
            "component_type": "agent",
            "label": "coder",
            "type": "execution_agent",
            "name": "coder",
            "config": {
                "user_id": "test",
                "name": "coder",
                "nick_name": "coder",
                "description": "",
                "llm_type": "basic",
                "selected_tools": [],
                "prompt": ""
            },
        },
        "browser": {
            "component_type": "agent",
            "label": "browser",
            "type": "execution_agent",
            "name": "browser",
            "config": {
                "user_id": "test",
                "name": "browser",
                "nick_name": "browser",
                "description": "",
                "llm_type": "basic",
                "tools": [],
                "prompt": ""
            },
        }
    },
    "graph": [
    ]
}
