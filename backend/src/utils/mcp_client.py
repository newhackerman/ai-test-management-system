"""
MCP (Model Context Protocol) 客户端实现

本模块实现了MCP协议的基础客户端，用于与AI服务提供商进行通信。
MCP是一个标准化的协议，用于AI模型和应用程序之间的上下文共享和通信。

主要功能：
1. MCP服务器连接管理
2. 消息序列化和反序列化
3. 异步通信处理
4. 错误处理和重试机制
5. 连接健康检查

技术特性：
- 异步编程模式，支持高并发
- 标准JSON-RPC 2.0协议
- 自动重连和故障恢复
- 连接池管理
- 性能监控和日志记录
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import uuid

logger = logging.getLogger(__name__)


class MCPMessageType(Enum):
    """MCP消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPConnectionState(Enum):
    """MCP连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class MCPMessage:
    """MCP消息对象"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 移除None值
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """从字典创建消息对象"""
        return cls(**data)
    
    def is_request(self) -> bool:
        """是否为请求消息"""
        return self.method is not None and self.id is not None
    
    def is_response(self) -> bool:
        """是否为响应消息"""
        return self.id is not None and (self.result is not None or self.error is not None)
    
    def is_notification(self) -> bool:
        """是否为通知消息"""
        return self.method is not None and self.id is None


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60
    disabled: bool = False
    auto_approve: List[str] = None
    
    def __post_init__(self):
        if self.env is None:
            self.env = {}
        if self.auto_approve is None:
            self.auto_approve = []


