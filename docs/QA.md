## What is the difference between Cooragent and other Agents?

The biggest difference between Cooragent and other Agents is: Cooragent's core philosophy is based on Agent collaboration to complete complex tasks, rather than tool collaboration. In our view, tool collaboration has a lower ceiling and is difficult to apply to relatively complex scenarios. Agent collaboration, on the other hand, has greater optimization potential. Theoretically, through the infinite combination of Agents, it can better adapt to various scenarios.

## API KEY Error

If you encounter the following error:
```
The api key client option must be set either by passing api key to the client or by setting the OPENAI API KEy environment variable
```
Please check the `REASONING_MODEL`, `BASIC_MODEL`, `TAVILY_API_KEY` configurations in the `.env` file. These three keys are required.

⚙️ To configure `TAVILY_API_KEY`? please visit [Tavily Console](https://app.tavily.com/home) to obtain your key.  


## Planner Execution Error

If you encounter the following error:
```
Starting execution: planner...ERROR:src.workflow.process:Error
```
This is usually caused by an incorrect output format from the Reasoning Model. It is recommended to switch to `qwen-max-latest` or `deepseek-r1`.

## Is a UI provided?

The Cooragent platform is currently being polished and will be released soon. Stay tuned!

## Windows Platform Support

The primary issue is the lack of support for the `readline` dependency in the CLI tool. Here's the workaround:
```bash
pip install pyreadline
```

However, we recommend using Linux, macOS, or Windows Subsystem for Linux (WSL) for local development and deployment.

## How to Enable Debug Mode
Cooragent allows users to enable Debug mode by appending `--debug` to the startup command. Debug mode will output more detailed log information.

