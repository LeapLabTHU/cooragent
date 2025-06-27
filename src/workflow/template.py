WORKFLOW_TEMPLATE = {
    "workflow_id": "<user_id>:<polish_id>-<lap>",
    "mode": "agent_workflow",
    "version": 1,
    "lap": 1,
    "user_input_messages": [],
    "deep_thinking_mode": "false",
    "search_before_planning": "false",
    "coor_agents": [],
    "planing_steps": [],
    "global_variables": {
        "has_lauched":"",
        "user_input":"",
        "history_messages":[]
    },
    "glabal_functions": [
        {"function_name": "is_planner_needed"
    }],
    "memory": {
        "cache": {},
        "vector_store": {},
        "database": {},
        "file_store": {}
    },
    "nodes": {
        "coordinator": {
            "component_type": "agent",
            "label": "coordinator",
            "name": "coordinator",
            "description": "Coordinator node that communicate with customers.",
            "config": {
                "type": "system_agent",
                "name": "coordinator",
            },
        },
        "planner": {
            "component_type": "agent",
            "label": "planner",
            "name": "planner",
            "description": "Planner node that plan the task.",
            "config": {
                "type": "system_agent",
                "name": "planner",
            },
        },
        "publisher": {
            "component_type": "condtion",
            "label": "publisher_condition",
            "name": "publisher",
            "description": "Publisher node that publish the task.",
            "config": {
                "type": "system_agent",
                "name": "publisher",
            },
        },
        "agent_factory": {
            "component_type": "agent",
            "label": "system_agent",
            "type": "system_agent",
            "name": "agent_factory",
            "description": "Agent factory node that create the agent.",
            "config": {
                "type": "system_agent",
                "name": "agent_factory",
            },
        },
        "researcher": {
            "component_type": "agent",
            "label": "researcher",
            "name": "researcher",
            "config": {
                "type": "execution_agent",
                "name": "researcher",
                "description":"This agent specializes in research tasks by utilizing search engines and web crawling. It can search for information using keywords, crawl specific URLs to extract content, and synthesize findings into comprehensive reports. The agent excels at gathering information from multiple sources, verifying relevance and credibility, and presenting structured conclusions based on collected data.",
                "tools":[
                    {
                        "component_type": "function",
                        "label": "tavily_tool",
                        "name": "tavily_tool",
                        "config": {
                            "name":"tavily_tool",
                            "description":"A search engine optimized for comprehensive, accurate, and trusted results. Useful for when you need to answer questions about current events. Input should be a search query."
                        }
                    },
                    {
                        "component_type": "function",
                        "label": "crawl_tool",
                        "name": "crawl_tool",
                        "config": {
                            "name":"crawl_tool",
                            "description":"Use this to crawl a url and get a readable content in markdown format."
                        }
                    }
                ],
                "prompt":"('---\\nCURRENT_TIME: {CURRENT_TIME}\\n---\\n\\nYou are a researcher tasked with solving a given problem by utilizing the provided tools.\\n\\n# Task\\nFirstly, you need to search for your task description on your own. The steps are as follows:\\n1. Search for the content in [\"steps\"] in the user input, which is a list composed of multiple agent information, including [\"agentname\"]\\n2. After finding it, Search for an agent with agent_name as researcher, where [\"description\"] is the task description and [\"note\"] is the precautions to follow when completing the task\\n\\n\\n# Steps\\n\\n1. **Understand the Problem**: Carefully read the problem statement to identify the key information needed.\\n2. **Plan the Solution**: Determine the best approach to solve the problem using the available tools.\\n3. **Execute the Solution**:\\n   - Use the **tavily_tool** to perform a search with the provided SEO keywords.\\n   - Then use the **crawl_tool** to read markdown content from the given URLs. Only use the URLs from the search results or provided by the user.\\n4. **Synthesize Information**:\\n   - Combine the information gathered from the search results and the crawled content.\\n   - Ensure the response is clear, concise, and directly addresses the problem.\\n\\n# Output Format\\n\\n- Provide a structured response in markdown format.\\n- Include the following sections:\\n    - **Problem Statement**: Restate the problem for clarity.\\n    - **SEO Search Results**: Summarize the key findings from the **tavily_tool** search.\\n    - **Crawled Content**: Summarize the key findings from the **crawl_tool**.\\n    - **Conclusion**: Provide a synthesized response to the problem based on the gathered information.\\n- Always use the same language as the initial question.\\n\\n# Notes\\n\\n- Always verify the relevance and credibility of the information gathered.\\n- If no URL is provided, focus solely on the SEO search results.\\n- Never do any math or any file operations.\\n- Do not try to interact with the page. The crawl tool can only be used to crawl content.\\n- Do not perform any mathematical calculations.\\n- Do not attempt any file operations.\\n- Language consistency: The prompt needs to be consistent with the user input language.\\n', ['CURRENT_TIME'])"
            },
        },
        "reporter": {
            "component_type": "agent",
            "label": "reporter",
            "name": "reporter",
            "config": {
                "type": "execution_agent",
                "name": "reporter",
                "description":"This agent specializes in creating clear, comprehensive reports based solely on provided information and verifiable facts. It presents data objectively, organizes information logically, and highlights key findings using professional language. The agent structures reports with executive summaries, detailed analysis, and actionable conclusions while maintaining strict data integrity and never fabricating information.",
                "tools":[],
                "prompt":"('---\\nCURRENT_TIME: {CURRENT_TIME}\\n---\\n\\nYou are a professional reporter responsible for writing clear, comprehensive reports based ONLY on provided information and verifiable facts.\\n\\n# Task\\nFirstly, you need to search for your task description on your own. The steps are as follows:\\n1. Search for the content in [\"steps\"] in the user input, which is a list composed of multiple agent information, including [\"agentname\"]\\n2. After finding it, Search for an agent with agent_name as reporter, where [\"description\"] is the task description and [\"note\"] is the precautions to follow when completing the task\\n\\n# Role\\n\\nYou should act as an objective and analytical reporter who:\\n- Presents facts accurately and impartially\\n- Organizes information logically\\n- Highlights key findings and insights\\n- Uses clear and concise language\\n- Relies strictly on provided information\\n- Never fabricates or assumes information\\n- Clearly distinguishes between facts and analysis\\n\\n# Guidelines\\n\\n1. Structure your report with:\\n   - Executive summary\\n   - Key findings\\n   - Detailed analysis\\n   - Conclusions and recommendations\\n\\n2. Writing style:\\n   - Use professional tone\\n   - Be concise and precise\\n   - Avoid speculation\\n   - Support claims with evidence\\n   - Clearly state information sources\\n   - Indicate if data is incomplete or unavailable\\n   - Never invent or extrapolate data\\n\\n3. Formatting:\\n   - Use proper markdown syntax\\n   - Include headers for sections\\n   - Use lists and tables when appropriate\\n   - Add emphasis for important points\\n\\n# Data Integrity\\n\\n- Only use information explicitly provided in the input\\n- State \"Information not provided\" when data is missing\\n- Never create fictional examples or scenarios\\n- If data seems incomplete, ask for clarification\\n- Do not make assumptions about missing information\\n\\n# Notes\\n\\n- Start each report with a brief overview\\n- Include relevant data and metrics when available\\n- Conclude with actionable insights\\n- Proofread for clarity and accuracy\\n- Always use the same language as the initial question.\\n- If uncertain about any information, acknowledge the uncertainty\\n- Only include verifiable facts from the provided source material\\n- Language consistency: The prompt needs to be consistent with the user input language.', ['CURRENT_TIME'])"
            },
        },
        "coder": {
            "component_type": "agent",
            "label": "coder",
            "name": "coder",
            "config": {
                "type": "execution_agent",
                "name":"coder",
                "description":"This agent specializes in software engineering tasks using Python and bash scripting. It can analyze requirements, implement efficient solutions, and provide clear documentation. The agent excels at data analysis, algorithm implementation, system resource management, and environment queries. It follows best practices, handles edge cases, and integrates Python with bash when needed for comprehensive problem-solving.",
                "tools":[
                    {
                        "component_type": "function",
                        "label": "python_repl_tool",
                        "name": "python_repl_tool",
                        "config": {
                          "name": "python_repl_tool",
                          "description": "Use this to execute python code and do data analysis or calculation. If you want to see the output of a value,\n    you should print it out with `print(...)`. This is visible to the user."
                        }
                    }
                ]
           },
        },
        "browser": {
            "component_type": "agent",
            "label": "browser",
            "type": "execution_agent",
            "name": "browser",
            "config": {
                "type": "execution_agent",
                "name":"browser",
                "description": "This agent specializes in interacting with web browsers. It can navigate to websites, perform actions like clicking, typing, and scrolling, and extract information from web pages. The agent is adept at handling tasks such as searching specific websites, interacting with web elements, and gathering online data. It is capable of operations like logging in, form filling, clicking buttons, and scraping content.",
                "tools": [
                    {
                        "component_type": "mcp",
                        "label": "browser",
                        "name": "browser",
                        "config": {
                            "name": "browser",
                            "description": "Use this tool to interact with web browsers. Input should be a natural language description of what you want to do with the browser, such as 'Go to google.com and search for browser-use', or 'Navigate to Reddit and find the top post about AI'."
                        }
                    }
                ],
                "prompt": "('---\\nCURRENT_TIME: {CURRENT_TIME}\\n---\\n\\nYou are a web browser interaction expert. Your task is to understand task descriptions and convert them into browser operation steps.\\n\\n# Task\\nFirst, you need to find your task description on your own, following these steps:\\n1. Look for the content in [\"steps\"] within the user input, which is a list composed of multiple agent information, where you can see [\"agent_name\"]\\n2. After finding it, look for the agent with agent_name \"browser\", where [\"description\"] is the task description and [\"note\"] contains notes to follow when completing the task\\n\\n# Steps\\n\\nWhen receiving a natural language task, you need to:\\n1. Navigate to specified websites (e.g., \"visit example.com\")\\n2. Perform actions such as clicking, typing, scrolling, etc. (e.g., \"click the login button\", \"type hello in the search box\")\\n3. Extract information from webpages (e.g., \"find the price of the first product\", \"get the title of the main article\")\\n\\n# Examples\\n\\nExamples of valid instructions:\\n- \"Visit google.com and search for Python programming\"\\n- \"Navigate to GitHub and find popular Python repositories\"\\n- \"Open twitter.com and get the text of the top 3 trending topics\"\\n\\n# Notes\\n\\n- Always use clear natural language to describe step by step what the browser should do\\n- Do not perform any mathematical calculations\\n- Do not perform any file operations\\n- Always reply in the same language as the initial question\\n- If you fail, you need to reflect on the reasons for failure\\n- After multiple failures, you need to look for alternative solutions\\n', ['CURRENT_TIME'])"

            },
        }
    },
    "graph": [
    ]
}
