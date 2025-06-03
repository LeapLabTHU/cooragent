import logging
import subprocess
from typing import ClassVar, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from .decorators import create_logged_tool

# Initialize logger
logger = logging.getLogger(__name__)


class BashToolInput(BaseModel):
    """Input for Bash Tool."""
    cmd: str = Field(..., description="The bash command to be executed.")


class BashTool(BaseTool):
    name: ClassVar[str] = "bash_tool"
    args_schema: Type[BaseModel] = BashToolInput
    description: ClassVar[str] = "Use this to execute bash command and do necessary operations."

    def _run(self, cmd: str) -> str:
        """Execute bash command and return result."""
        logger.info(f"Executing Bash Command: {cmd}")
        try:
            # Execute the command and capture output
            result = subprocess.run(
                cmd, shell=True, check=True, text=True, capture_output=True
            )
            # Return stdout as the result
            return result.stdout
        except subprocess.CalledProcessError as e:
            # If command fails, return error information
            error_message = f"Command failed with exit code {e.returncode}.\nStdout: {e.stdout}\nStderr: {e.stderr}"
            logger.error(error_message)
            return error_message
        except Exception as e:
            # Catch any other exceptions
            error_message = f"Error executing command: {str(e)}"
            logger.error(error_message)
            return error_message

    async def _arun(self, cmd: str) -> str:
        """Async version of bash tool."""
        return self._run(cmd)


# Create logged version of the tool
BashTool = create_logged_tool(BashTool)
bash_tool = BashTool()


if __name__ == "__main__":
    print(bash_tool.invoke("ls -all"))
