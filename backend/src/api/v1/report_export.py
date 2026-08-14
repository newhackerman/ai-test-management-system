"""
报告导出API

提供多种格式的报告生成和下载、报告模板管理和定制、导出权限验证和审计日志
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import io
import json
import csv
import uuid
import os
from pathlib import Path

from ...core.database import get_db
from ...services.data_aggregation_service import DataAggregationService
from ...services.auth import get_current_user
from ...models.user import User
from ...decorators.dashboard_permissions import (
    require_dashboard_permission,
    get_user_dashboard_permissions
)
from ...services.dashboard_permission_service import DashboardPermissionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report-export", tags=["报告导出"])

# 枚举定义

class ExportFormat(str, Enum):
    """导出格式"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    PNG = "png"
    SVG = "svg"

class ReportType(str, Enum):
    """报告类型"""
    PROJECT_OVERVIEW = "project_overview"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    TEST_SUMMARY = "test_summary"
    DEVELOPMENT_METRICS = "development_metrics"
    QUALITY_REPORT = "quality_report"
    PERFORMANCE_REPORT = "performance_report"
    CUSTOM_DASHBOARD = "custom_dashboard"

class TemplateType(str, Enum):
    """模板类型"""
    SYSTEM = "system"
    ENTERPRISE = "enterprise"
    USER_CUSTOM = "user_custom"

class ExportStatus(str, Enum):
    """导出状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

# Pydantic模型定义

class ExportRequest(BaseModel):
    """导出请求模型"""
    report_type: ReportType = Field(..., description="报告类型")
    format: ExportFormat = Field(..., description="导出格式")
    template_id: Optional[int] = Field(None, description="模板ID")
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")
    date_range: Optional[Dict[str, str]] = Field(None, description="日期范围")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    options: Optional[Dict[str, Any]] = Field(None, description="导出选项")
    include_charts: bool = Field(True, description="是否包含图表")
    include_raw_data: bool = Field(False, description="是否包含原始数据")

    @validator('date_range')
    def validate_date_range(cls, v):
        """验证日期范围"""
        if v:
            if 'start_date' in v and 'end_date' in v:
                try:
                    start = datetime.fromisoformat(v['start_date'])
                    end = datetime.fromisoformat(v['end_date'])
                    if end < start:
                        raise ValueError("End date must be after start date")
                except ValueError as e:
                    raise ValueError(f"Invalid date format: {str(e)}")
        return v

class ScheduledExportRequest(BaseModel):
    """定时导出请求模型"""
    report_type: ReportType = Field(..., description="报告类型")
    format: ExportFormat = Field(..., description="导出格式")
    template_id: Optional[int] = Field(None, description="模板ID")
    schedule_cron: str = Field(..., description="Cron表达式")
    recipients: List[str] = Field(..., description="接收者邮箱列表")
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    is_active: bool = Field(True, description="是否激活")

class ReportTemplate(BaseModel):
    """报告模板模型"""
    id: Optional[int] = None
    template_name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    template_type: TemplateType = Field(..., description="模板类型")
    report_type: ReportType = Field(..., description="报告类型")
    template_config: Dict[str, Any] = Field(..., description="模板配置")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    is_public: bool = Field(False, description="是否公开")
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ExportJob(BaseModel):
    """导出任务模型"""
    job_id: str
    user_id: int
    report_type: str
    format: str
    status: ExportStatus
    progress: int = Field(0, ge=0, le=100, description="进度百分比")
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    expires_at: str

class ExportResponse(BaseModel):
    """导出响应模型"""
    job_id: str
    status: ExportStatus
    download_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    expires_at: str
    message: str

# 依赖注入

def get_data_service(db: Session = Depends(get_db)) -> DataAggregationService:
    """获取数据聚合服务实例"""
    return DataAggregationService(db)

# 全局导出任务管理
export_jobs: Dict[str, ExportJob] = {}

# API端点

@router.post("/export", response_model=ExportResponse)
@require_dashboard_permission(DashboardPermissionType.REPORT_EXPORT)
async def create_export_job(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_service)
):
    """
    创建导出任务
    
    - **report_type**: 报告类型
    - **format**: 导出格式 (pdf, excel, csv, json, png, svg)
    - **template_id**: 模板ID (可选)
    - **project_ids**: 项目ID列表 (可选)
    - **date_range**: 日期范围 (可选)
    - **filters**: 过滤条件 (可选)
    - **include_charts**: 是否包含图表
    - **include_raw_data**: 是否包含原始数据
    """
    try:
        # 生成任务ID
        job_id = f"export_{uuid.uuid4().hex[:12]}"
        
        # 创建导出任务
        export_job = ExportJob(
            job_id=job_id,
            user_id=current_user.id,
            report_type=request.report_type.value,
            format=request.format.value,
            status=ExportStatus.PENDING,
            progress=0,
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat()
        )
        
        # 存储任务信息
        export_jobs[job_id] = export_job
        
        # 添加后台任务
        background_tasks.add_task(
            _process_export_job,
            job_id,
            request,
            current_user,
            data_service
        )
        
        # 记录审计日志
        await _log_export_activity(
            user_id=current_user.id,
            action="export_requested",
            report_type=request.report_type.value,
            format=request.format.value,
            job_id=job_id
        )
        
        return ExportResponse(
            job_id=job_id,
            status=ExportStatus.PENDING,
            expires_at=export_job.expires_at,
            message="导出任务已创建，正在处理中"
        )
        
    except Exception as e:
        logger.error(f"Error creating export job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建导出任务失败"
        )

@router.get("/jobs/{job_id}", response_model=ExportJob)
async def get_export_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取导出任务状态
    
    - **job_id**: 任务ID
    """
    try:
        if job_id not in export_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="导出任务不存在"
            )
        
        job = export_jobs[job_id]
        
        # 检查权限
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此导出任务"
            )
        
        # 检查是否过期
        if datetime.fromisoformat(job.expires_at) < datetime.utcnow():
            job.status = ExportStatus.EXPIRED
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取导出任务状态失败"
        )

