"""
需求报告生成服务

本模块实现需求管理的报告生成功能，包括：
- 自动报告生成器
- 多格式导出功能
- 定制化报告模板
- 报告数据聚合和分析
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from enum import Enum
import io
import base64

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError
from ..models.requirement import (
    Requirement, RequirementStatus, RequirementType, Priority, BusinessValue, Complexity,
    RequirementStatusHistory, RequirementDependency, RequirementReview, RequirementChangeRequest
)
from ..models.project import Project
from ..models.user import User
from .requirement_analytics_service import RequirementAnalyticsService, RequirementMetrics, RequirementQualityAssessment

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """报告格式枚举"""
    PDF = "PDF"
    EXCEL = "EXCEL"
    WORD = "WORD"
    HTML = "HTML"
    JSON = "JSON"
    CSV = "CSV"


class ReportType(Enum):
    """报告类型枚举"""
    SUMMARY = "SUMMARY"                    # 需求概要报告
    DETAILED = "DETAILED"                  # 详细需求报告
    METRICS = "METRICS"                    # 指标分析报告
    QUALITY = "QUALITY"                    # 质量评估报告
    PROGRESS = "PROGRESS"                  # 进度跟踪报告
    CHANGE_ANALYSIS = "CHANGE_ANALYSIS"    # 变更分析报告
    TRACEABILITY = "TRACEABILITY"          # 追溯性报告
    CUSTOM = "CUSTOM"                      # 自定义报告


@dataclass
class ReportTemplate:
    """报告模板"""
    id: str
    name: str
    description: str
    report_type: ReportType
    template_config: Dict[str, Any]
    sections: List[Dict[str, Any]]
    filters: Dict[str, Any]
    formatting: Dict[str, Any]
    created_by: int
    created_at: datetime
    updated_at: datetime


@dataclass
class ReportRequest:
    """报告请求"""
    report_type: ReportType
    format: ReportFormat
    project_id: Optional[int] = None
    template_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    custom_sections: Optional[List[str]] = None
    date_range: Optional[Dict[str, date]] = None
    include_charts: bool = True
    include_raw_data: bool = False
    requested_by: int = None


@dataclass
class ReportData:
    """报告数据"""
    title: str
    subtitle: str
    generated_at: datetime
    generated_by: int
    project_info: Optional[Dict[str, Any]]
    summary: Dict[str, Any]
    sections: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]
    raw_data: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class GeneratedReport:
    """生成的报告"""
    id: str
    request: ReportRequest
    data: ReportData
    content: bytes
    format: ReportFormat
    file_name: str
    file_size: int
    generated_at: datetime
    expires_at: Optional[datetime]


class RequirementReportService:
    """需求报告生成服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = RequirementAnalyticsService(db)
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, ReportTemplate]:
        """加载默认报告模板"""
        templates = {}
        
        # 需求概要报告模板
        templates['summary'] = ReportTemplate(
            id='summary',
            name='需求概要报告',
            description='项目需求的高级概要和关键指标',
            report_type=ReportType.SUMMARY,
            template_config={
                'include_charts': True,
                'include_metrics': True,
                'include_status_breakdown': True
            },
            sections=[
                {'id': 'overview', 'name': '项目概览', 'required': True},
                {'id': 'metrics', 'name': '关键指标', 'required': True},
                {'id': 'status_distribution', 'name': '状态分布', 'required': True},
                {'id': 'priority_analysis', 'name': '优先级分析', 'required': False},
                {'id': 'recommendations', 'name': '建议', 'required': False}
            ],
            filters={},
            formatting={
                'page_size': 'A4',
                'orientation': 'portrait',
                'font_family': 'Arial',
                'font_size': 12
            },
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 详细需求报告模板
        templates['detailed'] = ReportTemplate(
            id='detailed',
            name='详细需求报告',
            description='包含所有需求详细信息的完整报告',
            report_type=ReportType.DETAILED,
            template_config={
                'include_full_descriptions': True,
                'include_acceptance_criteria': True,
                'include_dependencies': True,
                'include_history': True
            },
            sections=[
                {'id': 'project_info', 'name': '项目信息', 'required': True},
                {'id': 'requirements_list', 'name': '需求列表', 'required': True},
                {'id': 'dependencies', 'name': '依赖关系', 'required': False},
                {'id': 'change_history', 'name': '变更历史', 'required': False},
                {'id': 'appendix', 'name': '附录', 'required': False}
            ],
            filters={},
            formatting={
                'page_size': 'A4',
                'orientation': 'portrait',
                'font_family': 'Arial',
                'font_size': 11
            },
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 质量评估报告模板
        templates['quality'] = ReportTemplate(
            id='quality',
            name='需求质量评估报告',
            description='需求质量分析和改进建议',
            report_type=ReportType.QUALITY,
            template_config={
                'include_quality_metrics': True,
                'include_improvement_suggestions': True,
                'include_benchmark_comparison': True
            },
            sections=[
                {'id': 'quality_overview', 'name': '质量概览', 'required': True},
                {'id': 'quality_dimensions', 'name': '质量维度分析', 'required': True},
                {'id': 'quality_issues', 'name': '质量问题', 'required': True},
                {'id': 'improvement_plan', 'name': '改进计划', 'required': True},
                {'id': 'benchmark_comparison', 'name': '基准对比', 'required': False}
            ],
            filters={},
            formatting={
                'page_size': 'A4',
                'orientation': 'portrait',
                'font_family': 'Arial',
                'font_size': 12
            },
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return templates
    
    async def generate_report(self, request: ReportRequest) -> GeneratedReport:
        """
        生成报告
        
        Args:
            request: 报告请求
            
        Returns:
            生成的报告
        """
        try:
            # 获取报告模板
            template = self._get_template(request.template_id, request.report_type)
            
            # 收集报告数据
            report_data = await self._collect_report_data(request, template)
            
            # 生成报告内容
            content = await self._generate_report_content(report_data, request.format, template)
            
            # 创建报告对象
            report_id = self._generate_report_id()
            file_name = self._generate_file_name(request, report_data.title)
            
            generated_report = GeneratedReport(
                id=report_id,
                request=request,
                data=report_data,
                content=content,
                format=request.format,
                file_name=file_name,
                file_size=len(content),
                generated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7)  # 7天后过期
            )
            
            logger.info(f"报告生成成功: {report_id}, 格式: {request.format.value}, 大小: {len(content)} bytes")
            
            return generated_report
            
        except Exception as e:
            logger.error(f"报告生成失败: {str(e)}")
            raise ValidationError(f"报告生成失败: {str(e)}")
    
    def _get_template(self, template_id: Optional[str], report_type: ReportType) -> ReportTemplate:
        """获取报告模板"""
        if template_id and template_id in self.templates:
            return self.templates[template_id]
        
        # 根据报告类型选择默认模板
        default_templates = {
            ReportType.SUMMARY: 'summary',
            ReportType.DETAILED: 'detailed',
            ReportType.QUALITY: 'quality'
        }
        
        default_template_id = default_templates.get(report_type, 'summary')
        return self.templates.get(default_template_id, self.templates['summary'])
    
    async def _collect_report_data(self, request: ReportRequest, template: ReportTemplate) -> ReportData:
        """收集报告数据"""
        # 获取项目信息
        project_info = None
        if request.project_id:
            project_info = await self._get_project_info(request.project_id)
        
        # 获取需求指标
        metrics = await self.analytics_service.calculate_requirement_metrics(request.project_id)
        
        # 根据报告类型收集特定数据
        sections = []
        charts = []
        
        if request.report_type == ReportType.SUMMARY:
            sections, charts = await self._collect_summary_data(request, template, metrics)
        elif request.report_type == ReportType.DETAILED:
            sections, charts = await self._collect_detailed_data(request, template, metrics)
        elif request.report_type == ReportType.QUALITY:
            sections, charts = await self._collect_quality_data(request, template, metrics)
        elif request.report_type == ReportType.METRICS:
            sections, charts = await self._collect_metrics_data(request, template, metrics)
        else:
            sections, charts = await self._collect_custom_data(request, template, metrics)
        
        # 生成摘要
        summary = self._generate_summary(metrics, request.report_type)
        
        # 收集原始数据（如果需要）
        raw_data = None
        if request.include_raw_data:
            raw_data = await self._collect_raw_data(request)
        
        return ReportData(
            title=self._generate_report_title(request, template),
            subtitle=self._generate_report_subtitle(request, project_info),
            generated_at=datetime.utcnow(),
            generated_by=request.requested_by or 1,
            project_info=project_info,
            summary=summary,
            sections=sections,
            charts=charts if request.include_charts else [],
            raw_data=raw_data,
            metadata={
                'template_id': template.id,
                'filters_applied': request.filters or {},
                'generation_time': datetime.utcnow().isoformat()
            }
        )
    
    async def _get_project_info(self, project_id: int) -> Dict[str, Any]:
        """获取项目信息"""
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"项目不存在: {project_id}")
        
        return {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'start_date': project.planned_start_date.isoformat() if project.planned_start_date else None,
            'end_date': project.planned_end_date.isoformat() if project.planned_end_date else None,
            'progress': float(project.progress_percentage or 0),
            'budget': float(project.budget or 0),
            'manager': project.manager_id
        }
    
    async def _collect_summary_data(self, request: ReportRequest, template: ReportTemplate, 
                                  metrics: RequirementMetrics) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """收集概要报告数据"""
        sections = []
        charts = []
        
        # 项目概览部分
        sections.append({
            'id': 'overview',
            'title': '项目概览',
            'content': {
                'total_requirements': metrics.total_requirements,
                'completion_rate': f"{metrics.completion_rate:.1%}",
                'approval_rate': f"{metrics.approval_rate:.1%}",
                'avg_quality_score': f"{metrics.avg_quality_score:.1f}/10",
                'total_effort': f"{metrics.total_estimated_effort:.1f}人天"
            }
        })
        
        # 关键指标部分
        sections.append({
            'id': 'metrics',
            'title': '关键指标',
            'content': {
                'progress_metrics': {
                    'completion_rate': metrics.completion_rate,
                    'approval_rate': metrics.approval_rate,
                    'review_pass_rate': metrics.review_pass_rate
                },
                'quality_metrics': {
                    'avg_quality_score': metrics.avg_quality_score,
                    'avg_completeness_score': metrics.avg_completeness_score,
                    'quality_distribution': metrics.quality_distribution
                },
                'effort_metrics': {
                    'total_estimated': metrics.total_estimated_effort,
                    'total_actual': metrics.total_actual_effort,
                    'variance': metrics.effort_variance
                }
            }
        })
        
        # 状态分布部分
        sections.append({
            'id': 'status_distribution',
            'title': '需求状态分布',
            'content': {
                'distribution': metrics.status_distribution,
                'total': metrics.total_requirements
            }
        })
        
        # 生成图表
        if request.include_charts:
            charts.extend([
                {
                    'id': 'status_pie_chart',
                    'type': 'pie',
                    'title': '需求状态分布',
                    'data': metrics.status_distribution
                },
                {
                    'id': 'priority_bar_chart',
                    'type': 'bar',
                    'title': '优先级分布',
                    'data': metrics.priority_distribution
                },
                {
                    'id': 'quality_histogram',
                    'type': 'histogram',
                    'title': '质量评分分布',
                    'data': metrics.quality_distribution
                }
            ])
        
        return sections, charts
    
    async def _collect_detailed_data(self, request: ReportRequest, template: ReportTemplate,
                                   metrics: RequirementMetrics) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """收集详细报告数据"""
        sections = []
        charts = []
        
        # 获取详细需求列表
        requirements = await self._get_requirements_list(request.project_id, request.filters)
        
        # 项目信息部分
        if request.project_id:
            project_info = await self._get_project_info(request.project_id)
            sections.append({
                'id': 'project_info',
                'title': '项目信息',
                'content': project_info
            })
        
        # 需求列表部分
        requirements_data = []
        for req in requirements:
            req_data = {
                'id': req.id,
                'code': req.requirement_code,
                'title': req.title,
                'description': req.description,
                'type': req.requirement_type.value if req.requirement_type else None,
                'priority': req.priority.value if req.priority else None,
                'status': req.status.value if req.status else None,
                'complexity': req.complexity.value if req.complexity else None,
                'estimated_effort': float(req.estimated_effort) if req.estimated_effort else None,
                'actual_effort': float(req.actual_effort) if req.actual_effort else None,
                'quality_score': float(req.quality_score) if req.quality_score else None,
                'acceptance_criteria': req.acceptance_criteria,
                'created_at': req.created_at.isoformat() if req.created_at else None,
                'updated_at': req.updated_at.isoformat() if req.updated_at else None
            }
            requirements_data.append(req_data)
        
        sections.append({
            'id': 'requirements_list',
            'title': '需求详细列表',
            'content': {
                'requirements': requirements_data,
                'total_count': len(requirements_data)
            }
        })
        
        # 依赖关系部分
        if template.template_config.get('include_dependencies', False):
            dependencies = await self._get_dependencies_data(request.project_id)
            sections.append({
                'id': 'dependencies',
                'title': '需求依赖关系',
                'content': {
                    'dependencies': dependencies,
                    'total_count': len(dependencies)
                }
            })
        
        # 变更历史部分
        if template.template_config.get('include_history', False):
            change_history = await self._get_change_history_data(request.project_id)
            sections.append({
                'id': 'change_history',
                'title': '需求变更历史',
                'content': {
                    'changes': change_history,
                    'total_count': len(change_history)
                }
            })
        
        return sections, charts
    
    async def _collect_quality_data(self, request: ReportRequest, template: ReportTemplate,
                                  metrics: RequirementMetrics) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """收集质量报告数据"""
        sections = []
        charts = []
        
        # 获取质量评估数据
        quality_assessment = await self.analytics_service.assess_requirement_quality(request.project_id)
        
        # 质量概览部分
        sections.append({
            'id': 'quality_overview',
            'title': '质量概览',
            'content': {
                'overall_score': f"{quality_assessment.overall_quality_score:.2f}",
                'total_requirements': metrics.total_requirements,
                'quality_trend': quality_assessment.quality_trend,
                'assessment_date': quality_assessment.assessed_at.isoformat()
            }
        })
        
        # 质量维度分析部分
        sections.append({
            'id': 'quality_dimensions',
            'title': '质量维度分析',
            'content': {
                'completeness': quality_assessment.completeness_score,
                'consistency': quality_assessment.consistency_score,
                'clarity': quality_assessment.clarity_score,
                'testability': quality_assessment.testability_score,
                'traceability': quality_assessment.traceability_score
            }
        })
        
        # 质量问题部分
        sections.append({
            'id': 'quality_issues',
            'title': '质量问题分析',
            'content': {
                'issues': quality_assessment.quality_issues,
                'total_issues': sum(quality_assessment.quality_issues.values())
            }
        })
        
        # 改进建议部分
        sections.append({
            'id': 'improvement_plan',
            'title': '改进建议',
            'content': {
                'suggestions': quality_assessment.improvement_suggestions,
                'priority_actions': quality_assessment.improvement_suggestions[:3]  # 前3个优先建议
            }
        })
        
        # 基准对比部分
        if template.template_config.get('include_benchmark_comparison', False):
            sections.append({
                'id': 'benchmark_comparison',
                'title': '基准对比',
                'content': {
                    'comparison': quality_assessment.benchmark_comparison,
                    'performance_summary': self._analyze_benchmark_performance(quality_assessment.benchmark_comparison)
                }
            })
        
        # 生成质量相关图表
        if request.include_charts:
            charts.extend([
                {
                    'id': 'quality_dimensions_radar',
                    'type': 'radar',
                    'title': '质量维度雷达图',
                    'data': {
                        'completeness': quality_assessment.completeness_score,
                        'consistency': quality_assessment.consistency_score,
                        'clarity': quality_assessment.clarity_score,
                        'testability': quality_assessment.testability_score,
                        'traceability': quality_assessment.traceability_score
                    }
                },
                {
                    'id': 'quality_issues_bar',
                    'type': 'bar',
                    'title': '质量问题分布',
                    'data': quality_assessment.quality_issues
                }
            ])
        
        return sections, charts
    
    async def _collect_metrics_data(self, request: ReportRequest, template: ReportTemplate,
                                  metrics: RequirementMetrics) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """收集指标报告数据"""
        sections = []
        charts = []
        
        # 基础指标部分
        sections.append({
            'id': 'basic_metrics',
            'title': '基础指标',
            'content': {
                'total_requirements': metrics.total_requirements,
                'status_distribution': metrics.status_distribution,
                'type_distribution': metrics.type_distribution,
                'priority_distribution': metrics.priority_distribution,
                'complexity_distribution': metrics.complexity_distribution
            }
        })
        
        # 进度指标部分
        sections.append({
            'id': 'progress_metrics',
            'title': '进度指标',
            'content': {
                'completion_rate': metrics.completion_rate,
                'approval_rate': metrics.approval_rate,
                'review_pass_rate': metrics.review_pass_rate,
                'avg_cycle_time': metrics.avg_cycle_time,
                'avg_review_time': metrics.avg_review_time,
                'avg_development_time': metrics.avg_development_time
            }
        })
        
        # 质量指标部分
        sections.append({
            'id': 'quality_metrics',
            'title': '质量指标',
            'content': {
                'avg_quality_score': metrics.avg_quality_score,
                'avg_completeness_score': metrics.avg_completeness_score,
                'quality_distribution': metrics.quality_distribution
            }
        })
        
        # 工作量指标部分
        sections.append({
            'id': 'effort_metrics',
            'title': '工作量指标',
            'content': {
                'total_estimated_effort': metrics.total_estimated_effort,
                'total_actual_effort': metrics.total_actual_effort,
                'effort_variance': metrics.effort_variance,
                'avg_effort_per_requirement': metrics.avg_effort_per_requirement
            }
        })
        
        # 变更和依赖指标部分
        sections.append({
            'id': 'change_dependency_metrics',
            'title': '变更和依赖指标',
            'content': {
                'change_request_count': metrics.change_request_count,
                'change_approval_rate': metrics.change_approval_rate,
                'avg_change_impact': metrics.avg_change_impact,
                'dependency_count': metrics.dependency_count,
                'dependency_complexity': metrics.dependency_complexity,
                'circular_dependencies': metrics.circular_dependencies
            }
        })
        
        # 协作指标部分
        sections.append({
            'id': 'collaboration_metrics',
            'title': '协作指标',
            'content': {
                'review_participation_rate': metrics.review_participation_rate,
                'avg_comments_per_review': metrics.avg_comments_per_review
            }
        })
        
        return sections, charts
    
    async def _collect_custom_data(self, request: ReportRequest, template: ReportTemplate,
                                 metrics: RequirementMetrics) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """收集自定义报告数据"""
        sections = []
        charts = []
        
        # 根据自定义部分收集数据
        if request.custom_sections:
            for section_name in request.custom_sections:
                if section_name == 'overview':
                    sections.append({
                        'id': 'overview',
                        'title': '概览',
                        'content': {
                            'total_requirements': metrics.total_requirements,
                            'completion_rate': metrics.completion_rate,
                            'quality_score': metrics.avg_quality_score
                        }
                    })
                elif section_name == 'detailed_list':
                    requirements = await self._get_requirements_list(request.project_id, request.filters)
                    sections.append({
                        'id': 'detailed_list',
                        'title': '详细列表',
                        'content': {
                            'requirements': [req.to_dict() for req in requirements]
                        }
                    })
        
        return sections, charts
    
    async def _get_requirements_list(self, project_id: Optional[int], 
                                   filters: Optional[Dict[str, Any]]) -> List[Requirement]:
        """获取需求列表"""
        query = select(Requirement)
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        # 应用过滤器
        if filters:
            if 'status' in filters:
                query = query.where(Requirement.status.in_(filters['status']))
            if 'priority' in filters:
                query = query.where(Requirement.priority.in_(filters['priority']))
            if 'type' in filters:
                query = query.where(Requirement.requirement_type.in_(filters['type']))
            if 'date_range' in filters:
                date_range = filters['date_range']
                if 'start' in date_range:
                    query = query.where(Requirement.created_at >= date_range['start'])
                if 'end' in date_range:
                    query = query.where(Requirement.created_at <= date_range['end'])
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_dependencies_data(self, project_id: Optional[int]) -> List[Dict[str, Any]]:
        """获取依赖关系数据"""
        query = select(RequirementDependency)
        if project_id:
            query = query.join(Requirement, RequirementDependency.source_requirement_id == Requirement.id)\
                         .where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        dependencies = result.scalars().all()
        
        return [dep.to_dict() for dep in dependencies]
    
    async def _get_change_history_data(self, project_id: Optional[int]) -> List[Dict[str, Any]]:
        """获取变更历史数据"""
        query = select(RequirementChangeRequest)
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        changes = result.scalars().all()
        
        return [change.to_dict() for change in changes]
    
    async def _collect_raw_data(self, request: ReportRequest) -> Dict[str, Any]:
        """收集原始数据"""
        raw_data = {}
        
        # 获取需求原始数据
        requirements = await self._get_requirements_list(request.project_id, request.filters)
        raw_data['requirements'] = [req.to_dict() for req in requirements]
        
        # 获取依赖关系原始数据
        dependencies = await self._get_dependencies_data(request.project_id)
        raw_data['dependencies'] = dependencies
        
        # 获取变更请求原始数据
        changes = await self._get_change_history_data(request.project_id)
        raw_data['change_requests'] = changes
        
        return raw_data
    
    def _generate_summary(self, metrics: RequirementMetrics, report_type: ReportType) -> Dict[str, Any]:
        """生成报告摘要"""
        summary = {
            'total_requirements': metrics.total_requirements,
            'completion_rate': metrics.completion_rate,
            'quality_score': metrics.avg_quality_score,
            'key_insights': []
        }
        
        # 根据数据生成关键洞察
        if metrics.completion_rate < 0.5:
            summary['key_insights'].append('项目完成率较低，需要关注进度管理')
        
        if metrics.avg_quality_score < 6.0:
            summary['key_insights'].append('需求质量有待提升，建议加强评审')
        
        if metrics.change_request_count > metrics.total_requirements * 0.3:
            summary['key_insights'].append('变更请求较多，需要加强需求稳定性')
        
        if metrics.effort_variance > 0.5:
            summary['key_insights'].append('工作量估算偏差较大，需要改进估算方法')
        
        return summary
    
    def _generate_report_title(self, request: ReportRequest, template: ReportTemplate) -> str:
        """生成报告标题"""
        base_title = template.name
        
        if request.project_id:
            base_title += f" - 项目 {request.project_id}"
        
        return base_title
    
    def _generate_report_subtitle(self, request: ReportRequest, 
                                project_info: Optional[Dict[str, Any]]) -> str:
        """生成报告副标题"""
        subtitle_parts = []
        
        if project_info:
            subtitle_parts.append(f"项目: {project_info['name']}")
        
        if request.date_range:
            start_date = request.date_range.get('start', '').strftime('%Y-%m-%d') if request.date_range.get('start') else ''
            end_date = request.date_range.get('end', '').strftime('%Y-%m-%d') if request.date_range.get('end') else ''
            if start_date and end_date:
                subtitle_parts.append(f"时间范围: {start_date} 至 {end_date}")
        
        subtitle_parts.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return " | ".join(subtitle_parts)
    
    def _analyze_benchmark_performance(self, benchmark_comparison: Dict[str, float]) -> Dict[str, str]:
        """分析基准性能"""
        performance = {}
        
        for metric, diff in benchmark_comparison.items():
            if diff > 0.1:
                performance[metric] = '优于基准'
            elif diff < -0.1:
                performance[metric] = '低于基准'
            else:
                performance[metric] = '接近基准'
        
        return performance
    
    async def _generate_report_content(self, data: ReportData, format: ReportFormat, 
                                     template: ReportTemplate) -> bytes:
        """生成报告内容"""
        if format == ReportFormat.JSON:
            return self._generate_json_content(data)
        elif format == ReportFormat.HTML:
            return self._generate_html_content(data, template)
        elif format == ReportFormat.CSV:
            return self._generate_csv_content(data)
        elif format == ReportFormat.PDF:
            return await self._generate_pdf_content(data, template)
        elif format == ReportFormat.EXCEL:
            return await self._generate_excel_content(data, template)
        elif format == ReportFormat.WORD:
            return await self._generate_word_content(data, template)
        else:
            raise ValidationError(f"不支持的报告格式: {format.value}")
    
    def _generate_json_content(self, data: ReportData) -> bytes:
        """生成JSON格式内容"""
        json_data = asdict(data)
        # 处理datetime对象
        json_data['generated_at'] = data.generated_at.isoformat()
        return json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
    
    def _generate_html_content(self, data: ReportData, template: ReportTemplate) -> bytes:
        """生成HTML格式内容"""
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{data.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin-bottom: 25px; }}
                .section h2 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
                .chart-placeholder {{ background: #e9ecef; padding: 20px; text-align: center; margin: 10px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{data.title}</h1>
                <p>{data.subtitle}</p>
            </div>
            
            <div class="section">
                <h2>报告摘要</h2>
                <div class="metric">总需求数: {data.summary.get('total_requirements', 0)}</div>
                <div class="metric">完成率: {data.summary.get('completion_rate', 0):.1%}</div>
                <div class="metric">质量评分: {data.summary.get('quality_score', 0):.1f}/10</div>
            </div>
        """
        
        # 添加各个部分
        for section in data.sections:
            html_content += f"""
            <div class="section">
                <h2>{section['title']}</h2>
                <div>{self._format_section_content_html(section['content'])}</div>
            </div>
            """
        
        # 添加图表占位符
        for chart in data.charts:
            html_content += f"""
            <div class="section">
                <h2>{chart['title']}</h2>
                <div class="chart-placeholder">图表: {chart['type']} - {chart['title']}</div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        return html_content.encode('utf-8')
    
    def _format_section_content_html(self, content: Any) -> str:
        """格式化HTML部分内容"""
        if isinstance(content, dict):
            html = "<table>"
            for key, value in content.items():
                if isinstance(value, (dict, list)):
                    value = str(value)
                html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
            html += "</table>"
            return html
        elif isinstance(content, list):
            html = "<ul>"
            for item in content:
                html += f"<li>{item}</li>"
            html += "</ul>"
            return html
        else:
            return str(content)
    
    def _generate_csv_content(self, data: ReportData) -> bytes:
        """生成CSV格式内容"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题
        writer.writerow(['报告标题', data.title])
        writer.writerow(['生成时间', data.generated_at.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # 写入摘要
        writer.writerow(['摘要'])
        for key, value in data.summary.items():
            writer.writerow([key, value])
        writer.writerow([])
        
        # 写入各部分数据
        for section in data.sections:
            writer.writerow([section['title']])
            if isinstance(section['content'], dict):
                for key, value in section['content'].items():
                    writer.writerow([key, value])
            writer.writerow([])
        
        return output.getvalue().encode('utf-8')
    
    async def _generate_pdf_content(self, data: ReportData, template: ReportTemplate) -> bytes:
        """生成PDF格式内容"""
        # 这里需要使用PDF生成库，如reportlab
        # 简化实现，返回HTML转PDF的占位符
        html_content = self._generate_html_content(data, template)
        
        # 实际实现中应该使用weasyprint或类似库将HTML转换为PDF
        # from weasyprint import HTML
        # pdf_bytes = HTML(string=html_content.decode('utf-8')).write_pdf()
        # return pdf_bytes
        
        # 占位符实现
        return b"PDF content placeholder - " + html_content
    
    async def _generate_excel_content(self, data: ReportData, template: ReportTemplate) -> bytes:
        """生成Excel格式内容"""
        # 这里需要使用Excel生成库，如openpyxl
        # 简化实现，返回占位符
        return b"Excel content placeholder"
    
    async def _generate_word_content(self, data: ReportData, template: ReportTemplate) -> bytes:
        """生成Word格式内容"""
        # 这里需要使用Word生成库，如python-docx
        # 简化实现，返回占位符
        return b"Word content placeholder"
    
    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import uuid
        return f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    def _generate_file_name(self, request: ReportRequest, title: str) -> str:
        """生成文件名"""
        # 清理标题中的特殊字符
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        extension = request.format.value.lower()
        
        return f"{clean_title}_{timestamp}.{extension}"
    
    async def get_available_templates(self) -> List[ReportTemplate]:
        """获取可用的报告模板"""
        return list(self.templates.values())
    
    async def create_custom_template(self, template: ReportTemplate) -> ReportTemplate:
        """创建自定义报告模板"""
        self.templates[template.id] = template
        return template
    
    async def update_template(self, template_id: str, updates: Dict[str, Any]) -> ReportTemplate:
        """更新报告模板"""
        if template_id not in self.templates:
            raise NotFoundError(f"模板不存在: {template_id}")
        
        template = self.templates[template_id]
        
        # 更新模板属性
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        
        return template
    
    async def delete_template(self, template_id: str) -> bool:
        """删除报告模板"""
        if template_id in self.templates:
            del self.templates[template_id]
            return True
        return False