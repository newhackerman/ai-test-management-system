"""
需求AI分析API接口

提供需求智能分析的REST API接口，包括：
1. 需求质量分析接口
2. 需求优化建议接口
3. 需求冲突检测接口
4. 实时分析反馈接口
5. 分析结果可视化接口

集成到需求编辑流程中，提供实时的智能分析和建议。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.config import get_route_config
from ...services.auth import get_current_user
from ...services.openai_requirement_analysis_service import (
    get_openai_requirement_analysis_service,
    RequirementQualityAnalysis,
    RequirementConflictAnalysis
)
from ...services.requirement_optimization_service import (
    get_requirement_optimization_service,
    OptimizationReport
)
from ...models.user import User

logger = logging.getLogger(__name__)

# 获取路由配置
route_config = get_route_config("ai_assistant")
router = APIRouter(
    prefix=route_config["prefix"] + "/requirement-analysis",
    tags=["需求AI分析"]
)


# 请求模型
class RequirementAnalysisRequest(BaseModel):
    """需求分析请求"""
    title: str = Field(..., description="需求标题", max_length=200)
    description: str = Field(..., description="需求描述", max_length=10000)
    acceptance_criteria: Optional[str] = Field(None, description="验收标准", max_length=5000)
    requirement_type: Optional[str] = Field(None, description="需求类型")
    project_context: Optional[Dict[str, Any]] = Field(None, description="项目上下文")


class RequirementConflictRequest(BaseModel):
    """需求冲突检测请求"""
    current_requirement: Dict[str, Any] = Field(..., description="当前需求")
    existing_requirements: List[Dict[str, Any]] = Field(..., description="已存在的需求列表")


class RequirementOptimizationRequest(BaseModel):
    """需求优化请求"""
    title: str = Field(..., description="需求标题")
    description: str = Field(..., description="需求描述")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    requirement_type: Optional[str] = Field(None, description="需求类型")
    existing_requirements: Optional[List[Dict[str, Any]]] = Field(None, description="已存在的需求")
    project_context: Optional[Dict[str, Any]] = Field(None, description="项目上下文")


class RealTimeAnalysisRequest(BaseModel):
    """实时分析请求"""
    content: str = Field(..., description="需求内容", max_length=5000)
    analysis_type: str = Field(..., description="分析类型", pattern="^(quality|completeness|clarity)$")


# 响应模型
class QualityAnalysisResponse(BaseModel):
    """质量分析响应"""
    overall_score: float = Field(..., description="总体质量评分")
    completeness_score: float = Field(..., description="完整性评分")
    consistency_score: float = Field(..., description="一致性评分")
    clarity_score: float = Field(..., description="清晰度评分")
    testability_score: float = Field(..., description="可测试性评分")
    feasibility_score: float = Field(..., description="可行性评分")
    traceability_score: float = Field(..., description="可追溯性评分")
    complexity_estimate: str = Field(..., description="复杂度评估")
    effort_estimate: float = Field(..., description="工作量估算")
    improvement_suggestions: List[str] = Field(..., description="改进建议")
    risk_factors: List[str] = Field(..., description="风险因素")
    confidence_level: float = Field(..., description="分析置信度")
    analysis_time: float = Field(..., description="分析耗时")


class ConflictAnalysisResponse(BaseModel):
    """冲突分析响应"""
    has_conflicts: bool = Field(..., description="是否存在冲突")
    conflict_types: List[str] = Field(..., description="冲突类型")
    conflicting_requirements: List[Dict[str, Any]] = Field(..., description="冲突需求")
    resolution_suggestions: List[str] = Field(..., description="解决建议")
    severity_level: str = Field(..., description="严重程度")


class OptimizationResponse(BaseModel):
    """优化建议响应"""
    requirement_id: Optional[str] = Field(None, description="需求ID")
    overall_quality_score: float = Field(..., description="总体质量评分")
    improvement_potential: float = Field(..., description="改进潜力")
    improvements_count: int = Field(..., description="改进建议数量")
    conflicts_count: int = Field(..., description="冲突数量")
    dependencies_count: int = Field(..., description="依赖关系数量")
    best_practices_count: int = Field(..., description="最佳实践建议数量")
    analysis_time: float = Field(..., description="分析耗时")
    confidence_score: float = Field(..., description="置信度")


class RealTimeAnalysisResponse(BaseModel):
    """实时分析响应"""
    analysis_type: str = Field(..., description="分析类型")
    score: float = Field(..., description="评分")
    suggestions: List[str] = Field(..., description="建议")
    issues: List[str] = Field(..., description="问题")
    processing_time: float = Field(..., description="处理时间")


@router.post("/quality-analysis", response_model=QualityAnalysisResponse)
async def analyze_requirement_quality(
    request: RequirementAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分析需求质量
    
    对需求进行全面的质量分析，包括完整性、一致性、清晰度、
    可测试性、可行性、可追溯性等维度的评估。
    """
    try:
        logger.info(f"User {current_user.id} requested quality analysis for requirement: {request.title[:50]}")
        
        # 获取OpenAI需求分析服务
        analysis_service = await get_openai_requirement_analysis_service(db)
        
        # 执行质量分析
        analysis_result = await analysis_service.analyze_requirement_quality(
            title=request.title,
            description=request.description,
            acceptance_criteria=request.acceptance_criteria,
            requirement_type=request.requirement_type,
            user_id=current_user.id
        )
        
        # 构建响应
        response = QualityAnalysisResponse(
            overall_score=analysis_result.overall_score,
            completeness_score=analysis_result.completeness_score,
            consistency_score=analysis_result.consistency_score,
            clarity_score=analysis_result.clarity_score,
            testability_score=analysis_result.testability_score,
            feasibility_score=analysis_result.feasibility_score,
            traceability_score=analysis_result.traceability_score,
            complexity_estimate=analysis_result.complexity_estimate.value,
            effort_estimate=analysis_result.effort_estimate,
            improvement_suggestions=analysis_result.improvement_suggestions,
            risk_factors=analysis_result.risk_factors,
            confidence_level=analysis_result.confidence_level,
            analysis_time=analysis_result.analysis_time
        )
        
        logger.info(f"Quality analysis completed for user {current_user.id}, "
                   f"overall score: {analysis_result.overall_score:.1f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in quality analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"需求质量分析失败: {str(e)}"
        )