class MCPConnection:
    """MCP连接对象"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.state = MCPConnectionState.DISCONNECTED
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected_at: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        self.message_count = 0
        self.error_count = 0
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        async with self._lock:
            if self.state in [MCPConnectionState.CONNECTED, MCPConnectionState.CONNECTING]:
                return True
            
            try:
                self.state = MCPConnectionState.CONNECTING
                logger.info(f"Connecting to MCP server: {self.config.name}")
                
                # 启动MCP服务器进程
                env = {**os.environ, **self.config.env}
                self.process = await asyncio.create_subprocess_exec(
                    self.config.command,
                    *self.config.args,
                    env=env,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # 等待进程启动
                await asyncio.sleep(0.5)
                
                # 检查进程是否正常启动
                if self.process.returncode is not None:
                    stderr_output = await self.process.stderr.read()
                    error_msg = stderr_output.decode('utf-8', errors='ignore')
                    raise RuntimeError(f"MCP server failed to start: {error_msg}")
                
                # 设置流读写器
                self.reader = self.process.stdout
                self.writer = self.process.stdin
                
                # 发送初始化消息
                await self._send_initialize()
                
                # 启动消息监听
                asyncio.create_task(self._message_listener())
                
                # 启动健康检查
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                self.state = MCPConnectionState.CONNECTED
                self.connected_at = datetime.utcnow()
                self.last_activity = datetime.utcnow()
                
                logger.info(f"Successfully connected to MCP server: {self.config.name}")
                return True
                
            except Exception as e:
                self.state = MCPConnectionState.FAILED
                logger.error(f"Failed to connect to MCP server {self.config.name}: {str(e)}")
                await self._cleanup()
                return False
    
    async def disconnect(self):
        """断开连接"""
        async with self._lock:
            logger.info(f"Disconnecting from MCP server: {self.config.name}")
            
            self.state = MCPConnectionState.DISCONNECTED
            
            # 取消健康检查任务
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 清理资源
            await self._cleanup()
            
            logger.info(f"Disconnected from MCP server: {self.config.name}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, 
                          timeout: Optional[float] = None) -> Any:
        """发送请求消息"""
        if self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError(f"MCP server {self.config.name} is not connected")
        
        request_id = str(uuid.uuid4())
        message = MCPMessage(
            id=request_id,
            method=method,
            params=params or {}
        )
        
        # 创建Future等待响应
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            # 发送消息
            await self._send_message(message)
            
            # 等待响应
            timeout = timeout or self.config.timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for method {method} on server {self.config.name}")
            raise
        except Exception as e:
            logger.error(f"Error sending request {method} to server {self.config.name}: {str(e)}")
            raise
        finally:
            # 清理pending request
            self.pending_requests.pop(request_id, None)
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """发送通知消息"""
        if self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError(f"MCP server {self.config.name} is not connected")
        
        message = MCPMessage(
            method=method,
            params=params or {}
        )
        
        await self._send_message(message)
    
    def add_event_handler(self, event: str, handler: Callable):
        """添加事件处理器"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: str, handler: Callable):
        """移除事件处理器"""
        if event in self.event_handlers:
            try:
                self.event_handlers[event].remove(handler)
            except ValueError:
                pass
    
    async def _send_initialize(self):
        """发送初始化消息"""
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {}
            },
            "clientInfo": {
                "name": "AI Assistant MCP Client",
                "version": "1.0.0"
            }
        }
        
        try:
            response = await self.send_request("initialize", init_params)
            logger.debug(f"MCP server {self.config.name} initialized: {response}")
            
            # 发送initialized通知
            await self.send_notification("notifications/initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server {self.config.name}: {str(e)}")
            raise
    
    async def _send_message(self, message: MCPMessage):
        """发送消息到MCP服务器"""
        if not self.writer:
            raise RuntimeError("MCP connection not established")
        
        try:
            # 序列化消息
            message_data = json.dumps(message.to_dict(), ensure_ascii=False)
            message_bytes = message_data.encode('utf-8') + b'\n'
            
            # 发送消息
            self.writer.write(message_bytes)
            await self.writer.drain()
            
            self.message_count += 1
            self.last_activity = datetime.utcnow()
            
            logger.debug(f"Sent message to {self.config.name}: {message.method or 'response'}")
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error sending message to {self.config.name}: {str(e)}")
            raise
    
    async def _message_listener(self):
        """消息监听循环"""
        logger.debug(f"Starting message listener for {self.config.name}")
        
        try:
            while self.state == MCPConnectionState.CONNECTED and self.reader:
                try:
                    # 读取一行消息
                    line = await self.reader.readline()
                    if not line:
                        logger.warning(f"MCP server {self.config.name} closed connection")
                        break
                    
                    # 解析消息
                    message_data = line.decode('utf-8').strip()
                    if not message_data:
                        continue
                    
                    message_dict = json.loads(message_data)
                    message = MCPMessage.from_dict(message_dict)
                    
                    # 处理消息
                    await self._handle_message(message)
                    
                    self.last_activity = datetime.utcnow()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from {self.config.name}: {str(e)}")
                    self.error_count += 1
                except Exception as e:
                    logger.error(f"Error processing message from {self.config.name}: {str(e)}")
                    self.error_count += 1
                    
        except Exception as e:
            logger.error(f"Message listener error for {self.config.name}: {str(e)}")
        finally:
            logger.debug(f"Message listener stopped for {self.config.name}")
            if self.state == MCPConnectionState.CONNECTED:
                self.state = MCPConnectionState.FAILED
    
    async def _handle_message(self, message: MCPMessage):
        """处理接收到的消息"""
        try:
            if message.is_response():
                # 处理响应消息
                await self._handle_response(message)
            elif message.is_request():
                # 处理请求消息
                await self._handle_request(message)
            elif message.is_notification():
                # 处理通知消息
                await self._handle_notification(message)
            else:
                logger.warning(f"Unknown message type from {self.config.name}: {message.to_dict()}")
                
        except Exception as e:
            logger.error(f"Error handling message from {self.config.name}: {str(e)}")
    
    async def _handle_response(self, message: MCPMessage):
        """处理响应消息"""
        request_id = message.id
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            
            if message.error:
                # 错误响应
                error = Exception(f"MCP Error: {message.error}")
                future.set_exception(error)
            else:
                # 成功响应
                future.set_result(message.result)
        else:
            logger.warning(f"Received response for unknown request {request_id} from {self.config.name}")
    
    async def _handle_request(self, message: MCPMessage):
        """处理请求消息"""
        # 目前客户端不处理来自服务器的请求
        # 发送方法不支持的错误响应
        error_response = MCPMessage(
            id=message.id,
            error={
                "code": -32601,
                "message": "Method not found",
                "data": f"Client does not support method: {message.method}"
            }
        )
        await self._send_message(error_response)
    
    async def _handle_notification(self, message: MCPMessage):
        """处理通知消息"""
        method = message.method
        
        # 触发事件处理器
        if method in self.event_handlers:
            for handler in self.event_handlers[method]:
                try:
                    await handler(message.params or {})
                except Exception as e:
                    logger.error(f"Error in event handler for {method}: {str(e)}")
        
        logger.debug(f"Received notification {method} from {self.config.name}")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        logger.debug(f"Starting health check for {self.config.name}")
        
        try:
            while self.state == MCPConnectionState.CONNECTED:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self.state != MCPConnectionState.CONNECTED:
                    break
                
                try:
                    # 发送ping请求检查连接
                    await self.send_request("ping", timeout=5.0)
                    logger.debug(f"Health check passed for {self.config.name}")
                    
                except Exception as e:
                    logger.warning(f"Health check failed for {self.config.name}: {str(e)}")
                    self.error_count += 1
                    
                    # 如果错误过多，标记连接为失败
                    if self.error_count > 5:
                        logger.error(f"Too many errors for {self.config.name}, marking as failed")
                        self.state = MCPConnectionState.FAILED
                        break
                        
        except asyncio.CancelledError:
            logger.debug(f"Health check cancelled for {self.config.name}")
        except Exception as e:
            logger.error(f"Health check error for {self.config.name}: {str(e)}")
    
    async def _cleanup(self):
        """清理连接资源"""
        try:
            # 取消所有pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.cancel()
            self.pending_requests.clear()
            
            # 关闭流
            if self.writer:
                try:
                    self.writer.close()
                    await self.writer.wait_closed()
                except Exception:
                    pass
                self.writer = None
            
            self.reader = None
            
            # 终止进程
            if self.process:
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Force killing MCP server process for {self.config.name}")
                    self.process.kill()
                    await self.process.wait()
                except Exception as e:
                    logger.error(f"Error terminating MCP server process for {self.config.name}: {str(e)}")
                finally:
                    self.process = None
            
        except Exception as e:
            logger.error(f"Error during cleanup for {self.config.name}: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "pending_requests": len(self.pending_requests)
        }


