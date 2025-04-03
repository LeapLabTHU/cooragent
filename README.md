# cooragent

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Wechat](https://img.shields.io/badge/WeChat-cooragent-brightgreen?logo=wechat&logoColor=white)](./assets/wechat_community.jpg)
[![Discord Follow](https://dcbadge.vercel.app/api/server/m3MszDcn?style=flat)](https://discord.gg/m3MszDcn)

[English](./README.md) | [简体中文](./README_zh.md)

# What is Cooragent

Cooragent is an AI agent collaboration community where you can create a specific-function agent with just one sentence and collaborate with other agents to complete complex tasks. Agents can be freely combined to create unlimited possibilities. At the same time, you can also publish your agents to the community to share with each others.

## Demo Videos

> **Task**: Create a stock analysis agent that uses search tools to find Tencent's stock price information for the last seven days and Tencent's financial status. Then use the browser to find a couple of investor analyses about Tencent's recent stock performance (one or two entries). Based on this information, conduct a very detailed textual analysis, and finally generate a Chinese analysis report containing line charts and text, saved in a docx file.

> **Task**: Create an agent that searches for and learns about recently released OpenAI models and their characteristics, then use the created agent to write an article, and use the browser to publish it to the Xiaohongshu (RED) community.

## Quick Installation

```bash
# Clone repository
git clone https://github.com/SeamLessAI-Inc/cooragent
cd cooragent

# Create and activate virtual environment with uv
uv python install 3.12
uv venv --python 3.12

source .venv/bin/activate  # For Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env file and fill in your API keys

# Run the project
uv run main.py
```

## Why Cooragent

## Comparison with Other Tools
<table style="width: 100%;">
  <tr>
    <th align="center">Agent Plantform</th>
    <th align="center">cooragent</th>
    <th align="center">open-manus</th>
    <th align="center">cooragent</th>
    <th align="center">OpenAI Assistant Operator</th>
  </tr>
  <tr>
    <td align="center">Implementation</td>
    <td align="center">Agent collaboration through autonomous creation</td>
    <td align="center">Tool-based complex tasks</td>
    <td align="center">Tool-based complex tasks</td>
    <td align="center">Tool-based complex tasks</td>
  </tr>
  <tr>
    <td align="center">Supported LLMs</td>
    <td align="center">Diverse options</td>
    <td align="center">Diverse options</td>
    <td align="center">Diverse options</td>
    <td align="center">OpenAI only</td>
  </tr>
  <tr>
    <td align="center">MCP support</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">✅</td>
  </tr>
  <tr>
    <td align="center">Agent collaboration</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
  </tr>
  <tr>
    <td align="center">Multi-Agent Runtime support</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
  </tr>
  <tr>
    <td align="center">Easy to observe and edit</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
  </tr>
  <tr>
    <td align="center">Local deployment</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
  </tr>
</table>

## Architecture

Cooragent implements a hierarchical multi-agent system with a supervisor agent coordinating specialized agents to complete complex tasks:

![cooragent architecture](./assets/cooragent.png)

## One-sentence Agent Creation

## Agent Editing

## MCP-based Agent Creation

## Publish/Share Agents

## Completing Complex Tasks with Agent Teams

### Configuration

Create `.env` file in project root:

```bash
cp .env.example .env
```

## Web Interface

Cooragent provides a default web interface. Refer to [brainleap/brainleap-ai](https://www.brainleap.ai) for more details.

## Contribution

We welcome various forms of contribution! Whether it's fixing typos, improving documentation, or adding new features, your help will be greatly appreciated. Please check out our [contribution guide](CONTRIBUTING.md) to learn how to get started.

## License

This project is open-source, based on the [MIT License](LICENSE).

## Acknowledgments

Special thanks to all open-source projects and contributors that made cooragent possible. We stand on the shoulders of giants.