@router.post("/conflict-detection", response_model=ConflictAnalysisResponse)
async def detect_requirement_conflicts(
    request: RequirementConflictRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    检测需求冲突
    
    分析当前需求与已存在需求之间的潜在冲突，
    并提供解决建议。
    """
    try:
        logger.info(f"User {current_user.id} requested conflict detection")
        
        # 获取OpenAI需求分析服务
        analysis_service = await get_openai_requirement_analysis_service(db)
        
        # 执行冲突检测
        conflict_result = await analysis_service.detect_requirement_conflicts(
            current_requirement=request.current_requirement,
            existing_requirements=request.existing_requirements,
            user_id=current_user.id
        )
        
        # 构建响应
        response = ConflictAnalysisResponse(
            has_conflicts=conflict_result.has_conflicts,
            conflict_types=conflict_result.conflict_types,
            conflicting_requirements=conflict_result.conflicting_requirements,
            resolution_suggestions=conflict_result.resolution_suggestions,
            severity_level=conflict_result.severity_level
        )
        
        logger.info(f"Conflict detection completed for user {current_user.id}, "
                   f"conflicts found: {conflict_result.has_conflicts}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in conflict detection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"需求冲突检测失败: {str(e)}"
        )


@router.post("/optimization", response_model=OptimizationResponse)
async def generate_requirement_optimization(
    request: RequirementOptimizationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成需求优化建议
    
    基于需求内容生成综合的优化建议，包括改进建议、
    冲突解决、依赖识别、最佳实践等。
    """
    try:
        logger.info(f"User {current_user.id} requested optimization for requirement: {request.title[:50]}")
        
        # 获取需求优化服务
        optimization_service = await get_requirement_optimization_service(db)
        
        # 生成综合优化报告
        optimization_report = await optimization_service.generate_comprehensive_optimization(
            title=request.title,
            description=request.description,
            acceptance_criteria=request.acceptance_criteria,
            requirement_type=request.requirement_type,
            existing_requirements=request.existing_requirements,
            project_context=request.project_context,
            user_id=current_user.id
        )
        
        # 构建响应
        response = OptimizationResponse(
            requirement_id=optimization_report.requirement_id,
            overall_quality_score=optimization_report.overall_quality_score,
            improvement_potential=optimization_report.improvement_potential,
            improvements_count=len(optimization_report.improvements),
            conflicts_count=len(optimization_report.conflicts),
            dependencies_count=len(optimization_report.dependencies),
            best_practices_count=len(optimization_report.best_practices),
            analysis_time=optimization_report.analysis_time,
            confidence_score=optimization_report.confidence_score
        )
        
        # 在后台任务中保存详细报告（如果需要）
        background_tasks.add_task(
            _save_optimization_report,
            optimization_report,
            current_user.id
        )
        
        logger.info(f"Optimization completed for user {current_user.id}, "
                   f"generated {len(optimization_report.improvements)} improvements")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in requirement optimization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"需求优化分析失败: {str(e)}"
        )


