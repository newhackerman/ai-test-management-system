"""
阿里通义千问API接口

本模块提供阿里通义千问的API接口，包括：
1. 聊天完成接口
2. 流式聊天接口
3. 模型管理接口
4. 使用统计接口
5. 配置管理接口

主要功能：
- 智能聊天对话
- 模型推荐和选择
- 使用统计和成本分析
- 健康状态监控
- 配置管理
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from ...services.aliyun_tongyi_service import (
    get_tongyi_service, 
    AliyunTongyiService,
    TongyiModel,
    TaskComplexity,
    ModelRecommendation
)
from ...services.auth import get_current_user
from ...models.user import User
from ...adapters.base import ChatMessage, MessageRole

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic模型定义
class ChatMessageRequest(BaseModel):
    """聊天消息请求模型"""
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    messages: List[ChatMessageRequest] = Field(..., description="对话消息列表")
    model: Optional[str] = Field(None, description="指定模型")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="随机性控制")
    max_tokens: Optional[int] = Field(None, ge=1, le=32768, description="最大输出长度")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="核采样参数")
    stream: bool = Field(False, description="是否流式输出")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    priority: Optional[str] = Field("balanced", description="优先级: speed, balanced, quality")
    max_cost_per_request: Optional[float] = Field(None, description="单次请求最大成本")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""
    id: str
    model: str
    content: str
    usage: Dict[str, int]
    response_time: float
    confidence_score: Optional[float] = None
    finish_reason: Optional[str] = None
    created_at: str


class ModelRecommendationResponse(BaseModel):
    """模型推荐响应模型"""
    recommended_model: str
    confidence: float
    reasoning: str
    estimated_cost: float
    estimated_time: float


class UsageStatisticsResponse(BaseModel):
    """使用统计响应模型"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_tokens: int
    total_cost: float
    avg_response_time: float
    model_usage: Dict[str, int]
    cost_per_request: float


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    healthy: bool
    adapter_stats: Dict[str, Any]
    usage_stats: Dict[str, Any]
    available_models: List[str]
    error: Optional[str] = None