class MCPClient:
    """
    MCP (Model Context Protocol) 客户端
    
    这是MCP协议的核心客户端实现，负责管理与多个MCP服务器的连接，
    提供统一的接口用于AI服务通信。
    
    主要功能：
    1. 多服务器连接管理
    2. 消息路由和负载均衡
    3. 自动重连和故障恢复
    4. 性能监控和统计
    5. 事件处理和通知
    
    使用示例：
    ```python
    client = MCPClient()
    
    # 添加服务器配置
    config = MCPServerConfig(
        name="openai",
        command="uvx",
        args=["openai-mcp-server"],
        env={"OPENAI_API_KEY": "your-key"}
    )
    await client.add_server(config)
    
    # 发送请求
    result = await client.send_request("openai", "chat/completions", {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}]
    })
    ```
    """
    
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self._lock = asyncio.Lock()
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_connections": 0,
            "active_connections": 0
        }
        
        logger.info("MCP Client initialized")
    
    async def add_server(self, config: MCPServerConfig) -> bool:
        """
        添加MCP服务器
        
        Args:
            config: 服务器配置
            
        Returns:
            bool: 是否成功添加
        """
        async with self._lock:
            if config.disabled:
                logger.info(f"MCP server {config.name} is disabled, skipping")
                return False
            
            if config.name in self.connections:
                logger.warning(f"MCP server {config.name} already exists")
                return False
            
            try:
                # 创建连接
                connection = MCPConnection(config)
                
                # 尝试连接
                if await connection.connect():
                    self.connections[config.name] = connection
                    self.server_configs[config.name] = config
                    self.stats["total_connections"] += 1
                    self.stats["active_connections"] += 1
                    
                    logger.info(f"Successfully added MCP server: {config.name}")
                    return True
                else:
                    logger.error(f"Failed to connect to MCP server: {config.name}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error adding MCP server {config.name}: {str(e)}")
                return False
    
    async def remove_server(self, server_name: str) -> bool:
        """
        移除MCP服务器
        
        Args:
            server_name: 服务器名称
            
        Returns:
            bool: 是否成功移除
        """
        async with self._lock:
            if server_name not in self.connections:
                logger.warning(f"MCP server {server_name} not found")
                return False
            
            try:
                connection = self.connections[server_name]
                await connection.disconnect()
                
                del self.connections[server_name]
                del self.server_configs[server_name]
                self.stats["active_connections"] -= 1
                
                logger.info(f"Successfully removed MCP server: {server_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error removing MCP server {server_name}: {str(e)}")
                return False
    
    async def send_request(self, server_name: str, method: str, 
                          params: Optional[Dict[str, Any]] = None,
                          timeout: Optional[float] = None) -> Any:
        """
        发送请求到指定服务器
        
        Args:
            server_name: 服务器名称
            method: 方法名
            params: 参数
            timeout: 超时时间
            
        Returns:
            Any: 响应结果
            
        Raises:
            ValueError: 服务器不存在
            RuntimeError: 服务器不可用
        """
        self.stats["total_requests"] += 1
        
        try:
            if server_name not in self.connections:
                raise ValueError(f"MCP server {server_name} not found")
            
            connection = self.connections[server_name]
            
            if connection.state != MCPConnectionState.CONNECTED:
                # 尝试重连
                if not await self._reconnect_server(server_name):
                    raise RuntimeError(f"MCP server {server_name} is not available")
            
            result = await connection.send_request(method, params, timeout)
            self.stats["successful_requests"] += 1
            
            logger.debug(f"Successfully sent request {method} to {server_name}")
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"Error sending request {method} to {server_name}: {str(e)}")
            raise
    
    async def send_notification(self, server_name: str, method: str,
                               params: Optional[Dict[str, Any]] = None):
        """
        发送通知到指定服务器
        
        Args:
            server_name: 服务器名称
            method: 方法名
            params: 参数
        """
        try:
            if server_name not in self.connections:
                raise ValueError(f"MCP server {server_name} not found")
            
            connection = self.connections[server_name]
            
            if connection.state != MCPConnectionState.CONNECTED:
                # 尝试重连
                if not await self._reconnect_server(server_name):
                    raise RuntimeError(f"MCP server {server_name} is not available")
            
            await connection.send_notification(method, params)
            logger.debug(f"Successfully sent notification {method} to {server_name}")
            
        except Exception as e:
            logger.error(f"Error sending notification {method} to {server_name}: {str(e)}")
            raise
    
    async def broadcast_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """
        广播通知到所有服务器
        
        Args:
            method: 方法名
            params: 参数
        """
        tasks = []
        for server_name in self.connections.keys():
            task = asyncio.create_task(
                self.send_notification(server_name, method, params)
            )
            tasks.append(task)
        
        if tasks:
            # 等待所有通知发送完成，忽略错误
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_server_list(self) -> List[str]:
        """获取服务器列表"""
        return list(self.connections.keys())
    
    async def get_server_status(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        获取服务器状态
        
        Args:
            server_name: 服务器名称
            
        Returns:
            Dict: 服务器状态信息
        """
        if server_name not in self.connections:
            return None
        
        connection = self.connections[server_name]
        return connection.get_stats()
    
    async def get_all_server_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务器状态"""
        status = {}
        for server_name, connection in self.connections.items():
            status[server_name] = connection.get_stats()
        return status
    
    async def health_check(self, server_name: Optional[str] = None) -> Dict[str, bool]:
        """
        健康检查
        
        Args:
            server_name: 服务器名称，None表示检查所有服务器
            
        Returns:
            Dict: 健康检查结果
        """
        results = {}
        
        servers_to_check = [server_name] if server_name else list(self.connections.keys())
        
        for name in servers_to_check:
            if name not in self.connections:
                results[name] = False
                continue
            
            connection = self.connections[name]
            try:
                # 发送ping请求
                await connection.send_request("ping", timeout=5.0)
                results[name] = True
            except Exception:
                results[name] = False
        
        return results
    
    async def _reconnect_server(self, server_name: str) -> bool:
        """
        重连服务器
        
        Args:
            server_name: 服务器名称
            
        Returns:
            bool: 是否重连成功
        """
        if server_name not in self.connections:
            return False
        
        try:
            logger.info(f"Attempting to reconnect to MCP server: {server_name}")
            
            connection = self.connections[server_name]
            config = self.server_configs[server_name]
            
            # 断开现有连接
            await connection.disconnect()
            
            # 创建新连接
            new_connection = MCPConnection(config)
            
            # 尝试连接
            if await new_connection.connect():
                self.connections[server_name] = new_connection
                logger.info(f"Successfully reconnected to MCP server: {server_name}")
                return True
            else:
                logger.error(f"Failed to reconnect to MCP server: {server_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error reconnecting to MCP server {server_name}: {str(e)}")
            return False
    
    async def shutdown(self):
        """关闭所有连接"""
        logger.info("Shutting down MCP client")
        
        tasks = []
        for connection in self.connections.values():
            task = asyncio.create_task(connection.disconnect())
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.connections.clear()
        self.server_configs.clear()
        self.stats["active_connections"] = 0
        
        logger.info("MCP client shutdown complete")
    
    def get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            **self.stats,
            "servers": list(self.connections.keys()),
            "uptime": (datetime.utcnow() - datetime.utcnow()).total_seconds()  # 简化实现
        }


# 全局MCP客户端实例
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """获取全局MCP客户端实例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def initialize_mcp_client(configs: List[MCPServerConfig]) -> MCPClient:
    """
    初始化MCP客户端
    
    Args:
        configs: 服务器配置列表
        
    Returns:
        MCPClient: 初始化的客户端实例
    """
    client = await get_mcp_client()
    
    # 添加所有服务器
    for config in configs:
        try:
            await client.add_server(config)
        except Exception as e:
            logger.error(f"Failed to add MCP server {config.name}: {str(e)}")
    
    return client


# 便捷函数
async def send_mcp_request(server_name: str, method: str, 
                          params: Optional[Dict[str, Any]] = None) -> Any:
    """发送MCP请求的便捷函数"""
    client = await get_mcp_client()
    return await client.send_request(server_name, method, params)


async def send_mcp_notification(server_name: str, method: str,
                               params: Optional[Dict[str, Any]] = None):
    """发送MCP通知的便捷函数"""
    client = await get_mcp_client()
    await client.send_notification(server_name, method, params)