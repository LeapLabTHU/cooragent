# cooragent

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Wechat](https://img.shields.io/badge/WeChat-cooragent-brightgreen?logo=wechat&logoColor=white)](./assets/wechat_community.jpg)
[![Discord Follow](https://dcbadge.vercel.app/api/server/m3MszDcn?style=flat)](https://discord.gg/m3MszDcn)

[English](./README.md) | [简体中文](./README_zh.md)

# Cooragent 是什么

Cooragent 是一个 AI 智能体协作社区，在这个社区中，你可以通过一句话创建一个特定功能的智能体，并与其他智能体协作完成复杂任务。智能体可以自由组合，创造出无限可能。与此同时，你还可以将你的智能体发布到社区中，与其他人共享。

## 演示视频

> **Task**: Calculate the influence index of DeepSeek R1 on HuggingFace. This index can be designed by considering a weighted sum of factors such as followers, downloads, and likes.
>
> **任务**：创建一个股票分析 Agent，并分析明天的股票走势。

[![Demo](./assets/demo.gif)](./assets/demo.mp4)

- [在 YouTube 上观看](https://youtu.be/sZCHqrQBUGk)
- [下载视频](https://github.com/cooragent/cooragent/blob/main/assets/demo.mp4)

## 目录
- [快速开始](#快速开始)
- [架构](#架构)
- [功能特性](#功能特性)
- [为什么选择 cooragent？](#为什么选择-cooragent)
- [安装设置](#安装设置)
    - [前置要求](#前置要求)
    - [安装步骤](#安装步骤)
    - [配置](#配置)
- [使用方法](#使用方法)
- [网页界面](#网页界面)
- [开发](#开发)
- [贡献](#贡献)
- [许可证](#许可证)
- [致谢](#致谢)
- [API 服务器](#api-服务器)

## 快速安装

```bash
# 克隆仓库
git clone https://github.com/SeamLessAI-Inc/cooragent
cd cooragent

# 用uv创建并激活虚拟环境
uv python install 3.12
uv venv --python 3.12

source .venv/bin/activate  # Windows系统使用: .venv\Scripts\activate

# 安装依赖
uv sync

# 配置环境
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 运行项目
uv run main.py
```
## Cooragent 有什么不同


## 架构

cooragent 实现了一个分层的多智能体系统，其中有一个主管智能体协调专门的智能体来完成复杂任务：

![cooragent 架构](./assets/cooragent.png)

## 创建智能体
### 通过命令行创建智能体

### 通过网页创建智能体

## 编辑智能体

## 【发布/共享】智能体

## 使用一组智能体完成复杂任务





### 配置

在项目根目录创建 `.env` 文件并配置以下环境变量：

```ini
# 推理 LLM 配置（用于复杂推理任务）
REASONING_MODEL=your_reasoning_model
REASONING_API_KEY=your_reasoning_api_key
REASONING_BASE_URL=your_custom_base_url  # 可选

# 基础 LLM 配置（用于简单任务）
BASIC_MODEL=your_basic_model
BASIC_API_KEY=your_basic_api_key
BASIC_BASE_URL=your_custom_base_url  # 可选

# 视觉语言 LLM 配置（用于涉及图像的任务）
VL_MODEL=your_vl_model
VL_API_KEY=your_vl_api_key
VL_BASE_URL=your_custom_base_url  # 可选

# 工具 API 密钥
TAVILY_API_KEY=your_tavily_api_key
JINA_API_KEY=your_jina_api_key  # 可选

# 浏览器配置
CHROME_INSTANCE_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome  # 可选，Chrome 可执行文件路径
```

您可以复制 `.env.example` 文件作为模板开始：

```bash
cp .env.example .env
```

### API 服务器

cooragent 提供基于 FastAPI 的 API 服务器，支持流式响应：

```bash
# 启动 API 服务器
uv run server/app.py
```

API 服务器提供以下端点：

- `POST /api/chat/stream`：用于 LangGraph 调用的聊天端点，流式响应
    - 请求体：
    ```json
    {
      "messages": [
        {"role": "user", "content": "在此输入您的查询"}
      ],
      "debug": false
    }
    ```
    - 返回包含智能体响应的服务器发送事件（SSE）流



## web 端

cooragent 提供一个默认的网页界面。

请参考 [brainleap/brainleap-ai](https://www.brainleap.ai) 项目了解更多信息。


## 贡献

我们欢迎各种形式的贡献！无论是修复错别字、改进文档，还是添加新功能，您的帮助都将备受感激。请查看我们的[贡献指南](CONTRIBUTING.md)了解如何开始。

## 许可证

本项目是开源的，基于 [MIT 许可证](LICENSE)。

## 致谢

特别感谢所有让 cooragent 成为可能的开源项目和贡献者。我们站在巨人的肩膀上。