@router.post("/chat/completions", response_model=ChatCompletionResponse, summary="聊天完成")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    阿里通义千问聊天完成接口
    
    支持多种模型和参数配置，自动优化中文内容。
    """
    try:
        # 转换消息格式
        messages = []
        for msg in request.messages:
            try:
                role = MessageRole(msg.role.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid message role: {msg.role}")
            
            messages.append(ChatMessage(
                role=role,
                content=msg.content,
                name=msg.name
            ))
        
        # 检查流式请求
        if request.stream:
            return await _handle_stream_request(
                messages, request, current_user.id, tongyi_service
            )
        
        # 执行聊天完成
        response = await tongyi_service.chat_completion(
            messages=messages,
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            priority=request.priority,
            max_cost_per_request=request.max_cost_per_request
        )
        
        if not response.success:
            raise HTTPException(
                status_code=500,
                detail=f"Chat completion failed: {response.error_message}"
            )
        
        return ChatCompletionResponse(
            id=response.request_id,
            model=response.model,
            content=response.content,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            },
            response_time=response.response_time,
            confidence_score=response.confidence_score,
            finish_reason=response.finish_reason,
            created_at=response.timestamp.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_stream_request(messages: List[ChatMessage], 
                               request: ChatCompletionRequest,
                               user_id: int,
                               tongyi_service: AliyunTongyiService):
    """处理流式请求"""
    
    async def generate_stream():
        try:
            async for chunk in tongyi_service.stream_chat_completion(
                messages=messages,
                user_id=user_id,
                conversation_id=request.conversation_id,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                priority=request.priority,
                max_cost_per_request=request.max_cost_per_request
            ):
                # 构建SSE格式的数据
                chunk_data = {
                    "id": chunk.request_id,
                    "object": "chat.completion.chunk",
                    "created": int(chunk.timestamp.timestamp()),
                    "model": chunk.metadata.get("model", "unknown"),
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": chunk.content
                        },
                        "finish_reason": "stop" if chunk.is_final else None
                    }]
                }
                
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                if chunk.is_final:
                    yield "data: [DONE]\n\n"
                    break
                    
        except Exception as e:
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "stream_error"
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.get("/models", summary="获取可用模型")
async def get_available_models(
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    获取阿里通义千问可用模型列表
    
    返回所有支持的模型及其详细信息。
    """
    try:
        if not tongyi_service.adapter:
            return {"models": [], "total_count": 0}

        models = await tongyi_service.adapter.get_available_models()
        
        # 添加模型详细信息
        model_details = []
        for model in models:
            info = tongyi_service.adapter.get_model_info(model)
            model_details.append({
                "id": model,
                "name": info.get("name", model),
                "description": f"通义千问{model.replace('qwen-', '').upper()}模型",
                "max_tokens": info.get("max_tokens", 8192),
                "context_window": info.get("context_window", 8192),
                "cost_per_1k_tokens": info.get("cost_per_1k_tokens", 0.02),
                "strengths": info.get("strengths", ["通用对话"]),
                "use_cases": info.get("use_cases", ["通用任务"])
            })
        
        return {
            "models": model_details,
            "total_count": len(model_details)
        }
        
    except Exception as e:
        logger.error(f"Get models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ModelRecommendationRequest(BaseModel):
    """模型推荐请求模型"""
    task_description: str = Field(..., description="任务描述")
    cost_priority: bool = Field(False, description="是否优先考虑成本")


@router.post("/models/recommend", response_model=List[ModelRecommendationResponse], summary="模型推荐")
async def recommend_models(
    request: ModelRecommendationRequest,
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    根据任务描述推荐最适合的模型
    
    分析任务复杂度和需求，推荐最佳模型选择。
    """
    try:
        recommendations = await tongyi_service.get_model_recommendations(
            request.task_description, request.cost_priority
        )
        
        return [
            ModelRecommendationResponse(
                recommended_model=rec.recommended_model.value,
                confidence=rec.confidence,
                reasoning=rec.reasoning,
                estimated_cost=rec.estimated_cost,
                estimated_time=rec.estimated_time
            )
            for rec in recommendations
        ]
        
    except Exception as e:
        logger.error(f"Model recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/statistics", response_model=UsageStatisticsResponse, summary="使用统计")
async def get_usage_statistics(
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    获取阿里通义千问使用统计
    
    包括请求数量、成功率、Token使用、成本等信息。
    """
    try:
        if not tongyi_service.adapter:
            return UsageStatisticsResponse(
                total_requests=0, successful_requests=0, failed_requests=0,
                success_rate=0.0, total_tokens=0, total_cost=0.0,
                avg_response_time=0.0, model_usage={}, cost_per_request=0.0
            )

        stats = await tongyi_service.get_usage_statistics()

        return UsageStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Get usage statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthCheckResponse, summary="健康检查")
async def health_check(
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    阿里通义千问服务健康检查
    
    检查服务状态、适配器状态、使用统计等。
    """
    try:
        health_info = await tongyi_service.health_check()
        
        return HealthCheckResponse(**health_info)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            healthy=False,
            adapter_stats={},
            usage_stats={},
            available_models=[],
            error=str(e)
        )


class TestConnectionRequest(BaseModel):
    """测试连接请求模型"""
    test_message: str = Field("你好，请介绍一下通义千问。", description="测试消息")
    model: Optional[str] = Field(None, description="测试模型")


@router.post("/test", summary="测试连接")
async def test_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    测试阿里通义千问连接
    
    发送测试消息验证服务是否正常工作。
    """
    try:
        messages = [ChatMessage(role=MessageRole.USER, content=request.test_message)]
        
        response = await tongyi_service.chat_completion(
            messages=messages,
            user_id=current_user.id,
            model=request.model or "qwen-turbo",  # 使用最快的模型进行测试
            max_tokens=100
        )
        
        return {
            "success": response.success,
            "model": response.model,
            "content": response.content,
            "response_time": response.response_time,
            "usage": {
                "total_tokens": response.usage.total_tokens if response.usage else 0
            },
            "test_message": test_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Test connection error: {e}")
        return {
            "success": False,
            "error": str(e),
            "test_message": test_message,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/config", summary="获取配置信息")
async def get_config_info(
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    获取阿里通义千问配置信息
    
    返回当前服务配置和模型配置。
    """
    try:
        return {
            "service_initialized": tongyi_service.adapter is not None,
            "chinese_optimization": tongyi_service.chinese_optimization,
            "model_configs": {
                model.value: {
                    "cost_per_1k_tokens": config["cost_per_1k_tokens"],
                    "avg_response_time": config["avg_response_time"],
                    "quality_score": config["quality_score"],
                    "max_concurrent": config["max_concurrent"],
                    "strengths": config.get("strengths", []),
                    "use_cases": config.get("use_cases", [])
                }
                for model, config in tongyi_service.model_configs.items()
            },
            "available_models": await tongyi_service.adapter.get_available_models() if tongyi_service.adapter else []
        }
        
    except Exception as e:
        logger.error(f"Get config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChineseOptimizationRequest(BaseModel):
    """中文优化配置请求模型"""
    enable_context_enhancement: bool = Field(True, description="启用上下文增强")
    use_chinese_punctuation: bool = Field(True, description="使用中文标点")
    optimize_for_chinese_culture: bool = Field(True, description="中文文化优化")
    enable_idiom_usage: bool = Field(True, description="启用成语使用")
    enhance_politeness: bool = Field(True, description="增强礼貌用语")
    prefer_formal_language: bool = Field(False, description="偏好正式语言")


@router.post("/config/chinese-optimization", summary="配置中文优化")
async def update_chinese_optimization(
    request: ChineseOptimizationRequest,
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    配置中文内容优化选项
    
    调整中文内容处理和优化策略。
    """
    try:
        # 更新配置
        tongyi_service.chinese_optimization.update({
            "enable_context_enhancement": request.enable_context_enhancement,
            "use_chinese_punctuation": request.use_chinese_punctuation,
            "optimize_for_chinese_culture": request.optimize_for_chinese_culture,
            "enable_idiom_usage": request.enable_idiom_usage,
            "enhance_politeness": request.enhance_politeness,
            "prefer_formal_language": request.prefer_formal_language
        })
        
        return {
            "success": True,
            "message": "中文优化配置已更新",
            "config": tongyi_service.chinese_optimization,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Update chinese optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}/info", summary="获取模型详细信息")
async def get_model_info(
    model_id: str,
    current_user: User = Depends(get_current_user),
    tongyi_service: AliyunTongyiService = Depends(get_tongyi_service)
):
    """
    获取指定模型的详细信息
    
    包括模型能力、成本、性能等详细信息。
    """
    try:
        if not tongyi_service.adapter:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        available_models = await tongyi_service.adapter.get_available_models()
        
        if model_id not in available_models:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        model_info = tongyi_service.adapter.get_model_info(model_id)
        
        return {
            "model_id": model_id,
            "name": f"通义千问{model_id.replace('qwen-', '').upper()}",
            "description": f"阿里云通义千问{model_id.replace('qwen-', '').upper()}模型",
            "provider": "Aliyun",
            "capabilities": model_info.get("strengths", []),
            "use_cases": model_info.get("use_cases", []),
            "pricing": {
                "cost_per_1k_tokens": model_info.get("cost_per_1k_tokens", 0.02),
                "currency": "CNY"
            },
            "performance": {
                "avg_response_time": model_info.get("avg_response_time", 2.0),
                "quality_score": model_info.get("quality_score", 0.8),
                "max_concurrent": model_info.get("max_concurrent", 10)
            },
            "limits": {
                "max_tokens": model_info.get("max_tokens", 8192),
                "context_window": model_info.get("context_window", 8192)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get model info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))