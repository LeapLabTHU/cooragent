import os
import re
import logging
from datetime import datetime
import copy
from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt.chat_agent_executor import AgentState
from src.utils.path_utils import get_project_root
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)
def get_agent_task(state):

    select_agent_uuid = state["next_agent_messages"]["know_information"]
    workflow_memory= state["agent_memory"]["execution_flow"]
    know_information = ''
    uuids = []
    if select_agent_uuid:
        #check uuid
        for agent_information in workflow_memory:
            uuids.append(str(agent_information["uuid"]))
        for use_agent_uuid in select_agent_uuid:
            if use_agent_uuid not in uuids:
                logger.error("Publisher did not correctly select the uuid!!")
            else:
                for agent_information in workflow_memory:
                    if str(agent_information["uuid"]) == use_agent_uuid:
                        know_information += ('The work achievements of ' + str(agent_information["agent_name"]) + " : "
                                             + agent_information["agent_messages"] + '\n')
    task_description = state["next_agent_messages"]["task_description"]
    note = state["next_agent_messages"]["note"]
    state["TASK_DESCRIPTION"] = task_description
    state["NOTE"] = note
    state["KNOW_INFORMATION"] = know_information

def get_critic_prompt(state, response) -> list:
    _template,_ = get_prompt_template('critic')
    _prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=_template,
    ).format(HOMEWORK=response,**state)
    return [{'role':'user','content':_prompt}]


def apply_created_agent_prompt(prompt) -> str:
    _prompt =  (prompt["role_description"] +
               ("# Task"
               "TASK_DESCRIPTION -> Your main tasks are as follows, and your goal is to complete this task perfectly:"
               "<<TASK_DESCRIPTION>>"
               "KNOW_INFORMATION -> Other collaborative agents related to you have completed their work, and you can use their results:"
               "<<KNOW_INFORMATION>>"
               "NOTE -> Things you need to pay attention to during the homework process (its priority should be in line with Notes):"
               "<<NOTE>>")
                + f"# Steps:{prompt["steps"]}" + f"# Notes:{prompt["notes"]}"
                + "Please make sure to complete the task perfectly according to the steps and notes, and finally form a report."
                )
    return _prompt

def get_prompt_template(prompt_name: str) -> tuple:
    prompts_dir = get_project_root() / "src" / "prompts"
    template = open(os.path.join(prompts_dir, f"{prompt_name}.md")).read()
    
    # 提取模板中的变量名（格式为 <<VAR>>）
    variables = re.findall(r"<<([^>>]+)>>", template)
    
    # Escape curly braces using backslash
    
    template = template.replace("{", "{{").replace("}", "}}")
    # Replace `<<VAR>>` with `{VAR}`
    template = re.sub(r"<<([^>>]+)>>", r"{\1}", template)
    
    return template, variables


def apply_common_prompt(prompt_name: str, state: AgentState, template: str = None) -> list:
    state = copy.deepcopy(state)
    messages = []
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, dict) and 'role' in msg:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            else:
                messages.append({"role": "assistant", "content": msg["content"]})
    state["messages"] = messages
    _template, _ = get_prompt_template(prompt_name) if not template else template
    system_prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=_template,
    ).format(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **state)

    return [{"role": "system", "content": system_prompt}] + messages
def apply_prompt_template(prompt_name: str, state: AgentState, template:str=None) -> list:
    state = copy.deepcopy(state)
    _template, _ = get_prompt_template(prompt_name) if not template else template
    _prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=_template,
    ).format(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **state)

    return [{"role": "user", "content": _prompt}]

def decorate_prompt(template: str) -> str:
    variables = re.findall(r"<<([^>>]+)>>", template)
    template = template.replace("{", "{{").replace("}", "}}")
    # Replace `<<VAR>>` with `{VAR}`
    template = re.sub(r"<<([^>>]+)>>", r"{\1}", template)
    if "CURRENT_TIME" not in template:
        template = "Current time: {CURRENT_TIME}\n\n" + template
    return template

def apply_prompt(state: AgentState, template:str=None) -> str:
    template = decorate_prompt(template)
    _prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=template,
    ).format(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **state)
    return _prompt


def apply_publisher_prompt(state: AgentState,agent_set) -> str:
    template, _ = get_prompt_template('publisher')
    plan_content = state["agent_memory"]["plan_content"]
    execution_flow = state["agent_memory"]["execution_flow"]
    user_message = state["user_original_messages"][-1]["content"]
    use_team_members_description_template = """
    - **`{agent_name}`**: {agent_description}
    """
    all_teams_description = """
    """
    use_agent = [agent["agent_name"] for agent in state["agent_memory"]["plan_content"]["steps"]]
    use_agent = list(set(use_agent))
    for use_agent_name in use_agent:
        if use_agent_name in agent_set.keys():
            member_description = use_team_members_description_template.format(agent_name=use_agent_name,
                                                                          agent_description=agent_set[use_agent_name].description)
            all_teams_description += member_description + '\n'

    _prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=template,
    ).format(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
             plan_content = plan_content,
             execution_flow=execution_flow,
             user_message=user_message,
             ALL_TEAMS_DESCRIPTION=all_teams_description,)
    return _prompt
