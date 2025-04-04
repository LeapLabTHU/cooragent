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
@click.option('--deep-thinking/--no-deep-thinking', default=False, help='是否开启深度思考模式')
@click.option('--agents', '-a', multiple=True, help='协作Agent列表 (可多次使用此选项添加多个Agent)')
@async_command  # 使用异步命令装饰器
async def run_workflow(user_id, task_type, message, debug, deep_thinking, agents):
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
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在处理请求...", total=None)
        
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
        progress.update(task, description="[green]工作流开始执行...")
        console.print(Panel.fit("[highlight]工作流开始执行[/highlight]", title="CoorAgent", border_style="cyan"))
        server = Server()
        
        response_panel = Panel("", title="Agent响应", border_style="green")
        console.print(response_panel)
        
        async for chunk in server._run_agent_workflow(request):
            try:
                data = json.loads(chunk)
                if isinstance(data, dict):
                    # 格式化字典输出
                    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                    syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                    console.print(syntax)
                else:
                    console.print(f"[success]{data}[/success]")
            except:
                # 尝试解析为Markdown
                try:
                    md = Markdown(chunk)
                    console.print(md)
                except:
                    console.print(f"[warning]{chunk}[/warning]")
        
        progress.update(task, description="[success]工作流执行完成!")
        console.print(Panel.fit("[success]工作流执行完成![/success]", title="CoorAgent", border_style="green"))


@cli.command()
@click.option('--user-id', '-u', required=True, help='用户ID')
@click.option('--match', '-m', default="", help='匹配字符串')
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
        table.add_column("类型", style="agent_type")
        
        count = 0
        async for agent_json in server._list_default_agents():
            try:
                agent = json.loads(agent_json)
                table.add_row(agent.get("name", ""), agent.get("description", ""), agent.get("type", ""))
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
@click.option('--agent-json', '-j', help='Agent JSON数据')
@click.option('--interactive/--no-interactive', '-i/-n', default=False, help='是否使用交互模式')
@async_command  # 使用异步命令装饰器
async def edit_agent(agent_json, interactive):
    """编辑Agent"""
    if interactive:
        console.print(Panel("[highlight]进入交互式Agent编辑模式[/highlight]", border_style="cyan"))
        name = Prompt.ask("[cyan]Agent名称[/cyan]")
        description = Prompt.ask("[cyan]Agent描述[/cyan]")
        user_id = Prompt.ask("[cyan]用户ID[/cyan]")
        agent_type = Prompt.ask("[cyan]Agent类型[/cyan]", default="default")
        
        agent_data = {
            "name": name,
            "description": description,
            "user_id": user_id,
            "type": agent_type
        }
    else:
        if not agent_json:
            console.print("[danger]错误: 非交互模式下必须提供agent-json参数[/danger]")
            return
        
        try:
            agent_data = json.loads(agent_json)
        except json.JSONDecodeError:
            console.print("[danger]JSON格式错误[/danger]")
            return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在编辑Agent...", total=None)
        
        try:
            # 显示将要编辑的Agent信息
            agent_info = Table(title="Agent信息", show_header=True, header_style="bold magenta")
            agent_info.add_column("属性", style="cyan")
            agent_info.add_column("值", style="green")
            
            for key, value in agent_data.items():
                agent_info.add_row(key, str(value))
            
            console.print(agent_info)
            
            agent = Agent(**agent_data)
            server = Server()
            
            async for result_json in server._edit_agent(agent):
                result = json.loads(result_json)
                if result.get("result") == "success":
                    progress.update(task, description="[success]Agent编辑成功!")
                    console.print(Panel("[success]Agent编辑成功![/success]", border_style="green"))
                else:
                    progress.update(task, description="[danger]Agent编辑失败!")
                    console.print(Panel(f"[danger]Agent编辑失败: {result.get('result')}[/danger]", border_style="red"))
        except Exception as e:
            progress.update(task, description="[danger]发生错误!")
            console.print(f"[danger]错误: {str(e)}[/danger]")


@cli.command()
def help():
    """显示帮助信息"""
    help_text = """
    # CoorAgent 命令行工具使用指南
    
    ## 可用命令:
    
    ### 运行Agent工作流
    ```
    python cli.py run-workflow --user-id user123 --task-type planning --message "你好" --message "我能帮你什么?" --debug
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
