"""
质量度量和评估API接口

本模块提供质量度量和评估相关的RESTful API接口
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.auth import get_current_user
from ...core.exceptions import ValidationError
from ...models.user import User
from ...services.quality_metrics_service import QualityMetricsService
from ...schemas.quality_metrics import (
    CalculateMetricsRequest, CalculateMetricsResponse,
    MonitorMetricsRequest, MonitorMetricsResponse,
    TrendAnalysisRequest, TrendAnalysisResponse,
    ImprovementSuggestionsRequest, ImprovementSuggestionsResponse,
    BaselineManagementRequest, BaselineManagementResponse,
    TargetManagementRequest, TargetManagementResponse,
    BenchmarkAnalysisRequest, BenchmarkAnalysisResponse,
    QualityReportRequest, QualityReportResponse,
    QualityDashboard, QualityHealthCheck
)
from ...utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality-metrics", tags=["质量度量"])

@router.post("/calculate", response_model=CalculateMetricsResponse)
async def calculate_quality_metrics(
    request: CalculateMetricsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """计算质量指标"""
    try:
        logger.info(f"用户{current_user.id}请求计算质量指标: 项目{request.project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 计算基础指标
        metrics = await service.calculate_quality_metrics(
            project_id=request.project_id,
            date_range=request.date_range
        )
        
        response = CalculateMetricsResponse(metrics=metrics)
        
        # 计算整体评分
        if metrics:
            # 简化的评分计算
            scores = []
            for metric_name, value in metrics.items():
                if metric_name in service.quality_metrics:
                    target = service.quality_metrics[metric_name]['target']
                    score = min(100, (value / target) * 100) if target > 0 else 50
                    scores.append(score)
            
            if scores:
                response.overall_score = sum(scores) / len(scores)
                
                # 评级
                if response.overall_score >= 90:
                    response.grade = "A"
                elif response.overall_score >= 80:
                    response.grade = "B"
                elif response.overall_score >= 70:
                    response.grade = "C"
                elif response.overall_score >= 60:
                    response.grade = "D"
                else:
                    response.grade = "F"
        
        # 如果需要趋势分析
        if request.include_trends:
            trends_data = await service.analyze_quality_trends(
                project_id=request.project_id,
                days=30
            )
            response.trends = trends_data.get('trends', {})
        
        # 如果需要预测
        if request.include_predictions:
            # 预测逻辑已在趋势分析中包含
            if hasattr(response, 'trends') and response.trends:
                response.predictions = trends_data.get('predictions', {})
        
        logger.info(f"质量指标计算完成: 项目{request.project_id}, 整体评分{response.overall_score}")
        return response
        
    except ValidationError as e:
        logger.error(f"计算质量指标验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"计算质量指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail="计算质量指标失败")

@router.post("/monitor", response_model=MonitorMetricsResponse)
async def monitor_quality_metrics(
    request: MonitorMetricsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """监控质量指标"""
    try:
        logger.info(f"用户{current_user.id}请求监控质量指标: 项目{request.project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 执行监控
        alerts = await service.monitor_quality_metrics(request.project_id)
        
        # 构建指标状态
        metrics_status = {}
        for alert in alerts:
            if alert.alert_level == "critical":
                metrics_status[alert.metric_name] = "critical"
            elif alert.alert_level == "warning":
                if alert.metric_name not in metrics_status:
                    metrics_status[alert.metric_name] = "warning"
            else:
                if alert.metric_name not in metrics_status:
                    metrics_status[alert.metric_name] = "ok"
        
        # 生成监控摘要
        critical_count = len([a for a in alerts if a.alert_level == "critical"])
        warning_count = len([a for a in alerts if a.alert_level == "warning"])
        
        if critical_count > 0:
            monitoring_summary = f"发现{critical_count}个严重问题，{warning_count}个警告"
        elif warning_count > 0:
            monitoring_summary = f"发现{warning_count}个警告，需要关注"
        else:
            monitoring_summary = "所有指标正常"
        
        # 设置下次检查时间
        next_check_time = datetime.utcnow() + timedelta(hours=1)
        
        response = MonitorMetricsResponse(
            alerts=alerts,
            metrics_status=metrics_status,
            monitoring_summary=monitoring_summary,
            next_check_time=next_check_time
        )
        
        # 如果启用通知，添加后台任务发送通知
        if request.notification_enabled and alerts:
            background_tasks.add_task(send_quality_alerts, alerts, current_user.id)
        
        logger.info(f"质量监控完成: 项目{request.project_id}, 告警数量{len(alerts)}")
        return response
        
    except ValidationError as e:
        logger.error(f"监控质量指标验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"监控质量指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail="监控质量指标失败")

@router.post("/trends/analyze", response_model=TrendAnalysisResponse)
async def analyze_quality_trends(
    request: TrendAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """分析质量趋势"""
    try:
        logger.info(f"用户{current_user.id}请求分析质量趋势: 项目{request.project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 执行趋势分析
        analysis_result = await service.analyze_quality_trends(
            project_id=request.project_id,
            days=request.analysis_period_days
        )
        
        response = TrendAnalysisResponse(
            trends=analysis_result.get('trends', {}),
            predictions=analysis_result.get('predictions', {}),
            anomalies=analysis_result.get('anomalies', []),
            insights=[]
        )
        
        # 生成洞察
        insights = []
        for metric_name, trend in response.trends.items():
            if hasattr(trend, 'trend_direction'):
                if trend.trend_direction == 'improving':
                    insights.append(f"{metric_name}呈改善趋势")
                elif trend.trend_direction == 'declining':
                    insights.append(f"{metric_name}呈下降趋势，需要关注")
                elif trend.trend_direction == 'volatile':
                    insights.append(f"{metric_name}波动较大，需要稳定")
        
        response.insights = insights
        
        logger.info(f"质量趋势分析完成: 项目{request.project_id}")
        return response
        
    except ValidationError as e:
        logger.error(f"分析质量趋势验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"分析质量趋势失败: {str(e)}")
        raise HTTPException(status_code=500, detail="分析质量趋势失败")

@router.post("/improvements/suggest", response_model=ImprovementSuggestionsResponse)
async def suggest_quality_improvements(
    request: ImprovementSuggestionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """生成质量改进建议"""
    try:
        logger.info(f"用户{current_user.id}请求生成改进建议: 项目{request.project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 生成改进建议
        suggestions = await service.generate_improvement_suggestions(request.project_id)
        
        # 按优先级过滤
        if request.priority_level and request.priority_level != "all":
            priority_threshold = {
                "high": 7.0,
                "medium": 5.0,
                "low": 3.0
            }.get(request.priority_level, 0.0)
            
            suggestions = [s for s in suggestions if s.get('priority_score', 0) >= priority_threshold]
        
        # 构建优先级矩阵
        priority_matrix = {
            "high": [s['title'] for s in suggestions if s.get('priority_score', 0) >= 7.0],
            "medium": [s['title'] for s in suggestions if 5.0 <= s.get('priority_score', 0) < 7.0],
            "low": [s['title'] for s in suggestions if s.get('priority_score', 0) < 5.0]
        }
        
        # 构建实施路线图
        implementation_roadmap = []
        for i, suggestion in enumerate(suggestions[:5]):  # 取前5个建议
            roadmap_item = {
                "phase": i + 1,
                "title": suggestion['title'],
                "timeline": suggestion.get('timeline', '1-2周'),
                "priority": "高" if suggestion.get('priority_score', 0) >= 7.0 else "中",
                "dependencies": []
            }
            implementation_roadmap.append(roadmap_item)
        
        # 估算影响
        estimated_impact = {}
        for suggestion in suggestions:
            category = suggestion.get('category', 'general')
            if category not in estimated_impact:
                estimated_impact[category] = 0.0
            estimated_impact[category] += suggestion.get('priority_score', 0) / 10.0
        
        response = ImprovementSuggestionsResponse(
            suggestions=suggestions,
            priority_matrix=priority_matrix,
            implementation_roadmap=implementation_roadmap,
            estimated_impact=estimated_impact
        )
        
        logger.info(f"改进建议生成完成: 项目{request.project_id}, 建议数量{len(suggestions)}")
        return response
        
    except ValidationError as e:
        logger.error(f"生成改进建议验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成改进建议失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成改进建议失败")

@router.post("/baselines/manage", response_model=BaselineManagementResponse)
async def manage_quality_baselines(
    request: BaselineManagementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """管理质量基线"""
    try:
        logger.info(f"用户{current_user.id}请求管理质量基线: 项目{request.project_id}, 操作{request.action}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 执行基线管理操作
        result = await service.manage_quality_baselines(
            project_id=request.project_id,
            action=request.action,
            baseline_data=request.baseline_data
        )
        
        response = BaselineManagementResponse(
            message=f"基线{request.action}操作完成",
            success=True
        )
        
        if request.action in ["create", "update", "get"]:
            response.baseline = result
        elif request.action == "compare":
            response.comparison = result
        
        logger.info(f"质量基线管理完成: 项目{request.project_id}, 操作{request.action}")
        return response
        
    except ValidationError as e:
        logger.error(f"管理质量基线验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"管理质量基线失败: {str(e)}")
        raise HTTPException(status_code=500, detail="管理质量基线失败")

@router.post("/targets/manage", response_model=TargetManagementResponse)
async def manage_quality_targets(
    request: TargetManagementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """管理质量目标"""
    try:
        logger.info(f"用户{current_user.id}请求管理质量目标: 项目{request.project_id}, 操作{request.action}")
        
        service = QualityMetricsService(db, redis_client)
        
        if request.action == "set":
            result = await service.set_quality_targets(
                project_id=request.project_id,
                targets=request.target_data.get('targets', {}) if request.target_data else {}
            )
            response = TargetManagementResponse(
                target=result,
                message="质量目标设置成功",
                success=True
            )
        elif request.action == "check_progress":
            # 检查目标达成进度
            current_metrics = await service.calculate_quality_metrics(request.project_id)
            # 这里需要获取目标数据进行对比
            progress = {}
            for metric_name, current_value in current_metrics.items():
                # 简化处理，实际应该从存储的目标中获取
                target_value = service.quality_metrics.get(metric_name, {}).get('target', 1.0)
                progress[metric_name] = {
                    'current': current_value,
                    'target': target_value,
                    'progress': min(100, (current_value / target_value) * 100) if target_value > 0 else 0,
                    'status': 'achieved' if current_value >= target_value else 'in_progress'
                }
            
            response = TargetManagementResponse(
                progress=progress,
                message="目标进度检查完成",
                success=True
            )
        else:
            response = TargetManagementResponse(
                message=f"不支持的操作: {request.action}",
                success=False
            )
        
        logger.info(f"质量目标管理完成: 项目{request.project_id}, 操作{request.action}")
        return response
        
    except ValidationError as e:
        logger.error(f"管理质量目标验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"管理质量目标失败: {str(e)}")
        raise HTTPException(status_code=500, detail="管理质量目标失败")

@router.post("/benchmarks/analyze", response_model=BenchmarkAnalysisResponse)
async def analyze_quality_benchmarks(
    request: BenchmarkAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """基准对比分析"""
    try:
        logger.info(f"用户{current_user.id}请求基准对比分析: 项目{request.project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 执行基准分析
        analysis = await service.benchmark_quality_metrics(request.project_id)
        
        response = BenchmarkAnalysisResponse(
            overall_score=analysis.overall_score,
            grade="A" if analysis.overall_score >= 90 else 
                  "B" if analysis.overall_score >= 80 else
                  "C" if analysis.overall_score >= 70 else
                  "D" if analysis.overall_score >= 60 else "F",
            benchmarks=analysis.benchmarks,
            strengths=analysis.strengths,
            improvement_areas=analysis.improvement_areas
        )
        
        # 生成差距分析
        if request.include_gap_analysis:
            gap_analysis = {}
            for benchmark in analysis.benchmarks:
                if benchmark.comparison_result in ["below_average", "needs_improvement"]:
                    gap = benchmark.best_practice - benchmark.current_value if benchmark.best_practice else 0
                    gap_analysis[benchmark.metric_name] = f"需要提升{gap:.2%}以达到最佳实践水平"
            response.gap_analysis = gap_analysis
        
        # 生成建议
        recommendations = []
        for area in analysis.improvement_areas:
            recommendations.append(f"重点改进{area}，提升整体质量水平")
        response.recommendations = recommendations
        
        logger.info(f"基准对比分析完成: 项目{request.project_id}, 整体评分{analysis.overall_score}")
        return response
        
    except ValidationError as e:
        logger.error(f"基准对比分析验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"基准对比分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="基准对比分析失败")

@router.get("/dashboard", response_model=QualityDashboard)
async def get_quality_dashboard(
    project_id: Optional[int] = Query(None, description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """获取质量仪表板数据"""
    try:
        logger.info(f"用户{current_user.id}请求质量仪表板: 项目{project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 获取当前指标
        current_metrics = await service.calculate_quality_metrics(project_id)
        
        # 获取趋势数据
        trends_data = await service.analyze_quality_trends(project_id, days=30)
        trends = trends_data.get('trends', {})
        
        # 获取告警
        alerts = await service.monitor_quality_metrics(project_id)
        
        # 获取改进建议
        improvements = await service.generate_improvement_suggestions(project_id)
        recent_improvements = improvements[:3]  # 取前3个建议
        
        # 生成关键洞察
        key_insights = []
        
        # 基于指标生成洞察
        if current_metrics.get('pass_rate', 0) < 0.8:
            key_insights.append("测试通过率偏低，需要关注代码质量")
        
        if current_metrics.get('test_coverage', 0) < 0.7:
            key_insights.append("测试覆盖率不足，建议增加测试用例")
        
        if current_metrics.get('defect_density', 0) > 0.3:
            key_insights.append("缺陷密度较高，建议加强质量控制")
        
        # 基于趋势生成洞察
        for metric_name, trend in trends.items():
            if hasattr(trend, 'trend_direction') and trend.trend_direction == 'improving':
                key_insights.append(f"{metric_name}呈改善趋势，继续保持")
        
        dashboard = QualityDashboard(
            project_id=project_id,
            current_metrics=current_metrics,
            trends=trends,
            alerts=alerts,
            recent_improvements=recent_improvements,
            key_insights=key_insights
        )
        
        logger.info(f"质量仪表板数据获取完成: 项目{project_id}")
        return dashboard
        
    except ValidationError as e:
        logger.error(f"获取质量仪表板验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取质量仪表板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取质量仪表板失败")

@router.get("/health-check", response_model=QualityHealthCheck)
async def quality_health_check(
    project_id: Optional[int] = Query(None, description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """质量健康检查"""
    try:
        logger.info(f"用户{current_user.id}请求质量健康检查: 项目{project_id}")
        
        service = QualityMetricsService(db, redis_client)
        
        # 获取当前指标
        current_metrics = await service.calculate_quality_metrics(project_id)
        
        # 获取告警
        alerts = await service.monitor_quality_metrics(project_id)
        
        # 计算健康评分
        health_score = 100.0
        issues = []
        
        # 检查各项指标
        for metric_name, value in current_metrics.items():
            if metric_name in service.quality_metrics:
                metric_config = service.quality_metrics[metric_name]
                warning_threshold = metric_config['threshold_warning']
                critical_threshold = metric_config['threshold_critical']
                is_higher_better = metric_config['is_higher_better']
                
                if is_higher_better:
                    if value < critical_threshold:
                        health_score -= 20
                        issues.append({
                            'type': 'critical',
                            'metric': metric_name,
                            'message': f"{metric_config['name']}严重偏低",
                            'impact': 'high'
                        })
                    elif value < warning_threshold:
                        health_score -= 10
                        issues.append({
                            'type': 'warning',
                            'metric': metric_name,
                            'message': f"{metric_config['name']}偏低",
                            'impact': 'medium'
                        })
                else:
                    if value > critical_threshold:
                        health_score -= 20
                        issues.append({
                            'type': 'critical',
                            'metric': metric_name,
                            'message': f"{metric_config['name']}严重偏高",
                            'impact': 'high'
                        })
                    elif value > warning_threshold:
                        health_score -= 10
                        issues.append({
                            'type': 'warning',
                            'metric': metric_name,
                            'message': f"{metric_config['name']}偏高",
                            'impact': 'medium'
                        })
        
        # 确定健康状态
        if health_score >= 90:
            overall_health = "excellent"
        elif health_score >= 80:
            overall_health = "good"
        elif health_score >= 70:
            overall_health = "fair"
        elif health_score >= 60:
            overall_health = "poor"
        else:
            overall_health = "critical"
        
        # 生成建议
        recommendations = []
        if issues:
            critical_issues = [i for i in issues if i['type'] == 'critical']
            if critical_issues:
                recommendations.append("立即处理严重质量问题")
            
            warning_issues = [i for i in issues if i['type'] == 'warning']
            if warning_issues:
                recommendations.append("关注并改进警告级别的质量问题")
        else:
            recommendations.append("质量状况良好，继续保持")
        
        # 设置下次检查时间
        next_check_time = datetime.utcnow() + timedelta(hours=24)
        
        health_check = QualityHealthCheck(
            project_id=project_id,
            overall_health=overall_health,
            health_score=max(0, health_score),
            issues=issues,
            recommendations=recommendations,
            next_check_time=next_check_time
        )
        
        logger.info(f"质量健康检查完成: 项目{project_id}, 健康评分{health_score}")
        return health_check
        
    except ValidationError as e:
        logger.error(f"质量健康检查验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"质量健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="质量健康检查失败")

# 辅助函数
async def send_quality_alerts(alerts: List, user_id: int):
    """发送质量告警通知（后台任务）"""
    try:
        # 这里应该实现实际的通知发送逻辑
        # 例如发送邮件、短信、企业微信等
        logger.info(f"发送质量告警通知: 用户{user_id}, 告警数量{len(alerts)}")
        
        for alert in alerts:
            # 模拟发送通知
            logger.info(f"发送告警通知: {alert.message}")
            
    except Exception as e:
        logger.error(f"发送质量告警通知失败: {str(e)}")