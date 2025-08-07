# cooragent

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Wechat](https://img.shields.io/badge/WeChat-cooragent-brightgreen?logo=wechat&logoColor=white)](./assets/wechat_community.jpg)
[![GitHub stars](https://img.shields.io/github/stars/LeapLabTHU/Cooragent?style=social)](https://github.com/LeapLabTHU/Cooragent/stargazers)

[English](./README.md) | [简体中文](./README_zh.md)

# Cooragent 是什么

Cooragent 是一个 AI 智能体协作社区。在这个社区中，你可以通过一句话创建一个具备强大功能的智能体，并与其他智能体协作完成复杂任务。智能体可以自由组合，创造出无限可能。与此同时，你还可以将你的智能体发布到社区中，与其他人共享。

# cooragent 的核心理念
当智能体的构建和打磨变得足够简单，AGI 时代将真正到来。
cooragent 的核心目标是：帮助用户快速构建智能体，快速构建工作流，快速打磨工作流。

<h5 align="center">
<video src="https://github.com/user-attachments/assets/9af611e3-aed6-4a2f-8663-428a7707fe8d" width="70%" alt="introduce cooragent" controls></video>
</h5>

# Cooragent Agent Studio

Cooragent Agent Studio 是一款在线智能体工作室，能快速生成可完成各类场景任务的智能体。它支持随时随地使用，同时还允许你对自己创建的智能体进行管理与分享。 免费试用 [Cooragent Agent Studio](www.cooragent.com)

# 自动创建 Agent，创造无限可能
Cooragent 有两种任务模式：**Agent Factory** 和 **Agent Workflow**。
- **Agent Factory** 模式下，你只需要你对智能体做出描述，Cooragent 就会根据你的需求生成一个智能体。Agent Factory 模式下，系统的会自动分析用户需求，通过记忆和扩展深入理解用户，省去纷繁复杂的 Prompt 设计。Planner 会在深入理解用户需求的基础上，挑选合适的工具，自动打磨 Prompt，逐步完成智能体构建。智能体构建完成后，可以立即投入使用，但你仍然可以对智能体进行编辑，优化其行为和功能。
- **Agent Workflow** 模式下你只需要描述你想要完成的目标任务，Cooragent 会自动分析任务的需求，挑选合适的智能体进行协作。Planner 根据各个智能体擅长的领域，对其进行组合并规划任务步骤和完成顺序，随后交由任务分发节点 publish 发布任务。各个智能领取自身任务，并协作完成任务。
Cooragent 可以在两种模式下不断演进，从而创造出无限可能。

# 高效构建 Agentic Workflow
如何高效构建 Workflow 是提升 Agent 在生产场景落地的关键。传统的 Workflow 构建完全依赖于开发人员的经验。无论是工具的选择，Prompt 打磨还是结构选择都耗费大量的人工和时间成本。Cooragent 创造性的提供三种 Workflow 工作方式 - Launch, polish, production。
- **Launch** 模式下，用户只需描述想要完成的目标任务，Cooragent 自动分析任务的需求，挑选合适的 Agent，构建完整工作流。且在任务结束后将工作流保存在本地存储中（通常在 store/workflow 下），支持后续复用与二次编辑。在 cli 工具中，用户可以通过 `run-l` 命令启动 Launch 模式。

- **Polish** 模式下，用户可以手动调整 workflow 的执行顺序，Agent 的工具选择，Agent 的 LLM 配置以及相关 Prompt。用户也可以通过自然语言指令交由 Cooragent 针对性的对某些部分进行调整。例如用户可以告诉 Cooragent：“调整股票分析 agent 的工具选择， 使用 tavily 工具代替 browser 工具以便更快速的搜索信息“。Cooragent 会基于类似 [APE](!https://arxiv.org/abs/2211.01910), [Absolute-Zero-Reasoner](!https://andrewzh112.github.io/absolute-zero-reasoner/)等技术框架自动化地调整 Agent 使用的提示词、工具和其他流程。在 cli 工具中，用户可以通过 `run-o` 命令启动 Polish 模式。

- **Production** 模式下，Cooragent 根据已经打磨好的 Workflow 高效执行，避免过多的运行干预，同时使用 Supervisor 对运行结果进行兜底。在 cli 工具中，用户可以通过 `run-p` 命令启动 Production 模式。

**最佳实践**，Launch 模式用于自动化快速构建可运行的 Workflow。Polish 模式用于 Workflow 的精细化打磨。Production 模式用于生产场景，追求稳定运行。


<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/polish.png" alt="Cooragent polish" />
</div>


# 快速安装

1. 使用 conda 安装
```bash
git clone https://github.com/LeapLabTHU/cooragent.git
cd cooragent

conda create -n cooragent python=3.12
conda activate cooragent

pip install -e .

# Optional: 使用 browser 工具时需要安装
playwright install

# 配置 API keys 和其他环境变量
cp .env.example .env
# Edit .env file and fill in your API keys

# 通过 CLi 本地运行
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
# 注意 Browse tool 等待时间较长，默认是关闭的。可以通过设置  `USE_BROWSER=True` 开启
cp .env.example .env
# Edit .env file and fill in your API keys

# 通过 CLi 本地运行
uv run cli.py 
```
**注意**：如果在 windows 平台运行本项目 cli 工具，除了上述步骤外，还需要安装额外依赖，详见[windows-平台支持](./docs/QA_zh.md#windows-平台支持)。

## 配置

在项目根目录创建 `.env` 文件并配置以下环境变量：

```bash
cp .env.example .env
```


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

## 一句话创建小米股票分析智能体
```
run-l -t agent_workflow -u test -m '创建一个股票分析专家 agent. 今天是 2025年 4 月 22 日，查看过去一个月的小米股票走势，分析当前小米的热点新闻，预测下个交易日的股价走势，并给出买入或卖出的建议。'
```

## 打磨智能体工作流
```
run-o -u <user-id>
```

## 以 Production 模式运行智能体工作流
```
run-p -u <user-id> -w <workflow-id> -m <message>
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
run-l -t agent_workflow -u test -m '综合运用任务规划智能体，爬虫智能体，代码运行智能体，浏览器操作智能体，报告撰写智能体，文件操作智能体为我规划一个 2025 年五一期间去云南旅游的行程。首先运行爬虫智能体爬取云南旅游的景点信息，并使用浏览器操作智能体浏览景点信息，选取最值得去的 10 个景点。然后规划一个 5 天的旅游的行程，使用报告撰写智能体生成一份旅游报告，最后使用文件操作智能体将报告保存为 pdf 文件。'
```

## 集成 MCP 服务 (类似 Claude Desktop)

通过模型上下文协议 (MCP) 集成外部服务和工具，以增强您的智能体 (Agent) 的能力。这类似于某些桌面 AI 助手 (如 Claude Desktop) 管理外部功能的方式。

**配置方法：**

1.  **定位/创建配置文件**：
    在您的项目根目录中找到或创建 `config/mcp.json` 文件。

    ```bash
    cd ./config
    cp mcp.json.example mcp.json
    ```

2.  **添加 MCP 服务**：
    在此 JSON 文件中定义您的 MCP 服务。每个服务都有一个唯一的键 (key) 和一个配置对象。

    配置文件 (`config/mcp.json`) 示例：
    ```json
    {
        "mcpServers": {
          "aws-kb-retrieval": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-aws-kb-retrieval"],
            "env": {
              "AWS_ACCESS_KEY_ID": "YOUR_ACCESS_KEY_HERE",
              "AWS_SECRET_ACCESS_KEY": "YOUR_SECRET_ACCESS_KEY_HERE",
              "AWS_REGION": "YOUR_AWS_REGION_HERE"
            }
          },
          "AMAP": {
            "url": "https://mcp.amap.com/sse",
            "env": {
              "AMAP_MAPS_API_KEY": "AMAP_MAPS_API_KEY"
            }
          }
        }
    }
    ```

**工作原理：**

配置完成后，Cooragent 会自动将您在 `mcp.json` 中定义的这些 MCP 服务注册为可用工具。之后，智能体 (Agent) 在规划和执行任务时便可以选择和使用这些工具，从而实现更复杂的功能。
如上配置好高德地图相关工具后，你可以尝试如下的使用案例：
```
创建一个导航智能体，专注于导航，使用地图相关工具，规划如何从北京西站到故宫。
```


## 文档 & 支持
- [常见问题 (FAQ)](./docs/QA_zh.md)
- [商业支持计划](./docs/business_support_zh.md)


## 贡献

我们欢迎各种形式的贡献！无论是修复错别字、改进文档，还是添加新功能，您的帮助都将备受感激。请查看我们的[贡献指南](CONTRIBUTING.md)了解如何开始。


欢迎加入我们的 wechat 群，随时提问，分享，吐槽。

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/wechat_community.jpg" alt="Cooragent group" width="300" />
</div>


## Citation

Core contributors: Zheng Wang,  Shenzhi Wang, Yue Wu, Shiji Song, Gao Huang

```
@misc{wang2025cooragent,
  title        = {Cooragent: An AI Agent Collaboration Community},
  author       = {Zheng Wang, Shenzhi Wang, Yue Wu, Chi Zhang, Shiji Song, Gao Huang},
  howpublished = {\url{https://github.com/LeapLabTHU/cooragent}},
  year         = {2025}
}
```

## Star History
![Star History Chart](https://api.star-history.com/svg?repos=LeapLabTHU/cooragent&type=Date)


## 致谢
特别感谢所有让 cooragent 成为可能的开源项目和贡献者。我们站在巨人的肩膀上。

