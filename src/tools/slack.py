import logging
import dotenv
from langchain_community.agent_toolkits import SlackToolkit

dotenv.load_dotenv()


logger = logging.getLogger(__name__)

toolkit = SlackToolkit()

slack_tools = toolkit.get_tools()

if __name__ == "__main__":
    for tool in slack_tools:
        print(tool.name)
        print(tool.description)
        print(tool.args)

