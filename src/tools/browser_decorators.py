import logging
import functools
import asyncio
from typing import Any, Callable, Type, TypeVar
from src.service.tool_tracker import tool_tracker
from src.tools.websocket_manager import websocket_manager


logger = logging.getLogger(__name__)

T = TypeVar("T")


def log_io(func: Callable) -> Callable:
    """
    A decorator that logs the input parameters and output of a tool function.

    Args:
        func: The tool function to be decorated

    Returns:
        The wrapped function with input/output logging
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Log input parameters
        func_name = func.__name__
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.debug(f"Tool {func_name} called with parameters: {params}")

        # Execute the function
        result = func(*args, **kwargs)

        # Log the output
        logger.debug(f"Tool {func_name} returned: {result}")

        return result

    return wrapper


def early_tool_notification(tool_cls: Type[T]) -> Type[T]:
    """
    Decorator: Adds early notification functionality to the invoke and ainvoke methods of a tool class.
    This decorator sends a notification before the tool actually starts executing.
    """
    original_invoke = getattr(tool_cls, 'invoke', None)
    original_ainvoke = getattr(tool_cls, 'ainvoke', None)
    
    def _send_notification_sync(tool_name: str, user_id: str) -> None:
        """Synchronously sends a notification."""
        try:
            from src.tools.websocket_manager import websocket_manager
            
            # Record tool usage
            tool_tracker.record_tool_usage(user_id, tool_name)
            
            # Send notification
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If the event loop is running, create a task
                    asyncio.create_task(websocket_manager.broadcast_tool_start(user_id, tool_name))
                else:
                    # If there is no running event loop, run directly
                    loop.run_until_complete(websocket_manager.broadcast_tool_start(user_id, tool_name))
            except RuntimeError:
                # If there is no event loop, create a new one
                asyncio.run(websocket_manager.broadcast_tool_start(user_id, tool_name))
                
            logger.info(f"Early notification sent: Tool {tool_name}, User {user_id}")
        except Exception as e:
            logger.warning(f"Failed to send early notification: {e}")
    
    async def _send_notification_async(tool_name: str, user_id: str) -> None:
        """Asynchronously sends a notification."""
        try:
            from src.tools.websocket_manager import websocket_manager
            
            # Record tool usage
            tool_tracker.record_tool_usage(user_id, tool_name)
            
            # Send notification
            await websocket_manager.broadcast_tool_start(user_id, tool_name)
            logger.info(f"Early notification sent: Tool {tool_name}, User {user_id}")
        except Exception as e:
            logger.warning(f"Failed to send early notification: {e}")
    
    if original_invoke:
        @functools.wraps(original_invoke)
        def invoke(self, input, config=None, **kwargs):
            # Get tool name and user ID
            tool_name = getattr(self, 'name', self.__class__.__name__.lower())
            user_id = kwargs.get('user_id', None)
            
            # Send notification immediately
            if user_id:
                _send_notification_sync(tool_name, user_id)
            
            # Call the original method
            return original_invoke(self, input, config, **kwargs)
        
        setattr(tool_cls, 'invoke', invoke)
    
    if original_ainvoke:
        @functools.wraps(original_ainvoke)
        async def ainvoke(self, input, config=None, **kwargs):
            # Get tool name and user ID
            tool_name = getattr(self, 'name', self.__class__.__name__.lower())
            user_id = kwargs.get('user_id', None)
            
            # Send notification immediately
            if user_id:
                await _send_notification_async(tool_name, user_id)
            
            # Call the original method
            return await original_ainvoke(self, input, config, **kwargs)
        
        setattr(tool_cls, 'ainvoke', ainvoke)
    
    return tool_cls


class LoggedToolMixin:
    """A mixin class that adds logging functionality to any tool."""

    def _log_operation(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """Helper method to log tool operations."""
        tool_name = self.__class__.__name__.replace("Logged", "")
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.debug(f"Tool {tool_name}.{method_name} called with parameters: {params}")

    def _send_tool_notification(self, tool_name: str, user_id: str) -> None:
        """Synchronous method to send tool start notification."""
        try:
            
            # Create a new event loop to handle asynchronous notification
            def run_notification():
                try:
                    # Try to get the current event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If the event loop is running, create a task
                        task = asyncio.create_task(websocket_manager.broadcast_tool_start(user_id, tool_name))
                        return task
                    else:
                        # If there is no running event loop, run directly
                        return loop.run_until_complete(websocket_manager.broadcast_tool_start(user_id, tool_name))
                except RuntimeError:
                    # If there is no event loop, create a new one
                    return asyncio.run(websocket_manager.broadcast_tool_start(user_id, tool_name))
            
            run_notification()
            logger.debug(f"Successfully sent tool start notification: {tool_name} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to send tool start notification: {e}")

    async def _send_tool_notification_async(self, tool_name: str, user_id: str) -> None:
        """Asynchronous method to send tool start notification."""
        try:
            from src.tools.websocket_manager import websocket_manager
            await websocket_manager.broadcast_tool_start(user_id, tool_name)
            logger.debug(f"Successfully sent tool start notification: {tool_name} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to send tool start notification: {e}")

    def invoke(self, input, config=None, **kwargs):
        """Override invoke method to send notification before tool call."""
        # Get tool name and user ID
        tool_name = getattr(self, 'name', self.__class__.__name__.replace('Logged', '').lower())
        
        # Try to get user_id from multiple sources
        user_id = kwargs.get('user_id', None)
        
        # If not in kwargs, try to get from config
        if not user_id and config:
            # LangChain passes user_id in config.configurable
            if hasattr(config, 'configurable') and config.configurable:
                user_id = config.configurable.get('user_id')
            # Also try direct access if config is a dict
            elif isinstance(config, dict):
                user_id = config.get('user_id') or config.get('configurable', {}).get('user_id')
        
        # If still not found, try to get from input if it's a dict
        if not user_id and isinstance(input, dict):
            user_id = input.get('user_id')
        
        # Record tool usage and send start notification
        if user_id:
            tool_tracker.record_tool_usage(user_id, tool_name)
            # Send notification immediately
            self._send_tool_notification(tool_name, user_id)
        else:
            logger.debug(f"No user_id found for tool {tool_name}, skipping notification")
        
        # Call the original invoke method
        if hasattr(super(), 'invoke'):
            return super().invoke(input, config, **kwargs)
        else:
            # If there is no invoke method, fall back to _run
            return self._run(**input if isinstance(input, dict) else {"input": input})

    async def ainvoke(self, input, config=None, **kwargs):
        """Override ainvoke method to send notification before tool call."""
        # Get tool name and user ID
        tool_name = getattr(self, 'name', self.__class__.__name__.replace('Logged', '').lower())
        
        # Try to get user_id from multiple sources
        user_id = kwargs.get('user_id', None)
        
        # If not in kwargs, try to get from config
        if not user_id and config:
            # LangChain passes user_id in config.configurable
            if hasattr(config, 'configurable') and config.configurable:
                user_id = config.configurable.get('user_id')
            # Also try direct access if config is a dict
            elif isinstance(config, dict):
                user_id = config.get('user_id') or config.get('configurable', {}).get('user_id')
        
        # If still not found, try to get from input if it's a dict
        if not user_id and isinstance(input, dict):
            user_id = input.get('user_id')
        
        # Record tool usage and send start notification
        if user_id:
            tool_tracker.record_tool_usage(user_id, tool_name)
            # Send asynchronous notification immediately
            await self._send_tool_notification_async(tool_name, user_id)
        else:
            logger.debug(f"No user_id found for tool {tool_name}, skipping notification")
        
        # Call the original ainvoke method
        if hasattr(super(), 'ainvoke'):
            return await super().ainvoke(input, config, **kwargs)
        else:
            # If there is no ainvoke method, fall back to _arun or _run
            if hasattr(self, '_arun'):
                return await self._arun(**input if isinstance(input, dict) else {"input": input})
            else:
                return self._run(**input if isinstance(input, dict) else {"input": input})

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Override _run method to add logging and tool usage tracking."""
        self._log_operation("_run", *args, **kwargs)
        
        # Get tool name and user ID
        tool_name = getattr(self, 'name', self.__class__.__name__.replace('Logged', '').lower())
        user_id = kwargs.get('user_id', None)
        
        # If tool usage has not been recorded yet (possibly _run was called directly), record it and send notification
        if user_id and not tool_tracker.is_tool_active(user_id, tool_name):
            tool_tracker.record_tool_usage(user_id, tool_name)
            self._send_tool_notification(tool_name, user_id)
        
        result = None
        try:
            result = super()._run(*args, **kwargs)
            logger.debug(
                f"Tool {self.__class__.__name__.replace('Logged', '')} returned: {result}"
            )
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise
        
        return result


def create_logged_tool(base_tool_class: Type[T]) -> Type[T]:
    """
    Factory function to create a logged version of any tool class.

    Args:
        base_tool_class: The original tool class to be enhanced with logging

    Returns:
        A new class that inherits from both LoggedToolMixin and the base tool class
    """

    class LoggedTool(LoggedToolMixin, base_tool_class):
        pass

    # Set a more descriptive name for the class
    LoggedTool.__name__ = f"Logged{base_tool_class.__name__}"
    
    # Apply the early notification decorator
    LoggedTool = early_tool_notification(LoggedTool)
    
    return LoggedTool
