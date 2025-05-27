from src.utils.path_utils import get_project_root

workflow_dir = get_project_root() / "store" / "workflows"

tools_dir = get_project_root() / "store" / "tools"
agents_dir = get_project_root() / "store" / "agents"
prompts_dir = get_project_root() / "store" / "prompts"
workflows_dir = get_project_root() / "store" / "workflows"

context_variables = {
    "has_lauched": False
}

system_agents = {
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
}
