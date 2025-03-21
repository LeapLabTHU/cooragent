import os
import re
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt.chat_agent_executor import AgentState
from src.interface.agent_types import Prompt, PromptArgument

def get_prompt_template(prompt_name: str) -> str:
    template = open(os.path.join(os.path.dirname(__file__), f"{prompt_name}.md")).read()
    
    # 提取模板中的变量名（格式为 <<VAR>>）
    variables = re.findall(r"<<([^>>]+)>>", template)
    
    # Escape curly braces using backslash
    
    template = template.replace("{", "{{").replace("}", "}}")
    # Replace `<<VAR>>` with `{VAR}`
    template = re.sub(r"<<([^>>]+)>>", r"{\1}", template)
    
    return template, variables


def apply_prompt_template(prompt_name: str, state: AgentState, template:str=None) -> list:
    _template, _ = get_prompt_template(prompt_name, template)  if not template else template
    system_prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=_template,
    ).format(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **state)
    return [{"role": "system", "content": system_prompt}] + state["messages"]

def get_structured_prompt(prompt_name: str) -> str:
    _template, _variables = get_prompt_template(prompt_name)
    
    vars = [PromptArgument(name=v, description="", required=True) for v in _variables]
    
    return Prompt(
        name=prompt_name,
        description="",
        arguments=vars,
        content=_template
    )
    