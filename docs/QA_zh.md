## Cooragent 和其他 Agent 的区别是什么？

Cooragent 和其他 Agent 最大的区别在于：Cooragent 的核心理念是基于 Agent 协作完成复杂任务，而不是工具的协作。在我们看来，工具协作的上限较低，难以适用于相对复杂的场景。Agent 协作则具备更大的优化空间，理论上通过 Agent 的无限组合能更好地适应各种场景。

## API KEY 错误

如果您遇到以下错误：
```
The api key client option must be set either by passing api key to the client or by setting the OPENAI API KEy environment variable
```
请检查 `.env` 文件中的 `REASONING_MODEL`, `BASIC_MODEL`, `TAVILY_API_KEY` 配置。这三个 key 是必需的。

⚙️ 获取`TAVILY_API_KEY` ？ 请前往 [Tavily 控制台](https://app.tavily.com/home) 。

## Planner 执行错误

如果您遇到以下错误：
```
Starting execution: planner...ERROR:src.workflow.process:Error
```
这通常是由于 Reasoning Model 输出格式错误导致的。建议更换为 `qwen-max-latest` 或 `deepseek-r1`。

## 是否提供 UI？

Cooragent 平台正在加紧打磨中，近期即将发布，敬请期待！

## Windows 平台的支持

目前主要是 cli 工具的依赖包 `readline` 不支持，解决方法如下：
```bash
pip install pyreadline
```

但是，我们更推荐您使用 Linux、macOS 或者 Windows Subsystem for Linux (WSL) 进行本地开发和部署。

## 开启 Debug 模式的方式
Cooragent 允许用户通过在启动命令附加 `--debug` 开启 Debug 模式，debug 模式将输出更加详尽的日志信息。