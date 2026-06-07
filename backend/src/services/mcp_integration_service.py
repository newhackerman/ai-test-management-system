"""
MCP集成服务

本模块提供MCP客户端与AI助手服务的集成，实现：
1. MCP服务器的自动发现和连接
2. AI请求的智能路由到MCP服务器
3. MCP响应的处理和格式化
4. 服务健康监控和故障转移

主要功能：
- 统一的AI服务调用接口
- 多MCP服务器负载均衡
- 自动重连和故障恢复
- 请求缓存和优化
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from ..utils.mcp_client import MCPClient, MCPServerConfig, get_mcp_client
from ..utils.mcp_config import get_mcp_config_manager, load_mcp_config

logger = logging.getLogger(__name__)


class AIRequestType(Enum):
    """AI请求类型"""
    CHAT_COMPLETION = "chat_completion"
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"


class MCPIntegrationService:
    """
    MCP集成服务
    
    负责管理MCP客户端与AI助手服务的集成，提供统一的AI服务调用接口。
    """
    
    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.config_manager = None
        self.server_capabilities: Dict[str, List[str]] = {}
        self.server_health: Dict[str, bool] = {}
        self.request_stats: Dict[str, Dict[str, int]] = {}
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 服务器能力映射
        self.capability_mapping = {
            "openai": ["chat_completion", "text_generation", "code_generation"],
            "anthropic": ["chat_completion", "text_generation", "analysis"],
            "baidu-wenxin": ["chat_completion", "translation", "summarization"],
            "aliyun-tongyi": ["chat_completion", "translation", "analysis"],
            "google-gemini": ["chat_completion", "text_generation", "analysis"]
        }
    
    async def initialize(self, config_path: Optional[str] = None) -> bool:
        """
        初始化MCP集成服务
        
        Args:
            config_path: MCP配置文件路径
            
        Returns:
            bool: 是否初始化成功
        """
        try:
            logger.info("Initializing MCP Integration Service...")
            
            # 加载配置
            self.config_manager = await load_mcp_config(config_path)
            
            # 获取MCP客户端
            self.mcp_client = await get_mcp_client()
            
            # 加载所有服务器配置
            configs = await self.config_manager.get_all_configs()
            
            # 连接到所有启用的服务器
            connected_count = 0
            for server_name, config in configs.items():
                if not config.disabled:
                    try:
                        success = await self.mcp_client.add_server(config)
                        if success:
                            connected_count += 1
                            self.server_health[server_name] = True
                            self.server_capabilities[server_name] = self.capability_mapping.get(
                                server_name, ["chat_completion"]
                            )
                            self.request_stats[server_name] = {
                                "total": 0, "success": 0, "failed": 0
                            }
                            logger.info(f"Connected to MCP server: {server_name}")
                        else:
                            self.server_health[server_name] = False
                            logger.warning(f"Failed to connect to MCP server: {server_name}")
                    except Exception as e:
                        logger.error(f"Error connecting to MCP server {server_name}: {str(e)}")
                        self.server_health[server_name] = False
            
            # 启动健康检查
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._initialized = True
            logger.info(f"MCP Integration Service initialized with {connected_count} servers")
            
            return connected_count > 0
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Integration Service: {str(e)}")
            return False
    
    async def send_ai_request(self, request_type: AIRequestType, 
                             content: str, 
                             server_preference: Optional[str] = None,
                             **kwargs) -> Dict[str, Any]:
        """
        发送AI请求
        
        Args:
            request_type: 请求类型
            content: 请求内容
            server_preference: 首选服务器
            **kwargs: 其他参数
            
        Returns:
            Dict: AI响应结果
        """
        if not self._initialized:
            raise RuntimeError("MCP Integration Service not initialized")
        
        # 选择最适合的服务器
        server_name = await self._select_server(request_type, server_preference)
        if not server_name:
            raise RuntimeError("No available MCP server for this request")
        
        try:
            # 构建请求参数
            request_params = await self._build_request_params(
                request_type, content, server_name, **kwargs
            )
            
            # 发送请求
            start_time = datetime.utcnow()
            
            # 根据服务器类型选择合适的方法
            method = self._get_method_for_server(server_name, request_type)
            
            result = await self.mcp_client.send_request(
                server_name, method, request_params, timeout=30
            )
            
            # 处理响应
            processed_result = await self._process_response(
                result, server_name, request_type
            )
            
            # 更新统计
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._update_request_stats(server_name, True, processing_time)
            
            logger.info(f"AI request completed via {server_name} in {processing_time:.2f}s")
            
            return {
                "success": True,
                "result": processed_result,
                "server": server_name,
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await self._update_request_stats(server_name, False)
            logger.error(f"AI request failed via {server_name}: {str(e)}")
            
            # 尝试故障转移
            if server_preference is None:
                fallback_server = await self._get_fallback_server(server_name, request_type)
                if fallback_server:
                    logger.info(f"Attempting fallback to {fallback_server}")
                    return await self.send_ai_request(
                        request_type, content, fallback_server, **kwargs
                    )
            
            return {
                "success": False,
                "error": str(e),
                "server": server_name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _select_server(self, request_type: AIRequestType, 
                           preference: Optional[str] = None) -> Optional[str]:
        """选择最适合的服务器"""
        # 如果指定了首选服务器且可用，优先使用
        if preference and preference in self.server_health:
            if self.server_health[preference] and request_type.value in self.server_capabilities.get(preference, []):
                return preference
        
        # 找到支持该请求类型的健康服务器
        candidates = []
        for server_name, capabilities in self.server_capabilities.items():
            if (request_type.value in capabilities and 
                self.server_health.get(server_name, False)):
                candidates.append(server_name)
        
        if not candidates:
            return None
        
        # 基于负载选择服务器（简单的轮询策略）
        return min(candidates, key=lambda s: self.request_stats[s]["total"])
    
    async def _get_fallback_server(self, failed_server: str, 
                                 request_type: AIRequestType) -> Optional[str]:
        """获取故障转移服务器"""
        candidates = []
        for server_name, capabilities in self.server_capabilities.items():
            if (server_name != failed_server and 
                request_type.value in capabilities and 
                self.server_health.get(server_name, False)):
                candidates.append(server_name)
        
        if candidates:
            return min(candidates, key=lambda s: self.request_stats[s]["failed"])
        
        return None
    
    def _get_method_for_server(self, server_name: str, request_type: AIRequestType) -> str:
        """获取服务器对应的方法名"""
        method_mapping = {
            "openai": {
                AIRequestType.CHAT_COMPLETION: "chat/completions",
                AIRequestType.TEXT_GENERATION: "completions",
                AIRequestType.CODE_GENERATION: "chat/completions"
            },
            "anthropic": {
                AIRequestType.CHAT_COMPLETION: "messages/create",
                AIRequestType.TEXT_GENERATION: "messages/create",
                AIRequestType.ANALYSIS: "messages/create"
            },
            "baidu-wenxin": {
                AIRequestType.CHAT_COMPLETION: "chat",
                AIRequestType.TRANSLATION: "translate",
                AIRequestType.SUMMARIZATION: "summarize"
            }
        }
        
        server_methods = method_mapping.get(server_name, {})
        return server_methods.get(request_type, "chat")
    
    async def _build_request_params(self, request_type: AIRequestType, 
                                  content: str, server_name: str, 
                                  **kwargs) -> Dict[str, Any]:
        """构建请求参数"""
        base_params = {
            "content": content,
            "type": request_type.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 根据服务器类型调整参数格式
        if server_name == "openai":
            if request_type == AIRequestType.CHAT_COMPLETION:
                base_params.update({
                    "model": kwargs.get("model", "gpt-3.5-turbo"),
                    "messages": [{"role": "user", "content": content}],
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 1000)
                })
        elif server_name == "anthropic":
            base_params.update({
                "model": kwargs.get("model", "claude-3-sonnet-20240229"),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "messages": [{"role": "user", "content": content}]
            })
        elif server_name in ["baidu-wenxin", "aliyun-tongyi"]:
            base_params.update({
                "prompt": content,
                "temperature": kwargs.get("temperature", 0.7),
                "max_length": kwargs.get("max_tokens", 1000)
            })
        
        return base_params
    
    async def _process_response(self, response: Any, server_name: str, 
                              request_type: AIRequestType) -> Dict[str, Any]:
        """处理AI响应"""
        processed = {
            "raw_response": response,
            "server": server_name,
            "request_type": request_type.value
        }
        
        # 根据服务器类型解析响应
        if isinstance(response, dict):
            if server_name == "openai":
                if "choices" in response and response["choices"]:
                    processed["content"] = response["choices"][0].get("message", {}).get("content", "")
                    processed["usage"] = response.get("usage", {})
            elif server_name == "anthropic":
                if "content" in response:
                    processed["content"] = response["content"][0].get("text", "") if response["content"] else ""
                    processed["usage"] = response.get("usage", {})
            else:
                # 通用处理
                processed["content"] = str(response)
        else:
            processed["content"] = str(response)
        
        return processed
    
    async def _update_request_stats(self, server_name: str, success: bool, 
                                  processing_time: float = 0):
        """更新请求统计"""
        if server_name in self.request_stats:
            stats = self.request_stats[server_name]
            stats["total"] += 1
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self._initialized:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                if self.mcp_client:
                    health_results = await self.mcp_client.health_check()
                    
                    for server_name, is_healthy in health_results.items():
                        old_status = self.server_health.get(server_name, False)
                        self.server_health[server_name] = is_healthy
                        
                        if old_status != is_healthy:
                            status = "healthy" if is_healthy else "unhealthy"
                            logger.info(f"MCP server {server_name} is now {status}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
    
    async def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        if not self.mcp_client:
            return {}
        
        status = await self.mcp_client.get_all_server_status()
        
        # 添加额外信息
        for server_name in status:
            status[server_name].update({
                "health": self.server_health.get(server_name, False),
                "capabilities": self.server_capabilities.get(server_name, []),
                "stats": self.request_stats.get(server_name, {})
            })
        
        return status
    
    async def get_available_capabilities(self) -> Dict[str, List[str]]:
        """获取可用的AI能力"""
        capabilities = {}
        
        for server_name, server_capabilities in self.server_capabilities.items():
            if self.server_health.get(server_name, False):
                for capability in server_capabilities:
                    if capability not in capabilities:
                        capabilities[capability] = []
                    capabilities[capability].append(server_name)
        
        return capabilities
    
    async def shutdown(self):
        """关闭服务"""
        logger.info("Shutting down MCP Integration Service...")
        
        self._initialized = False
        
        # 取消健康检查任务
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # 关闭MCP客户端
        if self.mcp_client:
            await self.mcp_client.shutdown()
        
        # 关闭配置管理器
        if self.config_manager:
            await self.config_manager.shutdown()
        
        logger.info("MCP Integration Service shutdown complete")


# 全局服务实例
_mcp_integration_service: Optional[MCPIntegrationService] = None


async def get_mcp_integration_service() -> MCPIntegrationService:
    """获取全局MCP集成服务实例"""
    global _mcp_integration_service
    if _mcp_integration_service is None:
        _mcp_integration_service = MCPIntegrationService()
    return _mcp_integration_service


# 便捷函数
async def send_ai_chat_request(content: str, server: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """发送AI聊天请求的便捷函数"""
    service = await get_mcp_integration_service()
    return await service.send_ai_request(
        AIRequestType.CHAT_COMPLETION, content, server, **kwargs
    )


async def send_ai_code_request(content: str, server: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """发送AI代码生成请求的便捷函数"""
    service = await get_mcp_integration_service()
    return await service.send_ai_request(
        AIRequestType.CODE_GENERATION, content, server, **kwargs
    )


async def send_ai_analysis_request(content: str, server: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """发送AI分析请求的便捷函数"""
    service = await get_mcp_integration_service()
    return await service.send_ai_request(
        AIRequestType.ANALYSIS, content, server, **kwargs
    )