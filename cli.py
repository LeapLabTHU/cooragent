#!/usr/bin/env python
import os
import json
import asyncio
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.theme import Theme
from rich.style import Style
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from dotenv import load_dotenv
import functools

load_dotenv()

from src.interface.agent_types import *
from src.service.app import Server
from src.service.session import UserSession

# 自定义主题，增加更多颜色
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "command": "bold yellow",
    "highlight": "bold cyan",
    "agent_name": "bold blue",
    "agent_desc": "green",
    "agent_type": "magenta",
    "tool_name": "bold blue",
    "tool_desc": "green",
    "user_msg": "bold white on blue",
    "assistant_msg": "bold black on green",
})

# 创建Rich控制台对象用于美化输出
console = Console(theme=custom_theme)


def print_banner():
    """打印漂亮的横幅"""
    banner = """
							    ╔═══════════════════════════════════════════════════════════════════════════════╗
							    ║                                                                               ║
							    ║        ██████╗ ██████╗  ██████╗ ██████╗  █████╗  ██████╗ ███████╗███╗   ██╗████████╗    
							    ║       ██╔════╝██╔═══██╗██╔═══██╗██╔══██╗██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    
							    ║       ██║     ██║   ██║██║   ██║██████╔╝███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       
							    ║       ██║     ██║   ██║██║   ██║██╔══██╗██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       
							    ║       ╚██████╗╚██████╔╝╚██████╔╝██║  ██║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       
							    ║        ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       
							    ║                                                                               ║
							    ╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(Text(banner, style="bold cyan"), border_style="green"))
    console.print("欢迎使用 [highlight]CoorAgent[/highlight] Cooragent 是一个 AI 智能体协作社区，在这个社区中，你可以通过一句话创建一个特定功能的智能体，并与其他智能体协作完成复杂任务。智能体可以自由组合，创造出无限可能。与此同时，你还可以将你的智能体发布到社区中，与其他人共享。！\n", justify="center")


# 添加异步命令处理装饰器
def async_command(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@click.group()
def cli():
    """CoorAgent 命令行工具 - 直接调用Agent功能"""
    print_banner()


@cli.command()
@click.option('--user-id', '-u', default="test", help='用户ID')
@click.option('--task-type', '-t', required=True, 
              type=click.Choice([task_type.value for task_type in TaskType]), 
              help='任务类型 (可选值: agent_factory, agent_workflow)')
@click.option('--message', '-m', required=True, multiple=True, help='消息内容 (可多次使用此选项添加多条消息)')
@click.option('--debug/--no-debug', default=False, help='是否开启调试模式')
@click.option('--deep-thinking/--no-deep-thinking', default=True, help='是否开启深度思考模式')
@click.option('--agents', '-a', multiple=True, help='协作Agent列表 (可多次使用此选项添加多个Agent)')
@async_command  # 使用异步命令装饰器
async def run(user_id, task_type, message, debug, deep_thinking, agents):
    """运行Agent工作流"""
    # 显示配置信息
    config_table = Table(title="工作流配置", show_header=True, header_style="bold magenta")
    config_table.add_column("参数", style="cyan")
    config_table.add_column("值", style="green")
    config_table.add_row("用户ID", user_id)
    config_table.add_row("任务类型", task_type)
    config_table.add_row("调试模式", "✅ 开启" if debug else "❌ 关闭")
    config_table.add_row("深度思考", "✅ 开启" if deep_thinking else "❌ 关闭")
    config_table.add_row("协作Agent", ", ".join(agents) if agents else "无")
    console.print(config_table)
    
    # 显示消息历史
    msg_table = Table(title="消息历史", show_header=True, header_style="bold magenta")
    msg_table.add_column("角色", style="cyan")
    msg_table.add_column("内容", style="green")
    for i, msg in enumerate(message):
        role = "用户" if i % 2 == 0 else "助手"
        style = "user_msg" if i % 2 == 0 else "assistant_msg"
        msg_table.add_row(role, Text(msg, style=style))
    console.print(msg_table)
    
    # 构建消息列表
    messages = []
    for i, msg in enumerate(message):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": msg})
    
    # 构建请求对象
    request = AgentRequest(
        user_id=user_id,
        lang="zh",
        task_type=task_type,
        messages=messages,
        debug=debug,
        deep_thinking_mode=deep_thinking,
        search_before_planning=True,
        coor_agents=list(agents)
    )
    
    # 调用工作流
    console.print(Panel.fit("[highlight]工作流开始执行[/highlight]", title="CoorAgent", border_style="cyan"))
    server = Server()
    
    # 用于累积内容的变量
    current_agent = None
    current_content = ""
    current_message_id = None
    json_buffer = ""  # 用于累积JSON内容
    in_json_block = False  # 标记是否在JSON块内
    
    # 使用Progress组件显示进度
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True 
    ) as progress:
        task = progress.add_task("[green]正在处理请求...", total=None)
        
        async for chunk in server._run_agent_workflow(request):
            event_type = chunk.get("event")
            data = chunk.get("data", {})
            
            # 更新进度条描述
            if event_type == "start_of_agent":
                # 如果之前在处理JSON，确保完成输出
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  # 确保新行开始
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                agent_name = data.get("agent_name", "未知")
                progress.update(task, description=f"[green]正在执行: {agent_name}...")
                current_agent = agent_name
                console.print(f"\n[agent_name]>>> {agent_name} 开始执行...[/agent_name]")
            
            elif event_type == "end_of_agent":
                # 如果之前在处理JSON，确保完成输出
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  # 确保新行开始
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                agent_name = data.get("agent_name", "未知")
                progress.update(task, description=f"[success]{agent_name} 执行完成!")
                console.print(f"\n[agent_name]<<< {agent_name} 执行完成[/agent_name]")
                current_agent = None
                
                # 确保当前内容已完全输出
                if current_content:
                    console.print("\n", end="")
                    current_content = ""
            
            elif event_type == "message":
                # 获取消息内容
                delta = data.get("delta", {})
                content = delta.get("content", "")
                reasoning = delta.get("reasoning_content", "")
                message_id = data.get("message_id")
                
                # 检测是否是JSON内容
                if content and (content.strip().startswith("{") or in_json_block):
                    # 如果是新的JSON块
                    if not in_json_block:
                        in_json_block = True
                        json_buffer = ""
                    
                    # 累积JSON内容
                    json_buffer += content
                    
                    # 尝试解析完整的JSON
                    try:
                        parsed_json = json.loads(json_buffer)
                        # 如果解析成功，说明JSON完整了
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  # 确保新行开始
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                        json_buffer = ""
                        in_json_block = False
                    except:
                        # JSON不完整，继续累积
                        pass
                else:
                    # 如果不是JSON内容，直接输出
                    if content:
                        # 替换掉内容中的换行符，避免不自然的换行
                        content = content.replace('\n', ' ')
                        console.print(content, end="", highlight=False)
                
                # 如果有推理内容，显示在不同的样式中
                if reasoning:
                    console.print(f"\n[info]思考过程: {reasoning}[/info]")
            
            elif event_type == "tool_call":
                # 确保在新行开始
                if current_content and not current_content.endswith("\n"):
                    print("\n", end="", flush=True)
                
                tool_name = data.get("tool_name", "未知工具")
                tool_input = data.get("tool_input", {})
                formatted_input = json.dumps(tool_input, indent=2, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input)
                console.print(f"\n[tool_name]调用工具: {tool_name}[/tool_name]")
                syntax = Syntax(formatted_input, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
            
            elif event_type == "tool_call_result":
                # 确保在新行开始
                if current_content and not current_content.endswith("\n"):
                    print("\n", end="", flush=True)
                
                tool_name = data.get("tool_name", "未知工具")
                tool_result = data.get("tool_result", "")
                console.print(f"\n[tool_name]工具 {tool_name} 返回结果:[/tool_name]")
                
                # 尝试解析为JSON
                try:
                    result_json = json.loads(tool_result)
                    formatted_result = json.dumps(result_json, indent=2, ensure_ascii=False)
                    syntax = Syntax(formatted_result, "json", theme="monokai", line_numbers=False)
                    console.print(syntax)
                except:
                    # 尝试解析为Markdown
                    try:
                        md = Markdown(tool_result)
                        console.print(md)
                    except:
                        console.print(tool_result)
            
            elif event_type == "end_of_workflow":
                # 如果之前在处理JSON，确保完成输出
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  # 确保新行开始
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                progress.update(task, description="[success]工作流执行完成!")
                console.print(Panel.fit("[success]工作流执行完成![/success]", title="CoorAgent", border_style="green"))
    
    # 工作流结束
    console.print(Panel.fit("[success]工作流执行完成![/success]", title="CoorAgent", border_style="green"))


@cli.command()
@click.option('--user-id', '-u', required=True, help='用户ID')
@click.option('--match', '-m', default="", help='匹配字符串')
@async_command 
async def list_agents(user_id, match):
    """列出用户的Agent"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在获取Agent列表...", total=None)
        
        request = listAgentRequest(user_id=user_id, match=match)
        server = Server()
        
        table = Table(title=f"用户 [highlight]{user_id}[/highlight] 的Agent列表", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("名称", style="agent_name")
        table.add_column("描述", style="agent_desc")
        table.add_column("类型", style="agent_type")
        
        count = 0
        async for agent_json in server._list_agents(request):
            try:
                agent = json.loads(agent_json)
                table.add_row(agent.get("name", ""), agent.get("description", ""), agent.get("type", ""))
                count += 1
            except:
                console.print(f"[danger]解析错误: {agent_json}[/danger]")
        
        progress.update(task, description=f"[success]已获取 {count} 个Agent!")
        
        if count == 0:
            console.print(Panel(f"未找到匹配的Agent", title="结果", border_style="yellow"))
        else:
            console.print(table)


@cli.command()
@async_command  # 使用异步命令装饰器
async def list_default_agents():
    """列出默认Agent"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在获取默认Agent列表...", total=None)
        
        server = Server()
        
        table = Table(title="默认Agent列表", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("名称", style="agent_name")
        table.add_column("描述", style="agent_desc")
        
        count = 0
        async for agent_json in server._list_default_agents():
            try:
                agent = json.loads(agent_json)
                table.add_row(agent.get("agent_name", ""), agent.get("description", ""))
                count += 1
            except:
                console.print(f"[danger]解析错误: {agent_json}[/danger]")
        
        progress.update(task, description=f"[success]已获取 {count} 个默认Agent!")
        console.print(table)


@cli.command()
@async_command  # 使用异步命令装饰器
async def list_default_tools():
    """列出默认工具"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在获取默认工具列表...", total=None)
        
        server = Server()
        
        table = Table(title="默认工具列表", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("名称", style="tool_name")
        table.add_column("描述", style="tool_desc")
        
        count = 0
        async for tool_json in server._list_default_tools():
            try:
                tool = json.loads(tool_json)
                table.add_row(tool.get("name", ""), tool.get("description", ""))
                count += 1
            except:
                console.print(f"[danger]解析错误: {tool_json}[/danger]")
        
        progress.update(task, description=f"[success]已获取 {count} 个默认工具!")
        console.print(table)


@cli.command()
@click.option('--agent-name', '-n', help='Agent名称')
@click.option('--interactive/--no-interactive', '-i/-n', default=False, help='是否使用交互模式')
@async_command  # 使用异步命令装饰器
async def edit_agent(agent_name, interactive):
    """
    Edit an existing agent configuration.
    
    Args:
        agent_name (str): The name of the agent to edit
        interactive (bool): Whether to use interactive mode
    """
    # 查找当前 agent 的配置
    agent_path = os.path.join("store", "agents", f"{agent_name}.json")
    
    if not os.path.exists(agent_path):
        print(f"Agent '{agent_name}' not found.")
        return
    
    # 加载当前 agent 配置
    with open(agent_path, "r") as f:
        agent_config = json.load(f)
    
    if interactive:
        # 交互式编辑
        print(f"Editing agent: {agent_name}")
        print("Current configuration:")
        print(json.dumps(agent_config, indent=2))
        
        # 修改 agent 名称
        new_name = input(f"Agent name [{agent_config.get('agent_name', '')}]: ")
        if new_name:
            agent_config['agent_name'] = new_name
        
        # 修改 agent 描述
        new_description = input(f"Agent description [{agent_config.get('description', '')}]: ")
        if new_description:
            agent_config['description'] = new_description
        
        # 修改 LLM 类型
        llm_types = ["basic", "vision"]
        current_llm = agent_config.get('llm_type', 'basic')
        print(f"Current LLM type: {current_llm}")
        print("Available LLM types:")
        for i, llm_type in enumerate(llm_types):
            print(f"{i+1}. {llm_type}")
        llm_choice = input(f"Select LLM type (1-{len(llm_types)}) [{llm_types.index(current_llm)+1}]: ")
        if llm_choice and llm_choice.isdigit() and 1 <= int(llm_choice) <= len(llm_types):
            agent_config['llm_type'] = llm_types[int(llm_choice)-1]
        
        # 修改工具
        print("Current tools:")
        for i, tool in enumerate(agent_config.get('selected_tools', [])):
            print(f"{i+1}. {tool.get('name', 'Unknown tool')}")
        
        # 这里可以添加工具编辑逻辑
        # ...
        
        # 修改提示词
        edit_prompt = input("Edit prompt? (y/n): ").lower() == 'y'
        if edit_prompt:
            current_prompt = agent_config.get('prompt', '')
            # 可以使用外部编辑器或者多行输入
            print("Enter new prompt (type 'END' on a new line to finish):")
            lines = []
            while True:
                line = input()
                if line == "END":
                    break
                lines.append(line)
            if lines:
                agent_config['prompt'] = "\n".join(lines)
    
    # 保存修改后的配置
    with open(agent_path, "w") as f:
        json.dump(agent_config, f, indent=2)
    
    print(f"Agent '{agent_name}' updated successfully.")


@cli.command()
def help():
    """显示帮助信息"""
    help_text = """
    # CoorAgent 命令行工具使用指南
    
    ## 可用命令:
    
    ### 运行Agent工作流
    ```
    python cli.py run --user-id user123 --task-type planning --message "你好" --message "我能帮你什么?" --debug
    ```
    
    ### 列出用户的Agent
    ```
    python cli.py list-agents --user-id user123
    ```
    
    ### 列出默认Agent
    ```
    python cli.py list-default-agents
    ```
    
    ### 列出默认工具
    ```
    python cli.py list-default-tools
    ```
    
    ### 编辑Agent (交互模式)
    ```
    python cli.py edit-agent --interactive
    ```
    
    ### 编辑Agent (JSON模式)
    ```
    python cli.py edit-agent --agent-json '{"name": "myagent", "description": "测试agent", "user_id": "user123"}'
    ```
    """
    
    md = Markdown(help_text)
    console.print(Panel(md, title="帮助信息", border_style="cyan"))


if __name__ == "__main__":
    try:
        # 不再使用asyncio.run包装cli()
        cli()
    except KeyboardInterrupt:
        console.print("\n[warning]操作已取消[/warning]")
    except Exception as e:
        console.print(f"\n[danger]发生错误: {str(e)}[/danger]")
