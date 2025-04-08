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
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv
import functools
import shlex
import readline
import atexit
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

from src.interface.agent_types import *
from src.service.app import Server

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

HISTORY_FILE = os.path.expanduser("~/.cooragent_history")

def _init_readline():
    try:
        readline.parse_and_bind(r'"\C-?": backward-kill-word') 
        readline.parse_and_bind(r'"\e[3~": delete-char')        
        readline.parse_and_bind('set editing-mode emacs') 
        readline.parse_and_bind('set horizontal-scroll-mode on')
        readline.parse_and_bind('set bell-style none')
        
        history_dir = os.path.dirname(HISTORY_FILE)
        if not os.path.exists(history_dir):
            os.makedirs(history_dir, exist_ok=True)
        
        if not os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                pass
        
        try:
            readline.read_history_file(HISTORY_FILE)
        except:
            pass
        
        readline.set_history_length(1000)
        atexit.register(_save_history)
        
    except Exception as e:
        console.print(f"[warning]命令历史初始化失败: {str(e)}[/warning]")

def _save_history():
    """安全保存历史记录"""
    try:
        readline.write_history_file(HISTORY_FILE)
    except Exception as e:
        console.print(f"[warning]无法保存命令历史: {str(e)}[/warning]")


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


def init_server(ctx):
    """global init function"""
    if not ctx.obj.get('_initialized', False):
        with console.status("[bold green]正在初始化服务器...[/]", spinner="dots"):
            _init_readline()
            print_banner()
            ctx.obj['server'] = Server()
            ctx.obj['_initialized'] = True
        console.print("[success]✓ 服务器初始化完成[/]")

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """CoorAgent 命令行工具"""
    ctx.ensure_object(dict)
    init_server(ctx)
    
    if ctx.invoked_subcommand is None:
        console.print("输入 'exit' 退出交互模式\n")
        should_exit = False
        while not should_exit:
            try:
                command = input("\001\033[1;36m\002CoorAgent>\001\033[0m\002 ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ('exit', 'quit'):
                    console.print("[success]再见！[/]")
                    should_exit = True
                    break
                
                if command and not command.lower().startswith(('exit', 'quit')):
                    readline.add_history(command)
                
                args = shlex.split(command)
                with cli.make_context("cli", args, parent=ctx) as sub_ctx:
                    cli.invoke(sub_ctx)
                    
            except Exception as e:
                console.print(f"[danger]错误: {str(e)}[/]")
        return


@cli.command()
@click.pass_context
@click.option('--user-id', '-u', default="test", help='用户ID')
@click.option('--task-type', '-t', required=True, 
              type=click.Choice([task_type.value for task_type in TaskType]), 
              help='任务类型 (可选值: agent_factory, agent_workflow)')
@click.option('--message', '-m', required=True, multiple=True, help='消息内容 (可多次使用此选项添加多条消息)')
@click.option('--debug/--no-debug', default=False, help='是否开启调试模式')
@click.option('--deep-thinking/--no-deep-thinking', default=True, help='是否开启深度思考模式')
@click.option('--agents', '-a', multiple=True, help='协作Agent列表 (可多次使用此选项添加多个Agent)')
@async_command
async def run(ctx, user_id, task_type, message, debug, deep_thinking, agents):

    server = ctx.obj['server']
    
    config_table = Table(title="工作流配置", show_header=True, header_style="bold magenta")
    config_table.add_column("参数", style="cyan")
    config_table.add_column("值", style="green")
    config_table.add_row("用户ID", user_id)
    config_table.add_row("任务类型", task_type)
    config_table.add_row("调试模式", "✅ 开启" if debug else "❌ 关闭")
    config_table.add_row("深度思考", "✅ 开启" if deep_thinking else "❌ 关闭")
    config_table.add_row("协作Agent", ", ".join(agents) if agents else "无")
    console.print(config_table)
    
    msg_table = Table(title="消息历史", show_header=True, header_style="bold magenta")
    msg_table.add_column("角色", style="cyan")
    msg_table.add_column("内容", style="green")
    for i, msg in enumerate(message):
        role = "用户" if i % 2 == 0 else "助手"
        style = "user_msg" if i % 2 == 0 else "assistant_msg"
        msg_table.add_row(role, Text(msg, style=style))
    console.print(msg_table)
    
    messages = []
    for i, msg in enumerate(message):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": msg})
    
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
    
    console.print(Panel.fit("[highlight]工作流开始执行[/highlight]", title="CoorAgent", border_style="cyan"))
    
    current_content = ""
    json_buffer = ""  
    in_json_block = False  
    
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
            
            if event_type == "start_of_agent":
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                agent_name = data.get("agent_name", "未知")
                progress.update(task, description=f"[green]正在执行: {agent_name}...")
                console.print(f"\n[agent_name]>>> {agent_name} 开始执行...[/agent_name]")
            
            elif event_type == "end_of_agent":
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                agent_name = data.get("agent_name", "未知")
                progress.update(task, description=f"[success]{agent_name} 执行完成!")
                console.print(f"\n[agent_name]<<< {agent_name} 执行完成[/agent_name]")
                
    
                if current_content:
                    console.print("\n", end="")
                    current_content = ""
            
            elif event_type == "message":
                delta = data.get("delta", {})
                content = delta.get("content", "")
                reasoning = delta.get("reasoning_content", "")
                message_id = data.get("message_id")
                node = data.get("node", "")
                
                # check if content is json
                if content and (content.strip().startswith("{") or in_json_block):
                    # if new json block
                    if not in_json_block:
                        in_json_block = True
                        json_buffer = ""
                    
                    
                    json_buffer += content
                    
                    # try to parse complete json
                    try:
                        agent_name = data.get("agent_name", "")
                        parsed_json = json.loads(json_buffer)
                        # if parse success, json is complete
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  # ensure new line
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                        json_buffer = ""
                        in_json_block = False
                    except:
                        pass
                else:
                        # if not json, just output
                    if content:
                        content = content.replace('\n', ' ')
                        console.print(content, end="", highlight=False)
                
                # if there is reasoning content, show in different style
                if reasoning:
                    console.print(f"\n[info]思考过程: {reasoning}[/info]")
            
            elif event_type == "tool_call":
                # ensure new line
                if current_content and not current_content.endswith("\n"):
                    print("\n", end="", flush=True)
                
                tool_name = data.get("tool_name", "未知工具")
                tool_input = data.get("tool_input", {})
                formatted_input = json.dumps(tool_input, indent=2, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input)
                console.print(f"\n[tool_name]调用工具: {tool_name}[/tool_name]")
                syntax = Syntax(formatted_input, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
            
            elif event_type == "tool_call_result":
                if current_content and not current_content.endswith("\n"):
                    print("\n", end="", flush=True)
                
                tool_name = data.get("tool_name", "未知工具")
                tool_result = data.get("tool_result", "")
                console.print(f"\n[tool_name]工具 {tool_name} 返回结果:[/tool_name]")
                
                try:
                    result_json = json.loads(tool_result)
                    formatted_result = json.dumps(result_json, indent=2, ensure_ascii=False)
                    syntax = Syntax(formatted_result, "json", theme="monokai", line_numbers=False)
                    console.print(syntax)
                except:
                    try:
                        md = Markdown(tool_result)
                        console.print(md)
                    except:
                        console.print(tool_result)
            
            elif event_type == "end_of_workflow":
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                progress.update(task, description="[success]工作流执行完成!")
                console.print(Panel.fit("[success]工作流执行完成![/success]", title="CoorAgent", border_style="green"))
    
    console.print(Panel.fit("[success]工作流执行完成![/success]", title="CoorAgent", border_style="green"))


@cli.command()
@click.pass_context
@click.option('--user-id', '-u', required=True, help='用户ID')
@click.option('--match', '-m', default="", help='匹配字符串')
@async_command 
async def list_agents(ctx, user_id, match):
    """列出用户的Agent"""
    # 从上下文中获取server
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在获取Agent列表...", total=None)
        
        request = listAgentRequest(user_id=user_id, match=match)
        
        table = Table(title=f"用户 [highlight]{user_id}[/highlight] 的Agent列表", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("名称", style="agent_name")
        table.add_column("描述", style="agent_desc")
        table.add_column("工具", style="agent_type")
        
        count = 0
        async for agent_json in server._list_agents(request):
            try:
                agent = json.loads(agent_json)
                tools = []
                for tool in agent.get("selected_tools", []):
                    tools.append(tool.get("name", ""))
                table.add_row(agent.get("agent_name", ""), agent.get("description", ""), ', '.join(tools))
                count += 1
            except:
                console.print(f"[danger]解析错误: {agent_json}[/danger]")
        
        progress.update(task, description=f"[success]已获取 {count} 个Agent!")
        
        if count == 0:
            console.print(Panel(f"未找到匹配的Agent", title="结果", border_style="yellow"))
        else:
            console.print(table)


@cli.command()
@click.pass_context
@async_command  # 使用异步命令装饰器
async def list_default_agents(ctx):
    """列出默认Agent"""
    # 从上下文中获取server
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在获取默认Agent列表...", total=None)
        
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
@click.pass_context
@async_command  # 使用异步命令装饰器
async def list_default_tools(ctx):
    """列出默认工具"""
    # 从上下文中获取server
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]正在获取默认工具列表...", total=None)
        
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
@click.pass_context
@click.option('--agent-name', '-n', required=True, help='要编辑的Agent名称')
@click.option('--user-id', '-u', required=True, help='用户ID')
@click.option('--interactive/--no-interactive', '-i/-I', default=True, help='是否使用交互模式')
@async_command
async def edit_agent(ctx, agent_name, user_id, interactive):
    """编辑Agent配置（交互模式）"""
    # 从上下文中获取server
    server = ctx.obj['server']
    
    # 获取当前Agent配置
    console.print(Panel.fit(f"[highlight]正在获取 {agent_name} 的配置...[/highlight]", border_style="cyan"))
    original_config = None
    try:
        async for agent_json in server._list_agents(listAgentRequest(user_id=user_id, match=agent_name)):
            agent = json.loads(agent_json)
            if agent.get("agent_name") == agent_name:
                original_config = agent
                break
        if not original_config:
            console.print(f"[danger]未找到Agent: {agent_name}[/danger]")
            return
    except Exception as e:
        console.print(f"[danger]获取配置失败: {str(e)}[/danger]")
        return

    # 显示当前配置
    def show_current_config():
        console.print(Panel.fit(
            f"[agent_name]名称:[/agent_name] {original_config.get('agent_name', '')}\n"
            f"[agent_nick_name]昵称:[/agent_nick_name] {original_config.get('nick_name', '')}\n"
            f"[agent_desc]描述:[/agent_desc] {original_config.get('description', '')}\n"
            f"[tool_name]工具:[/tool_name] {', '.join([t.get('name', '') for t in original_config.get('selected_tools', [])])}\n"
            f"[highlight]提示词:[/highlight]\n{original_config.get('prompt', '')}",
            title="当前配置",
            border_style="blue"
        ))
    
    show_current_config()

    # 交互式编辑
    modified_config = original_config.copy()
    while interactive:
        # 显示选项菜单
        console.print("\n请选择要修改的内容：")
        console.print("1 - 修改昵称")
        console.print("2 - 修改描述")
        console.print("3 - 修改工具列表")
        console.print("4 - 修改提示词")
        console.print("5 - 预览修改")
        console.print("0 - 保存退出")
        
        # 直接接收数字输入
        choice = Prompt.ask(
            "请输入选项",
            choices=["0", "1", "2", "3", "4", "5"],
            show_choices=False
        )
        
        # 不需要再分割，直接使用输入的数字
        if choice == "1":
            new_name = Prompt.ask(
                "输入新昵称", 
                default=modified_config.get('nick_name', ''),
                show_default=True
            )
            modified_config['nick_name'] = new_name
        
        elif choice == "2":
            new_desc = Prompt.ask(
                "输入新描述", 
                default=modified_config.get('description', ''),
                show_default=True
            )
            modified_config['description'] = new_desc
        
        elif choice == "3":
            current_tools = [t.get('name') for t in modified_config.get('selected_tools', [])]
            console.print(f"当前工具: {', '.join(current_tools)}")
            new_tools = Prompt.ask(
                "输入新工具列表（逗号分隔）",
                default=", ".join(current_tools),
                show_default=True
            )
            modified_config['selected_tools'] = [
                {"name": t.strip(), "description": ""} 
                for t in new_tools.split(',') 
                if t.strip()
            ]
        
        elif choice == "4":
            console.print("输入新提示词（输入'END'结束）:")
            lines = []
            while True:
                line = Prompt.ask("> ", default="")
                if line == "END":
                    break
                lines.append(line)
            modified_config['prompt'] = "\n".join(lines)
        
        elif choice == "5":
            show_current_config()
            console.print(Panel.fit(
                f"[agent_name]新名称:[/agent_name] {modified_config.get('agent_name', '')}\n"
                f"[nick_name]新昵称:[/nick_name] {modified_config.get('nick_name', '')}\n"
                f"[agent_desc]新描述:[/agent_desc] {modified_config.get('description', '')}\n"
                f"[tool_name]新工具:[/tool_name] {', '.join([t.get('name', '') for t in modified_config.get('selected_tools', [])])}\n"
                f"[highlight]新提示词:[/highlight]\n{modified_config.get('prompt', '')}",
                title="修改后的配置",
                border_style="yellow"
            ))
        
        elif choice == "0":
            if Confirm.ask("确认保存修改吗？"):
                try:
                    # 构建Agent请求对象
                    agent_request = Agent(
                        user_id=original_config.get('user_id', ''),
                        nick_name=modified_config['nick_name'],
                        agent_name=modified_config['agent_name'],
                        description=modified_config['description'],
                        selected_tools=modified_config['selected_tools'],
                        prompt=modified_config['prompt'],
                        llm_type=original_config.get('llm_type', 'basic')
                    )
                    
                    # 调用服务保存修改
                    async for result in server._edit_agent(agent_request):
                        res = json.loads(result)
                        if res.get("result") == "success":
                            console.print(Panel.fit("[success]Agent 更新成功![/success]", border_style="green"))
                        else:
                            console.print(f"[danger]更新失败: {res.get('result', '未知错误')}[/danger]")
                    return
                except Exception as e:
                    console.print(f"[danger]保存时发生错误: {str(e)}[/danger]")
            else:
                console.print("[warning]修改已取消[/warning]")
            return


@cli.command()
def help():
    """显示帮助信息"""
    help_table = Table(title="帮助信息", show_header=False, border_style="cyan", width=100)
    help_table.add_column(style="bold cyan")
    help_table.add_column(style="green")
    
    help_table.add_row("[命令] run", "运行工作流")
    help_table.add_row("  -u/--user-id", "用户ID")
    help_table.add_row("  -t/--task-type", "任务类型 (agent_factory/agent_workflow)")
    help_table.add_row("  -m/--message", "消息内容 (可多次使用)")
    help_table.add_row("  --debug", "开启调试模式")
    help_table.add_row("  --no-deep-thinking", "关闭深度思考模式")
    help_table.add_row("  -a/--agents", "协作Agent列表")
    help_table.add_row()
    
    help_table.add_row("[命令] list-agents", "列出用户Agent")
    help_table.add_row("  -u/--user-id", "用户ID (必填)")
    help_table.add_row("  -m/--match", "匹配字符串")
    help_table.add_row()
    
    help_table.add_row("[命令] list-default-agents", "列出默认Agent")
    help_table.add_row("[命令] list-default-tools", "列出默认工具")
    help_table.add_row()
    
    help_table.add_row("[命令] edit-agent", "交互式编辑Agent")
    help_table.add_row("  -n/--agent-name", "Agent名称 (必填)")
    help_table.add_row("  -i/--interactive", "交互模式")
    help_table.add_row()
    
    help_table.add_row("[交互模式]", "直接运行 cli.py 进入")
    help_table.add_row("  exit/quit", "退出交互模式")
    
    console.print(help_table)


if __name__ == "__main__":
    try:
        # 不再使用asyncio.run包装cli()
        cli()
    except KeyboardInterrupt:
        console.print("\n[warning]操作已取消[/warning]")
    except Exception as e:
        console.print(f"\n[danger]发生错误: {str(e)}[/danger]")
