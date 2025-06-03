import logging
from typing import ClassVar, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_experimental.utilities import PythonREPL
from .decorators import create_logged_tool

# Initialize REPL and logger
repl = PythonREPL()
logger = logging.getLogger(__name__)


class PythonReplInput(BaseModel):
    """Input for Python REPL Tool."""
    code: str = Field(..., description="The python code to execute to do further analysis or calculation.")


class PythonReplTool(BaseTool):
    name: ClassVar[str] = "python_repl_tool"
    args_schema: Type[BaseModel] = PythonReplInput
    description: ClassVar[str] = """Use this to execute python code and do data analysis or calculation. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""

    def _run(self, code: str) -> str:
        """Execute Python code and return result."""
        logger.info("Executing Python code")
        try:
            result = repl.run(code)
            logger.info("Code execution successful")
        except BaseException as e:
            error_msg = f"Failed to execute. Error: {repr(e)}"
            logger.error(error_msg)
            return error_msg
        result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
        return result_str

    async def _arun(self, code: str) -> str:
        """Async version of Python REPL tool."""
        return self._run(code)


# Create logged version of the tool
PythonReplTool = create_logged_tool(PythonReplTool)
python_repl_tool = PythonReplTool()
