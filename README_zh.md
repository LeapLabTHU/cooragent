# cooragent

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Wechat](https://img.shields.io/badge/WeChat-cooragent-brightgreen?logo=wechat&logoColor=white)](./assets/wechat_community.jpg)
[![Discord Follow](https://dcbadge.vercel.app/api/server/StFHzvmz?style=flat)](https://discord.gg/StFHzvmz)

[English](./README.md) | [简体中文](./README_zh.md)

# Cooragent 是什么

Cooragent 是一个 AI 智能体协作社区。在这个社区中，你可以通过一句话创建一个具备强大功能的智能体，并与其他智能体协作完成复杂任务。智能体可以自由组合，创造出无限可能。与此同时，你还可以将你的智能体发布到社区中，与其他人共享。

<h5 align="center">
<video src="http://coooragent.aregrid.com/coooragent0418.mp4" width="60%" alt="web browser control" controls></video>
</h5>


# 无限可能
Cooragent 有两种工作模式：**Agent Factory** 和 **Agent Workflow**。
- **Agent Factory** 模式下，你只需要你对智能体做出描述，Cooragent 就会根据你的需求生成一个智能体。Agent Factory 模式下，系统的会自动分析用户需求，通过记忆和扩展深入理解用户，省去纷繁复杂的 Prompt 设计。Planner 会在深入理解用户需求的基础上，挑选合适的工具，自动打磨 Prompt，逐步完成智能体构建。智能体构建完成后，可以立即投入使用，但你仍然可以对智能体进行编辑，优化其行为和功能。
- **Agent Workflow** 模式下你只需要描述你想要完成的目标任务，Cooragent 会自动分析任务的需求，挑选合适的智能体进行协作。Planner 根据各个智能体擅长的领域，对其进行组合并规划任务步骤和完成顺序，随后交由任务分发节点 publish 发布任务。各个智能领取自身任务，并协作完成任务。
Cooragent 可以在两种模式下不断演进，从而创造出无限可能。

# 快速安装

```bash
git clone https://github.com/LeapLabTHU/cooragent.git
cd cooragent

conda create -n cooragent python=3.12
conda activate cooragent

pip install -e .

playwright install

cp .env.example .env

python cli.py 
```

2. Installation using venv
```bash
git clone https://github.com/LeapLabTHU/cooragent.git
cd cooragent

uv python install 3.12
uv venv --python 3.12

source .venv/bin/activate  # For Windows: .venv\Scripts\activate

uv sync

# Optional: 使用 browser 工具时需要安装
playwright install

# 配置 API keys 和其他环境变量
cp .env.example .env
# Edit .env file and fill in your API keys

# 通过 CLi 本地运行
uv run cli.py 
```

## 配置

在项目根目录创建 `.env` 文件并配置以下环境变量：

```bash
cp .env.example .env
```

## Cooragent 有什么不同

## 功能比较
<table style="width: 100%;">
  <tr>
    <th align="center">功能</th>
    <th align="center">cooragent</th>
    <th align="center">open-manus</th>
    <th align="center">langmanus</th>
    <th align="center">OpenAI Assistant Operator</th>
  </tr>
  <tr>
    <td align="center">实现原理</td>
    <td align="center">基于 Agent 自主创建实现不同 Agent 之间的协作完成复杂功能</td>
    <td align="center">基于工具调用实现复杂功能</td>
    <td align="center">基于工具调用实现复杂功能</td>
    <td align="center">基于工具调用实现复杂功能</td>
  </tr>
  <tr>
    <td align="center">支持的 LLMs</td>
    <td align="center">丰富多样</td>
    <td align="center">丰富多样</td>
    <td align="center">丰富多样</td>
    <td align="center">仅限 OpenAI</td>
  </tr>
  <tr>
    <td align="center">MCP 支持</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">✅</td>
  </tr>
  <tr>
    <td align="center">Agent 协作</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
  </tr>
  <tr>
    <td align="center">多 Agent Runtime 支持</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
  </tr>
  <tr>
    <td align="center">可观测性</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
  </tr>
  <tr>
    <td align="center">本地部署</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
  </tr>
</table>

# CLI 工具
Cooragent 提供了一系列开发者工具，帮助开发者快速构建智能体。通过 CLI 工具，开发者可以快速创建，编辑，删除智能体。CLI 的设计注重效率和易用性，大幅减少了手动操作的繁琐，让开发者能更专注于智能体本身的设计与优化。

## 使用 Cli 工具一句话创建智能体
进入 cooragent 命令工具界面
```
python cli.py
```
<p align="center">
<img src="./assets/cli.png" alt="Cooragent cli 工具" />
</p>

一句话创建小米股票分析智能体
```
run -t agent_workflow -u <user> -m '创建一个股票分析专家 agent，分析过去一个月的小米股票走势，并预测下个交易日的股价走势，并给出买入或卖出的建议。'
```

## 编辑智能体
```
edit-agent -n <agent_name> -i
```
## 查询智能体
```
list-agents -u <user-id> -m <regex>
```
## 删除智能体
```
remove-agent -n <agent_name> -u <user-id>
```

## 使用一组智能体协作完成复杂任务
```
run -t agent_workflow -u <user> -m '综合运用任务规划智能体，爬虫智能体，代码运行智能体，浏览器操作智能体，报告撰写智能体，文件操作智能体为我规划一个 2025 年五一期间去云南旅游的行程。首先运行爬虫智能体爬取云南旅游的景点信息，并使用浏览器操作智能体浏览景点信息，选取最值得去的 10 个景点。然后规划一个 5 天的旅游的行程，使用报告撰写智能体生成一份旅游报告，最后使用文件操作智能体将报告保存为 pdf 文件。'
```

## 通过 MCP 方式创建智能体
```
server_params = StdioServerParameters(
    command="python",
    args=[str(get_project_root()) + "/src/mcp/excel_mcp/server.py"]
)

async def excel_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            # Get tools
            tools = await load_mcp_tools(session)
            # Create and run the agent
            agent = create_react_agent(model, tools)
            return agent


agent = asyncio.run(excel_agent())
agent_obj = Agent(user_id="share", 
                  agent_name="mcp_excel_agent", 
                  nick_name="mcp_excel_agent", 
                  description="The agent are good at manipulating excel files, which includes creating, reading, writing, and analyzing excel files", 
                  llm_type=LLMType.BASIC, 
                  selected_tools=[], 
                  prompt="")

MCPManager.register_agent("mcp_excel_agent", agent, agent_obj)
```
代码见 [src/mcp/excel_agent.py](./src/mcp/excel_agent.py)



## 全面的兼容性
Cooragent 在设计上追求极致的开放性和兼容性，确保能够无缝融入现有的 AI 开发生态，并为开发者提供最大的灵活性。这主要体现在对 Langchain 工具链的深度兼容、对MCP (Model Context Protocol) 协议的支持以及全面的 API 调用能力上。

- 深度兼容 Langchain 工具链:
  - 可以在 Cooragent 的智能体或工作流中直接使用熟悉的 Langchain 组件，如特定的 Prompts、Chains、Memory 模块、Document Loaders、Text Splitters 以及 Vector Stores 等。这使得开发者可以充分利用 Langchain 社区积累的丰富资源和既有代码。
  - 平滑迁移与整合: 如果您已经有基于 Langchain 开发的应用或组件，可以更轻松地将其迁移或整合到 Cooragent 框架中，利Cooragent 提供的协作、调度和管理能力对其进行增强。
  - 超越基础兼容: Cooragent 不仅兼容 Langchain，更在其基础上提供了如 Agent Factory、Agent Workflow、原生 A2A 通信等高级特性，旨在提供更强大、更易用的智能体构建和协作体验。您可以将 Langchain 作为强大的工具库，在 Cooragent 的框架内发挥其作用。
- 支持 MCP (Model Context Protocol):
  - 标准化交互: MCP 定义了一套规范，用于智能体之间传递信息、状态和上下文，使得不同来源、不同开发者构建的智能体能够更容易地理解彼此并进行协作。
  - 高效上下文管理: 通过 MCP，可以更有效地管理和传递跨多个智能体或多轮交互的上下文信息，减少信息丢失，提高复杂任务的处理效率。
  - 增强互操作性: 对 MCP 的支持使得 Cooragent 能够更好地与其他遵循该协议的系统或平台进行互操作，构建更广泛、更强大的智能生态系统。
- 全面的 API 调用支持:
  Cooragent 的核心功能都通过全面的 API (例如 RESTful API) 暴露出来，为开发者提供了强大的编程控制能力。
  - 程序化管理: 通过 API 调用，您可以自动化智能体的创建、部署、配置更新、启动/停止等全生命周期管理。
  - 任务集成: 将 Cooragent 的任务提交和结果获取能力集成到您自己的应用程序、脚本或工作流引擎中。
  - 状态监控与日志: 通过 API 获取智能体的实时运行状态、性能指标和详细日志，方便监控和调试。
  - 构建自定义界面: 利用 API，您可以为 Cooragent 构建自定义的前端用户界面或管理后台，满足特定的业务需求和用户体验。



## 贡献

我们欢迎各种形式的贡献！无论是修复错别字、改进文档，还是添加新功能，您的帮助都将备受感激。请查看我们的[贡献指南](CONTRIBUTING.md)了解如何开始。

## 许可证

本项目是开源的，基于 [MIT 许可证](LICENSE)。

## 致谢

特别感谢所有让 cooragent 成为可能的开源项目和贡献者。我们站在巨人的肩膀上。