@router.get("/jobs/{job_id}/download")
async def download_export_file(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    下载导出文件
    
    - **job_id**: 任务ID
    """
    try:
        if job_id not in export_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="导出任务不存在"
            )
        
        job = export_jobs[job_id]
        
        # 检查权限
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限下载此文件"
            )
        
        # 检查任务状态
        if job.status != ExportStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"导出任务未完成，当前状态: {job.status.value}"
            )
        
        # 检查文件是否存在
        if not job.file_path or not os.path.exists(job.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="导出文件不存在或已过期"
            )
        
        # 记录下载日志
        await _log_export_activity(
            user_id=current_user.id,
            action="file_downloaded",
            report_type=job.report_type,
            format=job.format,
            job_id=job_id
        )
        
        # 返回文件
        file_name = os.path.basename(job.file_path)
        return FileResponse(
            path=job.file_path,
            filename=file_name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下载文件失败"
        )

@router.get("/jobs", response_model=List[ExportJob])
async def get_user_export_jobs(
    status_filter: Optional[ExportStatus] = Query(None, alias="status", description="状态过滤"),
    limit: int = Query(20, ge=1, le=100, description="限制数量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的导出任务列表

    - **status**: 状态过滤 (可选)
    - **limit**: 限制数量
    """
    try:
        user_jobs = [
            job for job in export_jobs.values()
            if job.user_id == current_user.id
        ]

        # 状态过滤
        if status_filter:
            user_jobs = [job for job in user_jobs if job.status == status_filter]
        
        # 按创建时间排序
        user_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # 限制数量
        return user_jobs[:limit]
        
    except Exception as e:
        logger.error(f"Error getting user export jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取导出任务列表失败"
        )

@router.delete("/jobs/{job_id}")
async def cancel_export_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    取消导出任务
    
    - **job_id**: 任务ID
    """
    try:
        if job_id not in export_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="导出任务不存在"
            )
        
        job = export_jobs[job_id]
        
        # 检查权限
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限取消此导出任务"
            )
        
        # 检查是否可以取消
        if job.status in [ExportStatus.COMPLETED, ExportStatus.FAILED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务已完成或失败，无法取消"
            )
        
        # 更新任务状态
        job.status = ExportStatus.FAILED
        job.error_message = "用户取消"
        job.completed_at = datetime.utcnow().isoformat()
        
        # 清理文件
        if job.file_path and os.path.exists(job.file_path):
            try:
                os.remove(job.file_path)
            except:
                pass
        
        # 记录取消日志
        await _log_export_activity(
            user_id=current_user.id,
            action="export_cancelled",
            report_type=job.report_type,
            format=job.format,
            job_id=job_id
        )
        
        return {
            "message": "导出任务已取消",
            "job_id": job_id,
            "cancelled_at": job.completed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling export job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消导出任务失败"
        )

@router.get("/templates", response_model=List[ReportTemplate])
async def get_report_templates(
    report_type: Optional[ReportType] = Query(None, description="报告类型过滤"),
    template_type: Optional[TemplateType] = Query(None, description="模板类型过滤"),
    current_user: User = Depends(get_current_user)
):
    """
    获取报告模板列表
    
    - **report_type**: 报告类型过滤 (可选)
    - **template_type**: 模板类型过滤 (可选)
    """
    try:
        # 这里应该从数据库获取模板列表
        # 为了演示，返回一些示例模板
        templates = [
            ReportTemplate(
                id=1,
                template_name="标准项目概览报告",
                template_type=TemplateType.SYSTEM,
                report_type=ReportType.PROJECT_OVERVIEW,
                template_config={
                    "sections": ["summary", "progress", "risks", "team"],
                    "chart_types": ["bar", "pie", "line"],
                    "color_scheme": "default"
                },
                description="系统预设的项目概览报告模板",
                is_public=True,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            ),
            ReportTemplate(
                id=2,
                template_name="需求分析详细报告",
                template_type=TemplateType.SYSTEM,
                report_type=ReportType.REQUIREMENT_ANALYSIS,
                template_config={
                    "sections": ["overview", "status", "quality", "traceability"],
                    "chart_types": ["bar", "line", "scatter"],
                    "color_scheme": "blue"
                },
                description="系统预设的需求分析报告模板",
                is_public=True,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
        ]
        
        # 应用过滤条件
        if report_type:
            templates = [t for t in templates if t.report_type == report_type]
        
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        
        return templates
        
    except Exception as e:
        logger.error(f"Error getting report templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取报告模板失败"
        )

@router.post("/templates", response_model=ReportTemplate)
@require_dashboard_permission(DashboardPermissionType.TEMPLATE_CREATE)
async def create_report_template(
    template: ReportTemplate,
    current_user: User = Depends(get_current_user)
):
    """
    创建报告模板
    
    - **template_name**: 模板名称
    - **template_type**: 模板类型
    - **report_type**: 报告类型
    - **template_config**: 模板配置
    - **description**: 模板描述 (可选)
    - **is_public**: 是否公开
    """
    try:
        # 这里应该保存到数据库
        # 为了演示，直接返回创建的模板
        template.id = len(export_jobs) + 100  # 简单的ID生成
        template.created_by = current_user.id
        template.created_at = datetime.utcnow().isoformat()
        template.updated_at = datetime.utcnow().isoformat()
        
        # 记录创建日志
        await _log_export_activity(
            user_id=current_user.id,
            action="template_created",
            report_type=template.report_type.value,
            template_id=template.id
        )
        
        return template
        
    except Exception as e:
        logger.error(f"Error creating report template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建报告模板失败"
        )

@router.get("/formats")
async def get_supported_formats():
    """获取支持的导出格式"""
    try:
        formats = [
            {
                "value": format_type.value,
                "name": format_type.name,
                "description": _get_format_description(format_type),
                "mime_type": _get_format_mime_type(format_type)
            }
            for format_type in ExportFormat
        ]
        
        return {
            "formats": formats,
            "total_count": len(formats)
        }
        
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取支持格式失败"
        )

@router.get("/report-types")
async def get_supported_report_types():
    """获取支持的报告类型"""
    try:
        report_types = [
            {
                "value": report_type.value,
                "name": report_type.name,
                "description": _get_report_type_description(report_type)
            }
            for report_type in ReportType
        ]
        
        return {
            "report_types": report_types,
            "total_count": len(report_types)
        }
        
    except Exception as e:
        logger.error(f"Error getting supported report types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取支持报告类型失败"
        )

# 辅助函数

async def _process_export_job(
    job_id: str,
    request: ExportRequest,
    user: User,
    data_service: DataAggregationService
):
    """处理导出任务"""
    try:
        job = export_jobs[job_id]
        job.status = ExportStatus.PROCESSING
        job.progress = 10
        
        # 获取数据
        job.progress = 30
        data = await _get_export_data(request, user, data_service)
        
        # 生成文件
        job.progress = 60
        file_path = await _generate_export_file(job_id, request, data)
        
        # 更新任务状态
        job.progress = 100
        job.status = ExportStatus.COMPLETED
        job.file_path = file_path
        job.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        job.completed_at = datetime.utcnow().isoformat()
        
        # 记录完成日志
        await _log_export_activity(
            user_id=user.id,
            action="export_completed",
            report_type=request.report_type.value,
            format=request.format.value,
            job_id=job_id,
            file_size=job.file_size
        )
        
    except Exception as e:
        logger.error(f"Error processing export job {job_id}: {str(e)}")
        job = export_jobs[job_id]
        job.status = ExportStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow().isoformat()
        
        # 记录失败日志
        await _log_export_activity(
            user_id=user.id,
            action="export_failed",
            report_type=request.report_type.value,
            format=request.format.value,
            job_id=job_id,
            error=str(e)
        )

async def _get_export_data(
    request: ExportRequest,
    user: User,
    data_service: DataAggregationService
) -> Dict[str, Any]:
    """获取导出数据"""
    if request.report_type == ReportType.PROJECT_OVERVIEW:
        return await data_service.get_project_overview_data(user.id, "ADMIN")
    elif request.report_type == ReportType.REQUIREMENT_ANALYSIS:
        return await data_service.get_requirement_metrics(request.project_ids or [])
    elif request.report_type == ReportType.TEST_SUMMARY:
        return await data_service.get_test_metrics(request.project_ids or [])
    else:
        return {"message": f"No data available for report type: {request.report_type}"}

async def _generate_export_file(
    job_id: str,
    request: ExportRequest,
    data: Dict[str, Any]
) -> str:
    """生成导出文件"""
    # 创建导出目录
    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{request.report_type.value}_{timestamp}_{job_id}.{request.format.value}"
    file_path = export_dir / filename
    
    # 根据格式生成文件
    if request.format == ExportFormat.JSON:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    elif request.format == ExportFormat.CSV:
        # 简化的CSV导出
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Key', 'Value'])
            for key, value in data.items():
                writer.writerow([key, str(value)])
    
    elif request.format == ExportFormat.EXCEL:
        # 这里应该使用openpyxl或pandas生成Excel文件
        # 为了简化，创建一个文本文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Excel format not implemented yet\n")
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
    
    elif request.format == ExportFormat.PDF:
        # 这里应该使用reportlab或其他PDF库生成PDF文件
        # 为了简化，创建一个文本文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("PDF format not implemented yet\n")
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
    
    else:
        # 默认JSON格式
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(file_path)

async def _log_export_activity(
    user_id: int,
    action: str,
    report_type: str,
    format: str = None,
    job_id: str = None,
    template_id: int = None,
    file_size: int = None,
    error: str = None
):
    """记录导出活动日志"""
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "report_type": report_type,
            "format": format,
            "job_id": job_id,
            "template_id": template_id,
            "file_size": file_size,
            "error": error
        }
        
        # 这里应该保存到审计日志表
        logger.info(f"Export activity: {json.dumps(log_entry)}")
        
    except Exception as e:
        logger.error(f"Error logging export activity: {str(e)}")

def _get_format_description(format_type: ExportFormat) -> str:
    """获取格式描述"""
    descriptions = {
        ExportFormat.PDF: "便携式文档格式，适合打印和分享",
        ExportFormat.EXCEL: "Excel电子表格格式，支持数据分析",
        ExportFormat.CSV: "逗号分隔值格式，通用数据交换格式",
        ExportFormat.JSON: "JSON数据格式，适合程序处理",
        ExportFormat.PNG: "PNG图片格式，适合图表导出",
        ExportFormat.SVG: "SVG矢量图格式，可缩放图形"
    }
    return descriptions.get(format_type, "未知格式")

def _get_format_mime_type(format_type: ExportFormat) -> str:
    """获取格式MIME类型"""
    mime_types = {
        ExportFormat.PDF: "application/pdf",
        ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ExportFormat.CSV: "text/csv",
        ExportFormat.JSON: "application/json",
        ExportFormat.PNG: "image/png",
        ExportFormat.SVG: "image/svg+xml"
    }
    return mime_types.get(format_type, "application/octet-stream")

def _get_report_type_description(report_type: ReportType) -> str:
    """获取报告类型描述"""
    descriptions = {
        ReportType.PROJECT_OVERVIEW: "项目概览报告，包含项目整体状态和关键指标",
        ReportType.REQUIREMENT_ANALYSIS: "需求分析报告，包含需求状态和质量分析",
        ReportType.TEST_SUMMARY: "测试总结报告，包含测试执行和质量统计",
        ReportType.DEVELOPMENT_METRICS: "开发指标报告，包含代码质量和开发效能",
        ReportType.QUALITY_REPORT: "质量报告，包含整体质量评估和改进建议",
        ReportType.PERFORMANCE_REPORT: "性能报告，包含系统性能和资源使用情况",
        ReportType.CUSTOM_DASHBOARD: "自定义仪表板报告，根据用户配置生成"
    }
    return descriptions.get(report_type, "未知报告类型")