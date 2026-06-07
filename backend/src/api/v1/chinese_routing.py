"""
中文内容优化路由API

提供中文内容分析、路由决策和优化建议的API接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from ...services.ai_router_service import AIRouterService, AIRequest, TaskType, RoutingStrategy
from ...core.dependencies import get_ai_router_service
from ...core.auth import get_current_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ChineseContentAnalysisRequest(BaseModel):
    """中文内容分析请求"""
    content: str = Field(..., description="待分析的中文内容", min_length=1, max_length=10000)


class ChineseContentAnalysisResponse(BaseModel):
    """中文内容分析响应"""
    is_chinese: bool = Field(..., description="是否为中文内容")
    content_type: str = Field(..., description="内容类型")
    complexity: str = Field(..., description="复杂度等级")
    cultural_context: str = Field(..., description="文化背景")
    chinese_ratio: float = Field(..., description="中文字符占比")
    traditional_ratio: float = Field(..., description="繁体字占比")
    technical_terms: List[str] = Field(..., description="技术术语列表")
    cultural_references: List[str] = Field(..., description="文化引用列表")
    formality_level: float = Field(..., description="正式程度 (0-1)")
    confidence_score: float = Field(..., description="分析置信度 (0-1)")
    language_features: Dict[str, bool] = Field(..., description="语言特征")
    domain: Optional[str] = Field(None, description="专业领域")
    industry_terms: List[str] = Field(..., description="行业术语列表")


class ChineseProviderRankingResponse(BaseModel):
    """中文提供商排名响应"""
    provider: str = Field(..., description="提供商名称")
    score: float = Field(..., description="适配分数")
    is_available: bool = Field(..., description="是否可用")
    success_rate: float = Field(..., description="成功率")
    response_time: float = Field(..., description="响应时间")
    current_load: int = Field(..., description="当前负载")
    chinese_capabilities: Dict[str, float] = Field(..., description="中文能力评分")


class ChineseOptimizationSuggestionsResponse(BaseModel):
    """中文优化建议响应"""
    content_analysis: Dict[str, Any] = Field(..., description="内容分析结果")
    provider_optimization: Dict[str, Any] = Field(..., description="提供商优化策略")
    quality_expectations: Dict[str, Any] = Field(..., description="质量预期")
    routing_info: Dict[str, Any] = Field(..., description="路由信息")


class ChineseRoutingRequest(BaseModel):
    """中文路由请求"""
    content: str = Field(..., description="中文内容", min_length=1, max_length=10000)
    user_id: int = Field(..., description="用户ID")
    routing_strategy: Optional[str] = Field("balanced", description="路由策略")
    max_tokens: Optional[int] = Field(None, description="最大Token数")
    temperature: Optional[float] = Field(None, description="温度参数")
    priority: str = Field("normal", description="优先级")


class ChineseRoutingResponse(BaseModel):
    """中文路由响应"""
    selected_provider: str = Field(..., description="选择的提供商")
    confidence: float = Field(..., description="置信度")
    reasoning: str = Field(..., description="选择理由")
    fallback_providers: List[str] = Field(..., description="备选提供商")
    estimated_cost: float = Field(..., description="预估成本")
    estimated_time: float = Field(..., description="预估时间")
    routing_strategy_used: str = Field(..., description="使用的路由策略")


class ChineseRoutingStatisticsResponse(BaseModel):
    """中文路由统计响应"""
    total_chinese_requests: int = Field(..., description="总中文请求数")
    total_chinese_success: int = Field(..., description="总成功数")
    overall_chinese_success_rate: float = Field(..., description="总体成功率")
    provider_stats: Dict[str, Any] = Field(..., description="提供商统计")
    chinese_router_config: Dict[str, Any] = Field(..., description="路由器配置")
    timestamp: str = Field(..., description="统计时间戳")


@router.post("/analyze", 
            response_model=ChineseContentAnalysisResponse,
            summary="分析中文内容特征",
            description="分析中文内容的类型、复杂度、文化背景等特征")
async def analyze_chinese_content(
    request: ChineseContentAnalysisRequest,
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    分析中文内容特征
    
    - **content**: 待分析的中文内容
    
    返回详细的中文内容分析结果，包括：
    - 内容类型识别
    - 复杂度评估
    - 文化背景判断
    - 技术术语提取
    - 语言特征检测
    """
    try:
        logger.info(f"User {current_user.id} analyzing Chinese content (length: {len(request.content)})")
        
        analysis = await router_service.analyze_chinese_content(request.content)
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {analysis['error']}")
        
        return ChineseContentAnalysisResponse(**analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing Chinese content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ranking",
            response_model=List[ChineseProviderRankingResponse],
            summary="获取中文提供商排名",
            description="根据中文内容特征获取AI提供商的适配排名")