@router.post("/real-time-analysis", response_model=RealTimeAnalysisResponse)
async def real_time_requirement_analysis(
    request: RealTimeAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    实时需求分析
    
    对用户输入的需求内容进行实时分析，
    提供即时的质量反馈和改进建议。
    """
    try:
        logger.info(f"User {current_user.id} requested real-time analysis: {request.analysis_type}")
        
        # 获取OpenAI需求分析服务
        analysis_service = await get_openai_requirement_analysis_service(db)
        
        start_time = datetime.utcnow()
        
        # 根据分析类型执行相应分析
        if request.analysis_type == "quality":
            # 快速质量分析
            result = await analysis_service.analyze_requirement_quality(
                title="实时分析",
                description=request.content,
                user_id=current_user.id
            )
            score = result.overall_score
            suggestions = result.improvement_suggestions[:3]  # 只返回前3个建议
            issues = result.risk_factors[:2]  # 只返回前2个风险
            
        elif request.analysis_type == "completeness":
            # 完整性分析
            result = await analysis_service.analyze_requirement_completeness(
                title="实时分析",
                description=request.content,
                user_id=current_user.id
            )
            score = result.get("completeness_score", 5.0)
            suggestions = result.get("improvement_suggestions", [])[:3]
            issues = result.get("missing_elements", [])[:2]
            
        elif request.analysis_type == "clarity":
            # 清晰度分析（简化版质量分析）
            result = await analysis_service.analyze_requirement_quality(
                title="实时分析",
                description=request.content,
                user_id=current_user.id
            )
            score = result.clarity_score
            suggestions = [s for s in result.improvement_suggestions if "清晰" in s or "明确" in s][:3]
            issues = [r for r in result.risk_factors if "理解" in r or "歧义" in r][:2]
            
        else:
            raise HTTPException(status_code=400, detail="不支持的分析类型")
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 构建响应
        response = RealTimeAnalysisResponse(
            analysis_type=request.analysis_type,
            score=score,
            suggestions=suggestions,
            issues=issues,
            processing_time=processing_time
        )
        
        logger.info(f"Real-time analysis completed for user {current_user.id}, "
                   f"type: {request.analysis_type}, score: {score:.1f}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in real-time analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"实时分析失败: {str(e)}"
        )


@router.get("/optimization-report/{requirement_id}")
async def get_optimization_report(
    requirement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取详细的优化报告
    
    返回指定需求的完整优化分析报告，
    包括所有改进建议、冲突解决方案等详细信息。
    """
    try:
        logger.info(f"User {current_user.id} requested optimization report for requirement: {requirement_id}")
        
        # 这里应该从数据库或缓存中获取保存的报告
        # 为了演示，返回一个示例响应
        
        return JSONResponse(content={
            "requirement_id": requirement_id,
            "message": "详细优化报告功能正在开发中",
            "status": "coming_soon"
        })
        
    except Exception as e:
        logger.error(f"Error getting optimization report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取优化报告失败: {str(e)}"
        )


@router.get("/analysis-history")
async def get_analysis_history(
    limit: int = Query(10, ge=1, le=100, description="返回记录数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取分析历史记录
    
    返回用户的需求分析历史记录，
    包括分析时间、类型、结果等信息。
    """
    try:
        logger.info(f"User {current_user.id} requested analysis history")
        
        # 这里应该从数据库中查询用户的分析历史
        # 为了演示，返回一个示例响应
        
        return JSONResponse(content={
            "total": 0,
            "items": [],
            "message": "分析历史记录功能正在开发中",
            "status": "coming_soon"
        })
        
    except Exception as e:
        logger.error(f"Error getting analysis history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取分析历史失败: {str(e)}"
        )


@router.get("/service-status")
async def get_service_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取AI分析服务状态
    
    返回AI分析服务的运行状态、性能指标等信息。
    """
    try:
        logger.info(f"User {current_user.id} requested service status")
        
        # 获取服务实例
        analysis_service = await get_openai_requirement_analysis_service(db)
        optimization_service = await get_requirement_optimization_service(db)
        
        # 获取服务指标
        analysis_metrics = await analysis_service.get_service_metrics()
        optimization_metrics = await optimization_service.get_service_metrics()
        
        return JSONResponse(content={
            "analysis_service": {
                "status": "healthy" if analysis_metrics["is_initialized"] else "unhealthy",
                "version": analysis_metrics["service_version"],
                "openai_available": analysis_metrics["openai_available"],
                "total_analyses": analysis_metrics["total_analyses"],
                "success_rate": (
                    analysis_metrics["successful_analyses"] / analysis_metrics["total_analyses"]
                    if analysis_metrics["total_analyses"] > 0 else 0
                ),
                "avg_analysis_time": analysis_metrics["avg_analysis_time"]
            },
            "optimization_service": {
                "status": "healthy" if optimization_metrics["is_initialized"] else "unhealthy",
                "version": optimization_metrics["service_version"],
                "total_optimizations": optimization_metrics["total_optimizations"],
                "success_rate": (
                    optimization_metrics["successful_optimizations"] / optimization_metrics["total_optimizations"]
                    if optimization_metrics["total_optimizations"] > 0 else 0
                ),
                "avg_optimization_time": optimization_metrics["avg_optimization_time"]
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取服务状态失败: {str(e)}"
        )


async def _save_optimization_report(report: OptimizationReport, user_id: int):
    """
    保存优化报告（后台任务）
    
    Args:
        report: 优化报告
        user_id: 用户ID
    """
    try:
        # 这里应该将报告保存到数据库或缓存中
        # 为了演示，只记录日志
        logger.info(f"Saving optimization report for user {user_id}, "
                   f"requirement: {report.requirement_id}")
        
        # 实际实现中可以保存到数据库表中
        # await save_report_to_database(report, user_id)
        
    except Exception as e:
        logger.error(f"Error saving optimization report: {str(e)}")


# 导出路由器
__all__ = ["router"]