"""
AI建议相关API端点

提供以下功能：
1. 生成智能建议
2. 需求质量分析
3. 测试建议生成
4. 优化建议生成
5. 建议管理（CRUD操作）
6. 建议统计和分析
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.auth import get_current_user
from ...models.user import User
from ...models.ai_suggestion import AISuggestion, SuggestionStatus, SuggestionType, SuggestionPriority
from ...services.suggestion_engine import SuggestionEngine, ProjectContext
from ...schemas.suggestion import (
    GenerateSuggestionsRequestSchema,
    GenerateSuggestionsResponseSchema,
    RequirementsAnalysisRequestSchema,
    RequirementsAnalysisResponseSchema,
    TestSuggestionsRequestSchema,
    TestSuggestionsResponseSchema,
    OptimizationSuggestionsRequestSchema,
    OptimizationSuggestionsResponseSchema,
    SuggestionCreateSchema,
    SuggestionUpdateSchema,
    SuggestionResponseSchema,
    SuggestionListResponseSchema,
    SuggestionStatsSchema,
    SuggestionFilterSchema,
    BulkSuggestionUpdateSchema,
    ProjectStatusAnalysisResponseSchema,
    DetailedClarityAnalysisResponseSchema
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=GenerateSuggestionsResponseSchema)
async def generate_suggestions(
    request: GenerateSuggestionsRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    生成智能建议
    
    基于项目上下文生成各类智能建议，包括：
    - 需求质量改进建议
    - 测试覆盖度建议
    - 项目管理建议
    - 质量优化建议
    """
    try:
        start_time = datetime.utcnow()
        
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 构建项目上下文
        context = ProjectContext(
            project_id=request.context.project_id,
            project_name=request.context.project_name,
            project_type=request.context.project_type,
            team_size=request.context.team_size,
            timeline=request.context.timeline,
            requirements=request.context.requirements,
            test_data=request.context.test_data,
            quality_metrics=request.context.quality_metrics
        )
        
        # 生成建议
        suggestions = await suggestion_engine.generate_project_suggestions(context)
        
        # 过滤建议类型
        if request.suggestion_types:
            type_values = [t.value for t in request.suggestion_types]
            suggestions = [s for s in suggestions if s.get("type") in type_values]
        
        # 过滤低优先级建议
        if not request.include_low_priority:
            suggestions = [s for s in suggestions if s.get("priority") != "LOW"]
        
        # 限制建议数量
        suggestions = suggestions[:request.max_suggestions]
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 生成分析摘要
        analysis_summary = {
            "total_requirements": len(request.context.requirements or []),
            "total_tests": len(request.context.test_data.get("test_cases", []) if request.context.test_data else []),
            "project_type": request.context.project_type,
            "team_size": request.context.team_size
        }
        
        # 生成元数据
        generation_metadata = {
            "user_id": current_user.id,
            "generation_time": datetime.utcnow().isoformat(),
            "engine_version": "1.0.0",
            "context_hash": hash(str(request.context.dict()))
        }
        
        logger.info(f"Generated {len(suggestions)} suggestions for user {current_user.id} in {processing_time:.2f}s")
        
        return GenerateSuggestionsResponseSchema(
            suggestions=suggestions,
            analysis_summary=analysis_summary,
            generation_metadata=generation_metadata,
            total_generated=len(suggestions),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成建议失败: {str(e)}")


@router.post("/analyze-requirements", response_model=RequirementsAnalysisResponseSchema)
async def analyze_requirements(
    request: RequirementsAnalysisRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    分析需求质量
    
    对提供的需求进行全面的质量分析，包括：
    - 完整性评估
    - 清晰度分析
    - 一致性检查
    - 可测试性评估
    - 问题需求识别
    """
    try:
        start_time = datetime.utcnow()
        
        if not request.requirements:
            raise HTTPException(status_code=400, detail="需求列表不能为空")
        
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 构建需求数据
        from ...services.suggestion_engine import RequirementsData
        requirements_data = RequirementsData(
            requirements=request.requirements,
            total_count=len(request.requirements),
            categories=[req.get("category", "未分类") for req in request.requirements],
            priorities=[req.get("priority", "MEDIUM") for req in request.requirements]
        )
        
        # 执行需求质量分析
        quality_analysis = await suggestion_engine._analyze_requirements_quality(requirements_data)
        
        # 生成改进建议
        suggestions = await suggestion_engine._generate_requirements_quality_suggestions(quality_analysis)
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 生成分析元数据
        analysis_metadata = {
            "user_id": current_user.id,
            "analysis_time": datetime.utcnow().isoformat(),
            "requirements_count": len(request.requirements),
            "analysis_options": request.analysis_options,
            "include_ai_analysis": request.include_ai_analysis
        }
        
        logger.info(f"Analyzed {len(request.requirements)} requirements for user {current_user.id}")
        
        return RequirementsAnalysisResponseSchema(
            quality_analysis={
                "completeness_score": quality_analysis.completeness_score,
                "clarity_score": quality_analysis.clarity_score,
                "consistency_score": quality_analysis.consistency_score,
                "testability_score": quality_analysis.testability_score,
                "overall_score": quality_analysis.overall_score,
                "problematic_requirements": quality_analysis.problematic_requirements
            },
            suggestions=suggestions,
            problematic_requirements=quality_analysis.problematic_requirements,
            analysis_metadata=analysis_metadata,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing requirements: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"需求分析失败: {str(e)}")


@router.post("/analyze-requirements-clarity", response_model=DetailedClarityAnalysisResponseSchema)
async def analyze_requirements_clarity_detailed(
    request: RequirementsAnalysisRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    详细需求清晰度分析
    
    提供增强的需求清晰度分析功能，包括：
    - 多维度清晰度评估（语言表达、结构完整性、量化指标、术语一致性、AI语义分析）
    - 单个需求的详细分析报告
    - 清晰度分布统计
    - 针对性的改进建议
    - 全局术语一致性分析
    """
    try:
        start_time = datetime.utcnow()
        
        if not request.requirements:
            raise HTTPException(status_code=400, detail="需求列表不能为空")
        
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 构建需求数据
        from ...services.suggestion_engine import RequirementsData
        requirements_data = RequirementsData(
            requirements=request.requirements,
            total_count=len(request.requirements),
            categories=[req.get("category", "未分类") for req in request.requirements],
            priorities=[req.get("priority", "MEDIUM") for req in request.requirements]
        )
        
        # 执行详细清晰度分析
        detailed_analysis = await suggestion_engine.generate_detailed_clarity_analysis(requirements_data)
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 添加处理时间到结果中
        detailed_analysis["processing_time"] = processing_time
        
        # 生成分析元数据
        detailed_analysis["analysis_metadata"].update({
            "user_id": current_user.id,
            "analysis_type": "detailed_clarity_analysis",
            "requirements_count": len(request.requirements),
            "include_ai_analysis": request.include_ai_analysis
        })
        
        logger.info(f"Completed detailed clarity analysis for {len(request.requirements)} requirements "
                   f"for user {current_user.id} in {processing_time:.2f}s. "
                   f"Overall score: {detailed_analysis.get('overall_clarity_score', 0):.3f}")
        
        return detailed_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in detailed requirements clarity analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"详细需求清晰度分析失败: {str(e)}")


@router.post("/generate-test-suggestions", response_model=TestSuggestionsResponseSchema)
async def generate_test_suggestions(
    request: TestSuggestionsRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    生成测试建议
    
    基于现有测试用例和需求，生成测试改进建议：
    - 识别测试覆盖率缺口
    - 生成缺失的测试用例建议
    - 提供测试策略建议
    """
    try:
        start_time = datetime.utcnow()
        
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 构建测试上下文
        from ...services.suggestion_engine import TestContext
        test_context = TestContext(
            existing_tests=request.existing_tests,
            requirements=request.requirements,
            coverage_data=request.coverage_data
        )
        
        # 生成测试建议
        suggestions = await suggestion_engine.generate_test_suggestions(test_context)
        
        # 限制建议数量
        suggestions = suggestions[:request.max_suggestions]
        
        # 分析覆盖率缺口
        coverage_gaps = await suggestion_engine._analyze_coverage_gaps(
            request.existing_tests, 
            request.requirements
        )
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 生成分析摘要
        analysis_summary = {
            "total_tests": len(request.existing_tests),
            "total_requirements": len(request.requirements),
            "coverage_gaps_count": len(coverage_gaps),
            "suggestions_generated": len(suggestions)
        }
        
        logger.info(f"Generated {len(suggestions)} test suggestions for user {current_user.id}")
        
        return TestSuggestionsResponseSchema(
            suggestions=[
                {
                    "title": s.title,
                    "description": s.description,
                    "test_steps": s.test_steps,
                    "expected_result": s.expected_result,
                    "priority": s.priority,
                    "rationale": s.rationale
                } for s in suggestions
            ],
            coverage_gaps=[
                {
                    "requirement_id": gap.requirement_id,
                    "requirement_description": gap.requirement_description,
                    "missing_scenarios": gap.missing_scenarios,
                    "existing_tests": gap.existing_tests
                } for gap in coverage_gaps
            ],
            analysis_summary=analysis_summary,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating test suggestions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成测试建议失败: {str(e)}")


@router.post("/analyze-project-status", response_model=ProjectStatusAnalysisResponseSchema)
async def analyze_project_status(
    request: GenerateSuggestionsRequestSchema,  # 复用现有的请求模式
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    项目状况分析API
    
    这是AI助手模块的核心分析功能，提供全面的项目健康度评估。
    分析维度包括：
    1. 项目健康度评估 - 基于进度、质量、资源等多维度指标
    2. 团队能力分析 - 评估团队规模、技能匹配度、工作负载
    3. 进度状态分析 - 分析项目时间线、里程碑完成情况
    4. 质量风险评估 - 基于需求质量、测试覆盖率等指标
    5. 资源配置分析 - 评估人力、时间、预算资源配置合理性
    
    返回详细的分析报告和改进建议。
    """
    try:
        start_time = datetime.utcnow()
        logger.info(f"Starting project status analysis for user {current_user.id}")
        
        # 创建建议引擎实例
        suggestion_engine = SuggestionEngine(db)
        
        # 构建项目上下文
        context = ProjectContext(
            project_id=request.context.project_id,
            project_name=request.context.project_name,
            project_type=request.context.project_type or "web_application",
            team_size=request.context.team_size,
            timeline=request.context.timeline,
            requirements=request.context.requirements,
            test_data=request.context.test_data,
            quality_metrics=request.context.quality_metrics
        )
        
        # 执行项目状况分析
        analysis_result = await suggestion_engine.analyze_project_status(context)
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 构建响应
        response = {
            "analysis_result": analysis_result,
            "processing_time": processing_time,
            "analysis_metadata": {
                "user_id": current_user.id,
                "analysis_timestamp": start_time.isoformat(),
                "context_summary": {
                    "project_id": context.project_id,
                    "project_name": context.project_name,
                    "project_type": context.project_type,
                    "team_size": context.team_size,
                    "has_timeline": bool(context.timeline),
                    "requirements_count": len(context.requirements) if context.requirements else 0,
                    "has_test_data": bool(context.test_data),
                    "has_quality_metrics": bool(context.quality_metrics)
                }
            }
        }
        
        logger.info(f"Project status analysis completed in {processing_time:.2f}s. "
                   f"Overall health score: {analysis_result.get('overall_health_score', 0):.2f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in project status analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"项目状况分析失败: {str(e)}"
        )


@router.post("/generate-optimization-suggestions", response_model=OptimizationSuggestionsResponseSchema)
async def generate_optimization_suggestions(
    request: OptimizationSuggestionsRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    生成优化建议
    
    基于性能指标和资源使用情况，生成系统优化建议：
    - 性能瓶颈识别
    - 资源优化建议
    - 架构改进建议
    """
    try:
        start_time = datetime.utcnow()
        
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 构建优化上下文
        from ...services.suggestion_engine import OptimizationContext
        optimization_context = OptimizationContext(
            performance_metrics=request.performance_metrics,
            resource_usage=request.resource_usage,
            bottlenecks=request.bottlenecks
        )
        
        # 生成优化建议
        suggestions = await suggestion_engine.generate_optimization_suggestions(optimization_context)
        
        # 识别性能瓶颈
        identified_bottlenecks = await suggestion_engine._identify_performance_bottlenecks(
            request.performance_metrics
        )
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 生成性能分析
        performance_analysis = {
            "avg_response_time": request.performance_metrics.get("avg_response_time", 0),
            "memory_usage": request.performance_metrics.get("memory_usage", 0),
            "cpu_usage": request.performance_metrics.get("cpu_usage", 0),
            "bottlenecks_identified": len(identified_bottlenecks),
            "optimization_opportunities": len(suggestions)
        }
        
        logger.info(f"Generated {len(suggestions)} optimization suggestions for user {current_user.id}")
        
        return OptimizationSuggestionsResponseSchema(
            suggestions=[
                {
                    "title": s.title,
                    "description": s.description,
                    "optimization_type": s.optimization_type,
                    "expected_improvement": s.expected_improvement,
                    "implementation_steps": s.implementation_steps,
                    "priority": s.priority
                } for s in suggestions
            ],
            identified_bottlenecks=identified_bottlenecks,
            performance_analysis=performance_analysis,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating optimization suggestions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成优化建议失败: {str(e)}")


@router.post("/", response_model=SuggestionResponseSchema)
async def create_suggestion(
    suggestion_data: SuggestionCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    创建建议
    
    手动创建一个新的建议记录
    """
    try:
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 保存建议
        suggestion = await suggestion_engine.save_suggestion(
            suggestion_data=suggestion_data.dict(),
            user_id=current_user.id,
            session_id=suggestion_data.session_id
        )
        
        if not suggestion:
            raise HTTPException(status_code=500, detail="创建建议失败")
        
        logger.info(f"Created suggestion {suggestion.id} for user {current_user.id}")
        
        return SuggestionResponseSchema.from_orm(suggestion)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating suggestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建建议失败: {str(e)}")


@router.get("/", response_model=SuggestionListResponseSchema)
async def get_suggestions(
    status: Optional[str] = Query(None, description="建议状态过滤"),
    type: Optional[str] = Query(None, description="建议类型过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取建议列表
    
    获取当前用户的建议列表，支持分页和过滤
    """
    try:
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 计算偏移量
        offset = (page - 1) * size
        
        # 获取建议列表
        suggestions = await suggestion_engine.get_user_suggestions(
            user_id=current_user.id,
            status=status,
            limit=size,
            offset=offset
        )
        
        # 获取总数（简化实现，实际应该单独查询）
        total = len(suggestions) + offset if len(suggestions) == size else len(suggestions) + offset
        has_more = len(suggestions) == size
        
        logger.info(f"Retrieved {len(suggestions)} suggestions for user {current_user.id}")
        
        return SuggestionListResponseSchema(
            suggestions=[SuggestionResponseSchema.from_orm(s) for s in suggestions],
            total=total,
            page=page,
            size=size,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取建议列表失败: {str(e)}")


@router.get("/{suggestion_id}", response_model=SuggestionResponseSchema)
async def get_suggestion(
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取单个建议详情
    """
    try:
        from sqlalchemy import select
        
        # 查询建议
        query = select(AISuggestion).where(
            AISuggestion.id == suggestion_id,
            AISuggestion.user_id == current_user.id
        )
        result = await db.execute(query)
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="建议不存在")
        
        return SuggestionResponseSchema.from_orm(suggestion)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestion {suggestion_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取建议详情失败: {str(e)}")


@router.put("/{suggestion_id}", response_model=SuggestionResponseSchema)
async def update_suggestion(
    suggestion_id: int,
    update_data: SuggestionUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新建议
    
    更新建议的状态、评分、反馈等信息
    """
    try:
        from sqlalchemy import select
        
        # 查询建议
        query = select(AISuggestion).where(
            AISuggestion.id == suggestion_id,
            AISuggestion.user_id == current_user.id
        )
        result = await db.execute(query)
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="建议不存在")
        
        # 更新字段
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(suggestion, field):
                setattr(suggestion, field, value)
        
        # 如果状态更新为已实施，记录实施时间
        if update_data.status == SuggestionStatus.IMPLEMENTED:
            suggestion.implemented_at = datetime.utcnow()
            suggestion.implemented_by = current_user.id
        
        await db.commit()
        await db.refresh(suggestion)
        
        logger.info(f"Updated suggestion {suggestion_id} for user {current_user.id}")
        
        return SuggestionResponseSchema.from_orm(suggestion)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating suggestion {suggestion_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新建议失败: {str(e)}")


@router.delete("/{suggestion_id}")
async def delete_suggestion(
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    删除建议
    """
    try:
        from sqlalchemy import select
        
        # 查询建议
        query = select(AISuggestion).where(
            AISuggestion.id == suggestion_id,
            AISuggestion.user_id == current_user.id
        )
        result = await db.execute(query)
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="建议不存在")
        
        # 软删除
        suggestion.status = SuggestionStatus.CANCELLED
        await db.commit()
        
        logger.info(f"Deleted suggestion {suggestion_id} for user {current_user.id}")
        
        return {"message": "建议已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting suggestion {suggestion_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除建议失败: {str(e)}")


@router.post("/bulk-update")
async def bulk_update_suggestions(
    update_request: BulkSuggestionUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    批量更新建议
    """
    try:
        from sqlalchemy import select, update
        
        if not update_request.suggestion_ids:
            raise HTTPException(status_code=400, detail="建议ID列表不能为空")
        
        # 验证建议所有权
        query = select(AISuggestion.id).where(
            AISuggestion.id.in_(update_request.suggestion_ids),
            AISuggestion.user_id == current_user.id
        )
        result = await db.execute(query)
        valid_ids = [row[0] for row in result.fetchall()]
        
        if len(valid_ids) != len(update_request.suggestion_ids):
            invalid_ids = set(update_request.suggestion_ids) - set(valid_ids)
            raise HTTPException(
                status_code=403, 
                detail=f"无权限操作建议: {list(invalid_ids)}"
            )
        
        # 批量更新
        update_dict = update_request.updates.dict(exclude_unset=True)
        if update_dict:
            update_stmt = update(AISuggestion).where(
                AISuggestion.id.in_(valid_ids)
            ).values(**update_dict)
            
            await db.execute(update_stmt)
            await db.commit()
        
        logger.info(f"Bulk updated {len(valid_ids)} suggestions for user {current_user.id}")
        
        return {
            "message": f"成功更新 {len(valid_ids)} 个建议",
            "updated_ids": valid_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk updating suggestions: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新建议失败: {str(e)}")


@router.get("/stats/summary", response_model=SuggestionStatsSchema)
async def get_suggestion_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取建议统计信息
    """
    try:
        from sqlalchemy import select, func
        
        # 基础统计查询
        base_query = select(AISuggestion).where(AISuggestion.user_id == current_user.id)
        
        # 总数统计
        total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
        total_suggestions = total_result.scalar()
        
        # 按状态统计
        status_query = select(
            AISuggestion.status,
            func.count(AISuggestion.id)
        ).where(
            AISuggestion.user_id == current_user.id
        ).group_by(AISuggestion.status)
        
        status_result = await db.execute(status_query)
        by_status = {row[0].value: row[1] for row in status_result.fetchall()}
        
        # 按类型统计
        type_query = select(
            AISuggestion.type,
            func.count(AISuggestion.id)
        ).where(
            AISuggestion.user_id == current_user.id
        ).group_by(AISuggestion.type)
        
        type_result = await db.execute(type_query)
        by_type = {row[0].value: row[1] for row in type_result.fetchall()}
        
        # 按优先级统计
        priority_query = select(
            AISuggestion.priority,
            func.count(AISuggestion.id)
        ).where(
            AISuggestion.user_id == current_user.id
        ).group_by(AISuggestion.priority)
        
        priority_result = await db.execute(priority_query)
        by_priority = {row[0].value: row[1] for row in priority_result.fetchall()}
        
        # 平均评分
        rating_query = select(func.avg(AISuggestion.user_rating)).where(
            AISuggestion.user_id == current_user.id,
            AISuggestion.user_rating.isnot(None)
        )
        rating_result = await db.execute(rating_query)
        avg_rating = rating_result.scalar()
        
        # 实施率
        implemented_count = by_status.get(SuggestionStatus.IMPLEMENTED.value, 0)
        implementation_rate = implemented_count / total_suggestions if total_suggestions > 0 else 0.0
        
        # 最近建议数量（最近7天）
        from datetime import timedelta
        recent_date = datetime.utcnow() - timedelta(days=7)
        recent_query = select(func.count()).where(
            AISuggestion.user_id == current_user.id,
            AISuggestion.created_at >= recent_date
        )
        recent_result = await db.execute(recent_query)
        recent_suggestions = recent_result.scalar()
        
        return SuggestionStatsSchema(
            total_suggestions=total_suggestions,
            by_status=by_status,
            by_type=by_type,
            by_priority=by_priority,
            avg_rating=float(avg_rating) if avg_rating else None,
            implementation_rate=implementation_rate,
            recent_suggestions=recent_suggestions
        )
        
    except Exception as e:
        logger.error(f"Error getting suggestion stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取建议统计失败: {str(e)}")


@router.post("/{suggestion_id}/accept")
async def accept_suggestion(
    suggestion_id: int,
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    接受建议
    """
    try:
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 更新建议状态
        success = await suggestion_engine.update_suggestion_status(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.ACCEPTED.value,
            user_feedback=feedback
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="建议不存在或无权限操作")
        
        logger.info(f"User {current_user.id} accepted suggestion {suggestion_id}")
        
        return {"message": "建议已接受"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting suggestion {suggestion_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"接受建议失败: {str(e)}")


@router.post("/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: int,
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    拒绝建议
    """
    try:
        # 初始化建议引擎
        suggestion_engine = SuggestionEngine(db)
        
        # 更新建议状态
        success = await suggestion_engine.update_suggestion_status(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.REJECTED.value,
            user_feedback=feedback
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="建议不存在或无权限操作")
        
        logger.info(f"User {current_user.id} rejected suggestion {suggestion_id}")
        
        return {"message": "建议已拒绝"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting suggestion {suggestion_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"拒绝建议失败: {str(e)}")


@router.post("/{suggestion_id}/implement")
async def implement_suggestion(
    suggestion_id: int,
    implementation_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    标记建议为已实施
    """
    try:
        from sqlalchemy import select
        
        # 查询建议
        query = select(AISuggestion).where(
            AISuggestion.id == suggestion_id,
            AISuggestion.user_id == current_user.id
        )
        result = await db.execute(query)
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="建议不存在")
        
        # 更新状态
        suggestion.status = SuggestionStatus.IMPLEMENTED
        suggestion.implemented_at = datetime.utcnow()
        suggestion.implemented_by = current_user.id
        if implementation_notes:
            suggestion.implementation_notes = implementation_notes
        
        await db.commit()
        
        logger.info(f"User {current_user.id} implemented suggestion {suggestion_id}")
        
        return {"message": "建议已标记为实施"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error implementing suggestion {suggestion_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"实施建议失败: {str(e)}")