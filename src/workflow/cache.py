import json
import logging
from src.workflow.template import WORKFLOW_TEMPLATE
from typing import Union
from src.interface.agent import Agent
from src.config import agents_dir
import os
from pathlib import Path
from collections import deque
import re

logger = logging.getLogger(__name__)

class WorkflowCache:
    _instance = None
    

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WorkflowCache, cls).__new__(cls)
        return cls._instance
    

    def __init__(self, workflow_dir):
        if not hasattr(self, 'initialized'): 
            if not workflow_dir.exists():
                logger.info(f"path {workflow_dir} does not exist when workflow cache initializing, gona to create...")
                workflow_dir.mkdir(parents=True, exist_ok=True)
            self.workflow_dir = workflow_dir
            self.queue = {}
            self.cache = {}
            self.latest_polish_id = {}
            self.initialized = True
            
    def _load_workflow(self, user_id: str):
        user_workflow_dir = self.workflow_dir / user_id
        if not user_workflow_dir.exists():
            logger.info(f"path {user_workflow_dir} does not exist when user {user_id} workflow cache initializing, gona to create...")
            user_workflow_dir.mkdir(parents=True, exist_ok=True)

        user_workflow_files = user_workflow_dir.glob("*.json")
        for workflow_file in user_workflow_files:
            with open(workflow_file, "r") as f:
                workflow = json.load(f)
                self.cache[workflow["workflow_id"]] = workflow        

    def init_cache(self, user_id: str, lap: int, mode: str, workflow_id: str, version: int, user_input_messages: list, deep_thinking_mode: bool, search_before_planning: bool, coor_agents: list[str], load_user_workflow: bool = True):
        try:
            self._load_workflow(user_id)
            if mode == "launch":
                self.cache[workflow_id] = WORKFLOW_TEMPLATE.copy()
                self.cache[workflow_id]["mode"] = mode
                self.cache[workflow_id]["lap"] = lap
                self.cache[workflow_id]["workflow_id"] = workflow_id
                self.cache[workflow_id]["version"] = version
                self.cache[workflow_id]["user_input_messages"] = user_input_messages
                self.cache[workflow_id]["deep_thinking_mode"] = deep_thinking_mode
                self.cache[workflow_id]["search_before_planning"] = search_before_planning
                self.cache[workflow_id]["coor_agents"] = coor_agents
            else:
                try:                  
                    if workflow_id not in self.cache:
                        user_id, polish_id = workflow_id.split(":")
                        user_workflow_dir = self.workflow_dir / user_id
                        user_workflow_file = user_workflow_dir / polish_id
                        with open(user_workflow_file, 'r') as f:
                            workflow = json.load(f)
                            if workflow:
                                self.cache[workflow["workflow_id"]] = workflow
                            else:
                                logger.error(f"Error loading workflow {user_workflow_file} for user {user_id}: {e}")
                                raise Exception(f"Error loading workflow {user_workflow_file} for user {user_id}")
                            
                    self.queue[workflow_id] = deque()
                    for agent in self.cache[workflow_id]["graph"]:
                        if agent["node_type"] == "execution_agent":
                            self.queue[workflow_id].append(agent)
                except Exception as e:
                    logger.error(f"Error initializing workflow cache: {e}")
                    raise e
        except Exception as e:
            logger.error(f"Error initializing workflow cache: {e}")
            raise e
    
    def list_workflows(self, user_id: str, match: str = None):
        self._load_workflow(user_id)
        user_workflow_dir = self.workflow_dir / user_id
        user_workflow_files = user_workflow_dir.glob("*.json")
        workflows = []
        for workflow_file in user_workflow_files:
            filename = workflow_file.stem
            if match:
                if re.match(match, filename):
                    workflows.append(self.cache[user_id + ":" + filename])
            else:
                workflows.append(self.cache[user_id + ":" + filename])
        return workflows
            
    def get_latest_polish_id(self, user_id: str):
        if user_id not in self.latest_polish_id or not self.latest_polish_id[user_id]:
            user_workflow_dir = self.workflow_dir / user_id
            latest_file = None
            latest_mtime = 0
            polish_id_to_set = None

            if user_workflow_dir.exists():
                workflow_files = list(user_workflow_dir.glob("*.json"))
                if workflow_files:
                    for workflow_file in workflow_files:
                        try:
                            mtime = os.path.getmtime(workflow_file)
                            if mtime > latest_mtime:
                                latest_mtime = mtime
                                latest_file = workflow_file
                        except OSError as e:
                            logger.warning(f"Could not get mtime for {workflow_file}: {e}")
                    
                    if latest_file:
                        polish_id_to_set = latest_file.stem # filename without extension
                        try:
                            with open(latest_file, "r") as f:
                                workflow_data = json.load(f)
                                workflow_id = user_id + ":" + polish_id_to_set
                                self.cache[workflow_id] = workflow_data
                            logger.info(f"Loaded latest polish workflow {polish_id_to_set} for user {user_id} from {latest_file}")
                        except Exception as e:
                            logger.error(f"Error loading latest polish workflow {latest_file} for user {user_id}: {e}")
                            polish_id_to_set = None # Failed to load
            
                        self.latest_polish_id[user_id] = polish_id_to_set
            if polish_id_to_set is None:
                logger.info(f"No suitable polish workflow found for user {user_id} in {user_workflow_dir}")

        return self.latest_polish_id.get(user_id)
        
    def restore_planning_steps(self, workflow_id: str, planning_steps):
        try:
            self.cache[workflow_id]["planning_steps"] = planning_steps
        except Exception as e:
            logger.error(f"Error restoring planning steps: {e}")
            self.cache[workflow_id]["planning_steps"] = []

    def get_planning_steps(self, workflow_id: str):
        try:
            return self.cache[workflow_id]["planning_steps"]
        except Exception as e:
            logger.error(f"Error getting planning steps: {e}")
            
    def update_stack(self, workflow_id: str, agent: Agent):
        self.queue[workflow_id].popleft()
    
    def get_next_node(self, workflow_id: str):
        try:
            if not self.queue[workflow_id][0]["next_to"] or self.queue[workflow_id][0]["next_to"][0] == "__end__":
                return "FINISH"
            else:
                return self.queue[workflow_id][0]["next_to"][0]
             
        except Exception as e:
            logger.error(f"Error getting next node: {e}")
            return "FINISH"
    
    def get_lap(self, workflow_id: str):
        try:
            return self.cache[workflow_id]["lap"]
        except Exception as e:
            logger.error(f"Error getting lap: {e}")
                 
    def restore_node(self, workflow_id: str, node: Union[Agent, str]):
        try:
            if isinstance(node, Agent):
                _agent = node
                if _agent.agent_name not in self.cache[workflow_id]["agent_nodes"]:
                    self.cache[workflow_id]["agent_nodes"][_agent.agent_name] = {
                        "type": "execution_agent",
                        "agent_name": _agent.agent_name,
                        "agent":_agent.model_dump_json()
                    }
                self.cache[workflow_id]["graph"].append({
                    "node_name": _agent.agent_name,
                    "node_type": "execution_agent",
                    "next_to": [],
                    "condition": "supervised"
                })
                
                self.queue[workflow_id].append(node)

            elif isinstance(node, str):
                _next_to = node
                if self.cache[workflow_id]["graph"][-1]["node_type"] == "execution_agent":
                    if not self.cache[workflow_id]["graph"][-1]["next_to"]:
                        self.cache[workflow_id]["graph"][-1]["next_to"].append(_next_to)
        except Exception as e:
            logger.error(f"Error restore_node: {e}")
        
            
        
    def dump(self, workflow_id: str, mode: str):
        try:
            if mode == "launch":
                workflow = self.cache[workflow_id]
                user_id, polish_id = workflow["workflow_id"].split(":")
                workflow_path = self.workflow_dir / user_id / f"{polish_id}.json"
                with open(workflow_path, "w") as f:
                    f.write(json.dumps(workflow, indent=2, ensure_ascii=False))
                self.latest_polish_id[user_id] = polish_id
            elif mode == "production":
                self.queue[workflow_id] = []
        except Exception as e:
            logger.error(f"Error dumping workflow: {e}")
            
    def get_editable_agents(self, workflow_id: str):
        try:
            agents = []
            for node in self.cache[workflow_id]["graph"]:
                agent_path = agents_dir / f"{node.node_name}.json"
                with open(agent_path, "r") as f:
                    json_str = f.read()
                    _agent = Agent.model_validate_json(json_str)                
                agents.append(_agent)
            return agents
        except Exception as e:
            logger.error(f"Error getting agents: {e}")
            return []
         
        
        
from config.global_variables import workflows_dir

workflow_cache = WorkflowCache(workflow_dir=workflows_dir)
