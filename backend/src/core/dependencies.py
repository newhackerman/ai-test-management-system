"""
FastAPI依赖注入函数

提供常用的依赖注入函数，用于FastAPI路由中获取服务实例
"""

from fastapi import Depends, Request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.ai_router_service import AIRouterService
    from ..services.ai_assistant_service import AIAssistantService
    from ..services.conversation_service import ConversationService

from .fastapi_integration import get_di_container


async def get_ai_router_service(request: Request) -> 'AIRouterService':
    """获取AI路由服务实例"""
    from ..services.ai_router_service import AIRouterService
    container = get_di_container(request)
    return await container.get_service_async(AIRouterService)


async def get_ai_assistant_service(request: Request) -> 'AIAssistantService':
    """获取AI助手服务实例"""
    from ..services.ai_assistant_service import AIAssistantService
    container = get_di_container(request)
    return await container.get_service_async(AIAssistantService)


async def get_conversation_service(request: Request) -> 'ConversationService':
    """获取对话服务实例"""
    from ..services.conversation_service import ConversationService
    container = get_di_container(request)
    return await container.get_service_async(ConversationService)