async def get_chinese_provider_ranking(
    request: ChineseContentAnalysisRequest,
    available_providers: Optional[List[str]] = Query(None, description="可用提供商列表"),
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    获取中文提供商排名
    
    - **content**: 中文内容
    - **available_providers**: 可用提供商列表（可选）
    
    返回按适配度排序的提供商列表
    """
    try:
        logger.info(f"User {current_user.id} getting Chinese provider ranking")
        
        rankings = await router_service.get_chinese_provider_ranking(
            request.content, available_providers
        )
        
        return [ChineseProviderRankingResponse(**ranking) for ranking in rankings]
        
    except Exception as e:
        logger.error(f"Error getting Chinese provider ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions",
            response_model=ChineseOptimizationSuggestionsResponse,
            summary="获取中文优化建议",
            description="获取针对中文内容的优化建议和策略")
async def get_chinese_optimization_suggestions(
    request: ChineseContentAnalysisRequest,
    provider: Optional[str] = Query(None, description="指定的AI提供商"),
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    获取中文优化建议
    
    - **content**: 中文内容
    - **provider**: 指定的AI提供商（可选，不指定则自动选择最佳）
    
    返回详细的优化建议，包括：
    - 内容分析结果
    - 提供商优化策略
    - 质量预期
    - 路由信息
    """
    try:
        logger.info(f"User {current_user.id} getting Chinese optimization suggestions")
        
        suggestions = await router_service.get_chinese_optimization_suggestions(
            request.content, provider
        )
        
        return ChineseOptimizationSuggestionsResponse(**suggestions)
        
    except Exception as e:
        logger.error(f"Error getting Chinese optimization suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route",
            response_model=ChineseRoutingResponse,
            summary="中文内容路由",
            description="为中文内容请求进行智能路由决策")
async def route_chinese_request(
    request: ChineseRoutingRequest,
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    中文内容路由
    
    - **content**: 中文内容
    - **user_id**: 用户ID
    - **routing_strategy**: 路由策略（可选）
    - **max_tokens**: 最大Token数（可选）
    - **temperature**: 温度参数（可选）
    - **priority**: 优先级（可选）
    
    返回路由决策结果
    """
    try:
        logger.info(f"User {current_user.id} routing Chinese request")
        
        # 验证用户权限
        if request.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # 转换路由策略
        strategy_mapping = {
            "accuracy_first": RoutingStrategy.ACCURACY_FIRST,
            "cost_first": RoutingStrategy.COST_FIRST,
            "speed_first": RoutingStrategy.SPEED_FIRST,
            "balanced": RoutingStrategy.BALANCED,
            "load_balanced": RoutingStrategy.LOAD_BALANCED
        }
        
        routing_strategy = strategy_mapping.get(request.routing_strategy, RoutingStrategy.BALANCED)
        
        # 创建AI请求对象
        ai_request = AIRequest(
            content=request.content,
            user_id=request.user_id,
            task_type=TaskType.CHINESE_CONTENT,
            routing_strategy=routing_strategy,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            priority=request.priority
        )
        
        # 执行中文路由
        decision = await router_service.route_chinese_request(ai_request)
        
        return ChineseRoutingResponse(
            selected_provider=decision.selected_provider.value,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            fallback_providers=[p.value for p in decision.fallback_providers],
            estimated_cost=decision.estimated_cost,
            estimated_time=decision.estimated_time,
            routing_strategy_used=decision.routing_strategy_used.value
        )
        
    except Exception as e:
        logger.error(f"Error routing Chinese request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics",
           response_model=ChineseRoutingStatisticsResponse,
           summary="获取中文路由统计",
           description="获取中文内容路由的统计信息")
async def get_chinese_routing_statistics(
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    获取中文路由统计
    
    返回中文路由的详细统计信息，包括：
    - 总请求数和成功率
    - 各提供商的表现统计
    - 路由器配置信息
    """
    try:
        logger.info(f"User {current_user.id} getting Chinese routing statistics")
        
        # 检查管理员权限
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin permission required")
        
        stats = await router_service.get_chinese_routing_statistics()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=f"Statistics error: {stats['error']}")
        
        return ChineseRoutingStatisticsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Chinese routing statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize",
            summary="优化中文路由配置",
            description="分析并优化中文路由配置")
