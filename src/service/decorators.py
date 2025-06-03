import logging
import functools
import asyncio
from typing import Any, Callable, Type, TypeVar
from src.service.tool_tracker import tool_tracker
from src.service.context import UserContext

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
    装饰器：在工具类的invoke和ainvoke方法中添加早期通知功能
    这个装饰器会在工具真正开始执行之前就发送通知
    """
    original_invoke = getattr(tool_cls, 'invoke', None)
    original_ainvoke = getattr(tool_cls, 'ainvoke', None)
    
    def _send_notification_sync(tool_name: str, user_id: str) -> None:
        """同步发送通知"""
        try:
            from src.service.websocket_manager import websocket_manager
            
            # 记录工具使用
            tool_tracker.record_tool_usage(user_id, tool_name)
            
            # 发送通知
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    asyncio.create_task(websocket_manager.broadcast_tool_start(user_id, tool_name))
                else:
                    # 如果没有运行的事件循环，直接运行
                    loop.run_until_complete(websocket_manager.broadcast_tool_start(user_id, tool_name))
            except RuntimeError:
                # 如果没有事件循环，创建新的
                asyncio.run(websocket_manager.broadcast_tool_start(user_id, tool_name))
                
            logger.info(f"早期通知已发送: 工具 {tool_name}, 用户 {user_id}")
        except Exception as e:
            logger.warning(f"早期通知发送失败: {e}")
    
    async def _send_notification_async(tool_name: str, user_id: str) -> None:
        """异步发送通知"""
        try:
            from src.service.websocket_manager import websocket_manager
            
            # 记录工具使用
            tool_tracker.record_tool_usage(user_id, tool_name)
            
            # 发送通知
            await websocket_manager.broadcast_tool_start(user_id, tool_name)
            logger.info(f"早期通知已发送: 工具 {tool_name}, 用户 {user_id}")
        except Exception as e:
            logger.warning(f"早期通知发送失败: {e}")
    
    if original_invoke:
        @functools.wraps(original_invoke)
        def invoke(self, input, config=None, **kwargs):
            # 获取工具名称和用户ID
            tool_name = getattr(self, 'name', self.__class__.__name__.lower())
            user_id = UserContext.get_user_id()
            
            # 立即发送通知
            if user_id:
                _send_notification_sync(tool_name, user_id)
            
            # 调用原始方法
            return original_invoke(self, input, config, **kwargs)
        
        setattr(tool_cls, 'invoke', invoke)
    
    if original_ainvoke:
        @functools.wraps(original_ainvoke)
        async def ainvoke(self, input, config=None, **kwargs):
            # 获取工具名称和用户ID
            tool_name = getattr(self, 'name', self.__class__.__name__.lower())
            user_id = UserContext.get_user_id()
            
            # 立即发送通知
            if user_id:
                await _send_notification_async(tool_name, user_id)
            
            # 调用原始方法
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
        """发送工具开始通知的同步方法"""
        try:
            from src.service.websocket_manager import websocket_manager
            
            # 创建一个新的事件循环来处理异步通知
            def run_notification():
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环正在运行，创建任务
                        task = asyncio.create_task(websocket_manager.broadcast_tool_start(user_id, tool_name))
                        return task
                    else:
                        # 如果没有运行的事件循环，直接运行
                        return loop.run_until_complete(websocket_manager.broadcast_tool_start(user_id, tool_name))
                except RuntimeError:
                    # 如果没有事件循环，创建新的
                    return asyncio.run(websocket_manager.broadcast_tool_start(user_id, tool_name))
            
            run_notification()
            logger.debug(f"成功发送工具开始通知: {tool_name} for user {user_id}")
        except Exception as e:
            logger.warning(f"发送工具开始通知失败: {e}")

    async def _send_tool_notification_async(self, tool_name: str, user_id: str) -> None:
        """发送工具开始通知的异步方法"""
        try:
            from src.service.websocket_manager import websocket_manager
            await websocket_manager.broadcast_tool_start(user_id, tool_name)
            logger.debug(f"成功发送工具开始通知: {tool_name} for user {user_id}")
        except Exception as e:
            logger.warning(f"发送工具开始通知失败: {e}")

    def invoke(self, input, config=None, **kwargs):
        """重写invoke方法，在工具调用前发送通知"""
        # 获取工具名称和用户ID
        tool_name = getattr(self, 'name', self.__class__.__name__.replace('Logged', '').lower())
        user_id = UserContext.get_user_id()
        
        # 记录工具使用情况和发送开始通知
        if user_id:
            tool_tracker.record_tool_usage(user_id, tool_name)
            # 立即发送通知
            self._send_tool_notification(tool_name, user_id)
        
        # 调用原始的invoke方法
        if hasattr(super(), 'invoke'):
            return super().invoke(input, config, **kwargs)
        else:
            # 如果没有invoke方法，回退到_run
            return self._run(**input if isinstance(input, dict) else {"input": input})

    async def ainvoke(self, input, config=None, **kwargs):
        """重写ainvoke方法，在工具调用前发送通知"""
        # 获取工具名称和用户ID
        tool_name = getattr(self, 'name', self.__class__.__name__.replace('Logged', '').lower())
        user_id = UserContext.get_user_id()
        
        # 记录工具使用情况和发送开始通知
        if user_id:
            tool_tracker.record_tool_usage(user_id, tool_name)
            # 立即发送异步通知
            await self._send_tool_notification_async(tool_name, user_id)
        
        # 调用原始的ainvoke方法
        if hasattr(super(), 'ainvoke'):
            return await super().ainvoke(input, config, **kwargs)
        else:
            # 如果没有ainvoke方法，回退到_arun或_run
            if hasattr(self, '_arun'):
                return await self._arun(**input if isinstance(input, dict) else {"input": input})
            else:
                return self._run(**input if isinstance(input, dict) else {"input": input})

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Override _run method to add logging and tool usage tracking."""
        self._log_operation("_run", *args, **kwargs)
        
        # 获取工具名称和用户ID
        tool_name = getattr(self, 'name', self.__class__.__name__.replace('Logged', '').lower())
        user_id = UserContext.get_user_id()
        
        # 如果还没有记录工具使用（可能是直接调用_run），则记录并发送通知
        if user_id and not tool_tracker.is_tool_active(user_id, tool_name):
            tool_tracker.record_tool_usage(user_id, tool_name)
            self._send_tool_notification(tool_name, user_id)
        
        # 执行工具
        success = True
        result = None
        try:
            result = super()._run(*args, **kwargs)
            logger.debug(
                f"Tool {self.__class__.__name__.replace('Logged', '')} returned: {result}"
            )
        except Exception as e:
            success = False
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
    
    # 应用早期通知装饰器
    LoggedTool = early_tool_notification(LoggedTool)
    
    return LoggedTool