async def optimize_chinese_routing_config(
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    优化中文路由配置
    
    分析当前中文路由性能并提供优化建议
    """
    try:
        logger.info(f"User {current_user.id} optimizing Chinese routing config")
        
        # 检查管理员权限
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin permission required")
        
        optimization_results = await router_service.optimize_chinese_routing_config()
        
        if "error" in optimization_results:
            raise HTTPException(
                status_code=500, 
                detail=f"Optimization error: {optimization_results['error']}"
            )
        
        return {
            "success": True,
            "message": "Chinese routing configuration optimized successfully",
            "results": optimization_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing Chinese routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health",
           summary="中文路由健康检查",
           description="检查中文路由功能的健康状态")
async def chinese_routing_health_check(
    current_user: User = Depends(get_current_user),
    router_service: AIRouterService = Depends(get_ai_router_service)
):
    """
    中文路由健康检查
    
    检查中文路由功能的各个组件是否正常工作
    """
    try:
        logger.info(f"User {current_user.id} performing Chinese routing health check")
        
        health_status = {
            "chinese_router_initialized": hasattr(router_service, 'chinese_router'),
            "chinese_providers_available": [],
            "analysis_functional": False,
            "routing_functional": False,
            "timestamp": None
        }
        
        # 检查中文路由器是否初始化
        if hasattr(router_service, 'chinese_router'):
            # 测试内容分析功能
            try:
                test_analysis = await router_service.analyze_chinese_content("测试内容")
                health_status["analysis_functional"] = test_analysis.get("is_chinese", False)
            except Exception as e:
                logger.warning(f"Chinese content analysis test failed: {e}")
            
            # 测试路由功能
            try:
                test_rankings = await router_service.get_chinese_provider_ranking("测试路由")
                health_status["routing_functional"] = len(test_rankings) > 0
            except Exception as e:
                logger.warning(f"Chinese routing test failed: {e}")
            
            # 检查中文优化提供商可用性
            chinese_providers = ["baidu_wenxin", "aliyun_tongyi", "zhipu_chatglm", "xunfei_xinghuo"]
            for provider_name in chinese_providers:
                try:
                    from ...services.ai_router_service import AIProvider
                    provider = AIProvider(provider_name)
                    health = router_service.provider_health.get(provider)
                    if health and health.is_available:
                        health_status["chinese_providers_available"].append(provider_name)
                except (ValueError, AttributeError):
                    continue
        
        health_status["timestamp"] = router_service.chinese_router.__class__.__name__ if hasattr(router_service, 'chinese_router') else None
        
        # 计算总体健康状态
        overall_healthy = (
            health_status["chinese_router_initialized"] and
            health_status["analysis_functional"] and
            health_status["routing_functional"] and
            len(health_status["chinese_providers_available"]) > 0
        )
        
        return {
            "healthy": overall_healthy,
            "status": health_status,
            "message": "Chinese routing is healthy" if overall_healthy else "Chinese routing has issues"
        }
        
    except Exception as e:
        logger.error(f"Error in Chinese routing health check: {e}")
        return {
            "healthy": False,
            "status": {"error": str(e)},
            "message": f"Health check failed: {str(e)}"
        }