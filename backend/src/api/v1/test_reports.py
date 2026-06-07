"""
测试报告管理API接口

本模块实现测试报告相关的RESTful API接口，包括：
- 报告生成和下载接口
- 报告统计和分析API
- 报告模板管理功能
- 报告分发和订阅功能
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging
import io

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ...core.allure_manager import get_allure_manager, TestExecutionData, AllureReportResult
from ...services.test_report_service import TestReportService
from ...services.test_report_distribution_service import TestReportDistributionService
from ...services.test_data_analysis_service import TestDataAnalysisService
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-reports", tags=["测试报告管理"])
security = HTTPBearer()


# 辅助函数
async def get_test_execution_by_id(db: Session, execution_id: int):
    """获取测试执行记录"""
    from ...models.test_case import TestExecution
    
    try:
        result = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        return result
    except Exception as e:
        logger.error(f"获取测试执行记录失败: {str(e)}")
        return None


# 请求模式
class GenerateReportRequest(BaseModel):
    """生成报告请求"""
    report_name: str = Field(..., min_length=1, max_length=200, description="报告名称")
    report_type: str = Field(..., description="报告类型")
    project_id: Optional[int] = Field(None, description="项目ID")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    template_id: Optional[int] = Field(None, description="报告模板ID")
    report_config: Dict[str, Any] = Field(..., description="报告配置")
    include_sections: List[str] = Field(..., description="包含的章节")
    date_range: Optional[Dict[str, Any]] = Field(None, description="数据时间范围")
    export_formats: List[str] = Field(["HTML"], description="导出格式")
    auto_send: bool = Field(False, description="是否自动发送")
    recipients: Optional[List[str]] = Field(None, description="接收人列表")


class CreateReportTemplateRequest(BaseModel):
    """创建报告模板请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_type: str = Field(..., description="模板类型")
    template_content: Dict[str, Any] = Field(..., description="模板内容")
    default_config: Dict[str, Any] = Field(..., description="默认配置")
    is_active: bool = Field(True, description="是否激活")


class UpdateReportTemplateRequest(BaseModel):
    """更新报告模板请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_content: Optional[Dict[str, Any]] = Field(None, description="模板内容")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置")
    is_active: Optional[bool] = Field(None, description="是否激活")


class CreateReportScheduleRequest(BaseModel):
    """创建报告调度请求"""
    name: str = Field(..., min_length=1, max_length=100, description="调度任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    report_config: Dict[str, Any] = Field(..., description="报告配置")
    template_id: Optional[int] = Field(None, description="模板ID")
    schedule_type: str = Field(..., description="调度类型")
    schedule_expression: str = Field(..., description="调度表达式")
    timezone: str = Field("UTC", description="时区")
    recipients: List[str] = Field(..., description="接收人列表")
    notification_config: Dict[str, Any] = Field(..., description="通知配置")
    is_active: bool = Field(True, description="是否激活")


class ShareReportRequest(BaseModel):
    """分享报告请求"""
    report_id: int = Field(..., description="报告ID")
    share_type: str = Field("link", description="分享类型")
    password_protected: bool = Field(False, description="是否密码保护")
    access_password: Optional[str] = Field(None, description="访问密码")
    max_access_count: Optional[int] = Field(None, description="最大访问次数")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    allowed_users: Optional[List[int]] = Field(None, description="允许访问的用户ID列表")
    allowed_roles: Optional[List[str]] = Field(None, description="允许访问的角色列表")


class GenerateAllureReportRequest(BaseModel):
    """生成Allure报告请求"""
    report_name: str = Field(..., min_length=1, max_length=200, description="报告名称")
    project_id: Optional[int] = Field(None, description="项目ID")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    test_execution_ids: List[int] = Field(..., description="测试执行ID列表")
    suite_name: Optional[str] = Field(None, description="测试套件名称")
    environment: Optional[str] = Field(None, description="测试环境")
    include_attachments: bool = Field(True, description="是否包含附件")
    auto_serve: bool = Field(False, description="是否自动启动服务")
    serve_port: Optional[int] = Field(None, description="服务端口")


class TestExecutionRequest(BaseModel):
    """测试执行数据请求"""
    test_case_id: str = Field(..., description="测试用例ID")
    test_name: str = Field(..., description="测试名称")
    status: str = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    description: Optional[str] = Field(None, description="测试描述")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_trace: Optional[str] = Field(None, description="错误堆栈")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")
    steps: Optional[List[Dict[str, Any]]] = Field(None, description="测试步骤")
    labels: Optional[Dict[str, str]] = Field(None, description="标签")
    links: Optional[List[Dict[str, str]]] = Field(None, description="链接")
    environment: Optional[str] = Field(None, description="测试环境")


# 响应模式
class TestReportResponse(BaseModel):
    """测试报告响应"""
    id: int = Field(..., description="报告ID")
    name: str = Field(..., description="报告名称")
    description: Optional[str] = Field(None, description="报告描述")
    report_type: str = Field(..., description="报告类型")
    project_id: Optional[int] = Field(None, description="项目ID")
    template_id: Optional[int] = Field(None, description="模板ID")
    report_config: Dict[str, Any] = Field(..., description="报告配置")
    include_sections: List[str] = Field(..., description="包含的章节")
    date_range: Optional[Dict[str, Any]] = Field(None, description="数据时间范围")
    export_formats: List[str] = Field(..., description="导出格式")
    file_paths: Optional[Dict[str, str]] = Field(None, description="文件路径")
    file_size: Optional[int] = Field(None, description="文件大小")
    status: str = Field(..., description="生成状态")
    generation_time: Optional[float] = Field(None, description="生成耗时")
    error_message: Optional[str] = Field(None, description="错误信息")
    view_count: int = Field(..., description="查看次数")
    download_count: int = Field(..., description="下载次数")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ReportTemplateResponse(BaseModel):
    """报告模板响应"""
    id: int = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_type: str = Field(..., description="模板类型")
    template_content: Dict[str, Any] = Field(..., description="模板内容")
    default_config: Dict[str, Any] = Field(..., description="默认配置")
    is_active: bool = Field(..., description="是否激活")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ReportScheduleResponse(BaseModel):
    """报告调度响应"""
    id: int = Field(..., description="调度ID")
    name: str = Field(..., description="调度任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    report_config: Dict[str, Any] = Field(..., description="报告配置")
    template_id: Optional[int] = Field(None, description="模板ID")
    schedule_type: str = Field(..., description="调度类型")
    schedule_expression: str = Field(..., description="调度表达式")
    timezone: str = Field(..., description="时区")
    recipients: List[str] = Field(..., description="接收人列表")
    notification_config: Dict[str, Any] = Field(..., description="通知配置")
    is_active: bool = Field(..., description="是否激活")
    last_run_time: Optional[datetime] = Field(None, description="上次运行时间")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    run_count: int = Field(..., description="运行次数")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ReportShareResponse(BaseModel):
    """报告分享响应"""
    id: int = Field(..., description="分享ID")
    report_id: int = Field(..., description="报告ID")
    share_token: str = Field(..., description="分享令牌")
    share_type: str = Field(..., description="分享类型")
    password_protected: bool = Field(..., description="是否密码保护")
    max_access_count: Optional[int] = Field(None, description="最大访问次数")
    access_count: int = Field(..., description="已访问次数")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    allowed_users: Optional[List[int]] = Field(None, description="允许访问的用户ID列表")
    allowed_roles: Optional[List[str]] = Field(None, description="允许访问的角色列表")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ReportAnalyticsResponse(BaseModel):
    """报告分析响应"""
    total_reports: int = Field(..., description="总报告数")
    reports_by_type: Dict[str, int] = Field(..., description="按类型分布")
    reports_by_status: Dict[str, int] = Field(..., description="按状态分布")
    generation_time_avg: Optional[float] = Field(None, description="平均生成时间")
    most_viewed_reports: List[Dict[str, Any]] = Field(..., description="最多查看的报告")
    most_downloaded_reports: List[Dict[str, Any]] = Field(..., description="最多下载的报告")
    report_trends: List[Dict[str, Any]] = Field(..., description="报告趋势")


class AllureReportResponse(BaseModel):
    """Allure报告响应"""
    report_id: str = Field(..., description="报告ID")
    report_name: str = Field(..., description="报告名称")
    report_path: str = Field(..., description="报告路径")
    report_url: Optional[str] = Field(None, description="报告访问URL")
    status: str = Field(..., description="生成状态")
    generation_time: float = Field(..., description="生成耗时(秒)")
    file_size: int = Field(..., description="文件大小(字节)")
    test_count: int = Field(..., description="测试用例总数")
    passed_count: int = Field(..., description="通过数量")
    failed_count: int = Field(..., description="失败数量")
    skipped_count: int = Field(..., description="跳过数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


# API接口实现
@router.post("/generate", response_model=BaseResponse[TestReportResponse])
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成测试报告
    
    根据配置生成测试报告，支持多种格式和自动分发。
    """
    try:
        service = TestReportService(db)
        
        # 创建报告记录
        report_data = {
            'name': request.report_name,
            'report_type': request.report_type,
            'project_id': request.project_id,
            'template_id': request.template_id,
            'report_config': request.report_config,
            'include_sections': request.include_sections,
            'date_range': request.date_range,
            'export_formats': request.export_formats,
            'created_by': current_user.id
        }
        
        # 创建报告记录
        report = await service.create_report_record(report_data)
        
        # 异步生成报告
        background_tasks.add_task(
            service.generate_report_async,
            report.id,
            request.auto_send,
            request.recipients or []
        )
        
        # 构建响应
        response_data = TestReportResponse(
            id=report.id,
            name=report.name,
            description=report.description,
            report_type=report.report_type,
            project_id=report.project_id,
            template_id=report.template_id,
            report_config=report.report_config,
            include_sections=report.include_sections,
            date_range=report.date_range,
            export_formats=report.export_formats,
            file_paths=report.file_paths,
            file_size=report.file_size,
            status=report.status,
            generation_time=report.generation_time,
            error_message=report.error_message,
            view_count=report.view_count,
            download_count=report.download_count,
            created_by=report.created_by,
            created_at=report.created_at,
            updated_at=report.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试报告生成任务已启动",
            data=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"生成测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/allure", response_model=BaseResponse[List[AllureReportResponse]])
async def list_allure_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取Allure报告列表

    获取所有可用的Allure报告列表。
    """
    try:
        allure_manager = get_allure_manager()
        reports = allure_manager.list_reports()

        response_data = []
        for report in reports:
            response_data.append(AllureReportResponse(
                report_id=report.report_id,
                report_name="Allure Report",
                report_path=report.report_path,
                report_url=report.report_url,
                status=report.status,
                generation_time=report.generation_time,
                file_size=report.file_size,
                test_count=report.test_count,
                passed_count=report.passed_count,
                failed_count=report.failed_count,
                skipped_count=report.skipped_count,
                error_message=report.error_message
            ))

        return BaseResponse(
            success=True,
            message="获取Allure报告列表成功",
            data=response_data
        )

    except Exception as e:
        logger.error(f"获取Allure报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Allure报告列表失败: {str(e)}")


@router.get("/{report_id:int}", response_model=BaseResponse[TestReportResponse])
async def get_report(
    report_id: int = Path(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试报告详情
    
    根据报告ID获取详细信息。
    """
    try:
        service = TestReportService(db)
        
        # 获取报告
        report = await service.get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="测试报告不存在")
        
        # 增加查看次数
        await service.increment_view_count(report_id)
        
        # 构建响应
        response_data = TestReportResponse(
            id=report.id,
            name=report.name,
            description=report.description,
            report_type=report.report_type,
            project_id=report.project_id,
            template_id=report.template_id,
            report_config=report.report_config,
            include_sections=report.include_sections,
            date_range=report.date_range,
            export_formats=report.export_formats,
            file_paths=report.file_paths,
            file_size=report.file_size,
            status=report.status,
            generation_time=report.generation_time,
            error_message=report.error_message,
            view_count=report.view_count + 1,  # 包含本次查看
            download_count=report.download_count,
            created_by=report.created_by,
            created_at=report.created_at,
            updated_at=report.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="获取测试报告成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{report_id:int}/download/{format}")
async def download_report(
    report_id: int = Path(..., description="报告ID"),
    format: str = Path(..., description="文件格式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    下载测试报告
    
    下载指定格式的测试报告文件。
    """
    try:
        service = TestReportService(db)
        
        # 获取报告
        report = await service.get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="测试报告不存在")
        
        # 检查格式是否可用
        if format.upper() not in report.export_formats:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 获取文件路径
        file_path = report.file_paths.get(format.upper())
        if not file_path:
            raise HTTPException(status_code=404, detail="报告文件不存在")
        
        # 增加下载次数
        await service.increment_download_count(report_id)
        
        # 返回文件
        return FileResponse(
            path=file_path,
            filename=f"{report.name}.{format.lower()}",
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"下载测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/", response_model=PaginatedResponse[TestReportResponse])
async def list_reports(
    project_id: Optional[int] = Query(None, description="项目ID"),
    report_type: Optional[str] = Query(None, description="报告类型"),
    status: Optional[str] = Query(None, description="生成状态"),
    created_by: Optional[int] = Query(None, description="创建人ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试报告列表
    
    支持多条件过滤和分页查询。
    """
    try:
        service = TestReportService(db)
        
        # 构建过滤条件
        filters = {}
        if project_id:
            filters['project_id'] = project_id
        if report_type:
            filters['report_type'] = report_type
        if status:
            filters['status'] = status
        if created_by:
            filters['created_by'] = created_by
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        if search:
            filters['search'] = search
        
        # 查询报告列表
        reports, total = await service.get_reports_by_filters(filters, page, page_size)
        
        # 构建响应数据
        response_data = []
        for report in reports:
            response_data.append(TestReportResponse(
                id=report.id,
                name=report.name,
                description=report.description,
                report_type=report.report_type,
                project_id=report.project_id,
                template_id=report.template_id,
                report_config=report.report_config,
                include_sections=report.include_sections,
                date_range=report.date_range,
                export_formats=report.export_formats,
                file_paths=report.file_paths,
                file_size=report.file_size,
                status=report.status,
                generation_time=report.generation_time,
                error_message=report.error_message,
                view_count=report.view_count,
                download_count=report.download_count,
                created_by=report.created_by,
                created_at=report.created_at,
                updated_at=report.updated_at
            ))
        
        return PaginatedResponse(
            success=True,
            message="获取测试报告列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取测试报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/{report_id:int}", response_model=BaseResponse[bool])
async def delete_report(
    report_id: int = Path(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除测试报告
    
    删除指定的测试报告及其文件。
    """
    try:
        service = TestReportService(db)
        
        # 删除报告
        result = await service.delete_report(report_id, current_user.id)
        
        return BaseResponse(
            success=True,
            message="测试报告删除成功",
            data=result
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 报告模板管理
@router.post("/templates", response_model=BaseResponse[ReportTemplateResponse])
async def create_report_template(
    request: CreateReportTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建报告模板
    
    创建新的报告模板。
    """
    try:
        service = TestReportService(db)
        
        # 转换请求数据
        template_data = request.dict()
        template_data['created_by'] = current_user.id
        
        # 创建模板
        template = await service.create_report_template(template_data)
        
        # 构建响应
        response_data = ReportTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            template_type=template.template_type,
            template_content=template.template_content,
            default_config=template.default_config,
            is_active=template.is_active,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="报告模板创建成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"创建报告模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/templates", response_model=PaginatedResponse[ReportTemplateResponse])
async def list_report_templates(
    template_type: Optional[str] = Query(None, description="模板类型"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取报告模板列表
    
    获取可用的报告模板列表。
    """
    try:
        service = TestReportService(db)
        
        # 构建过滤条件
        filters = {}
        if template_type:
            filters['template_type'] = template_type
        if is_active is not None:
            filters['is_active'] = is_active
        
        # 查询模板列表
        templates, total = await service.get_report_templates(filters, page, page_size)
        
        # 构建响应数据
        response_data = []
        for template in templates:
            response_data.append(ReportTemplateResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                template_type=template.template_type,
                template_content=template.template_content,
                default_config=template.default_config,
                is_active=template.is_active,
                created_by=template.created_by,
                created_at=template.created_at,
                updated_at=template.updated_at
            ))
        
        return PaginatedResponse(
            success=True,
            message="获取报告模板列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取报告模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.put("/templates/{template_id}", response_model=BaseResponse[ReportTemplateResponse])
async def update_report_template(
    template_id: int = Path(..., description="模板ID"),
    request: UpdateReportTemplateRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新报告模板
    
    更新报告模板的配置和内容。
    """
    try:
        service = TestReportService(db)
        
        # 转换请求数据，过滤None值
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        # 更新模板
        template = await service.update_report_template(template_id, update_data, current_user.id)
        
        # 构建响应
        response_data = ReportTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            template_type=template.template_type,
            template_content=template.template_content,
            default_config=template.default_config,
            is_active=template.is_active,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="报告模板更新成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"更新报告模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 报告调度管理
@router.post("/schedules", response_model=BaseResponse[ReportScheduleResponse])
async def create_report_schedule(
    request: CreateReportScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建报告调度
    
    创建定时生成报告的调度任务。
    """
    try:
        service = TestReportService(db)
        
        # 转换请求数据
        schedule_data = request.dict()
        schedule_data['created_by'] = current_user.id
        
        # 创建调度
        schedule = await service.create_report_schedule(schedule_data)
        
        # 构建响应
        response_data = ReportScheduleResponse(
            id=schedule.id,
            name=schedule.name,
            description=schedule.description,
            report_config=schedule.report_config,
            template_id=schedule.template_id,
            schedule_type=schedule.schedule_type,
            schedule_expression=schedule.schedule_expression,
            timezone=schedule.timezone,
            recipients=schedule.recipients,
            notification_config=schedule.notification_config,
            is_active=schedule.is_active,
            last_run_time=schedule.last_run_time,
            next_run_time=schedule.next_run_time,
            run_count=schedule.run_count,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="报告调度创建成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"创建报告调度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/schedules", response_model=PaginatedResponse[ReportScheduleResponse])
async def list_report_schedules(
    is_active: Optional[bool] = Query(None, description="是否激活"),
    schedule_type: Optional[str] = Query(None, description="调度类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取报告调度列表
    
    获取报告调度任务列表。
    """
    try:
        service = TestReportService(db)
        
        # 构建过滤条件
        filters = {}
        if is_active is not None:
            filters['is_active'] = is_active
        if schedule_type:
            filters['schedule_type'] = schedule_type
        
        # 查询调度列表
        schedules, total = await service.get_report_schedules(filters, page, page_size)
        
        # 构建响应数据
        response_data = []
        for schedule in schedules:
            response_data.append(ReportScheduleResponse(
                id=schedule.id,
                name=schedule.name,
                description=schedule.description,
                report_config=schedule.report_config,
                template_id=schedule.template_id,
                schedule_type=schedule.schedule_type,
                schedule_expression=schedule.schedule_expression,
                timezone=schedule.timezone,
                recipients=schedule.recipients,
                notification_config=schedule.notification_config,
                is_active=schedule.is_active,
                last_run_time=schedule.last_run_time,
                next_run_time=schedule.next_run_time,
                run_count=schedule.run_count,
                created_by=schedule.created_by,
                created_at=schedule.created_at,
                updated_at=schedule.updated_at
            ))
        
        return PaginatedResponse(
            success=True,
            message="获取报告调度列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取报告调度列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 报告分享
@router.post("/share", response_model=BaseResponse[ReportShareResponse])
async def share_report(
    request: ShareReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    分享测试报告
    
    创建报告分享链接。
    """
    try:
        service = TestReportService(db)
        
        # 转换请求数据
        share_data = request.dict()
        share_data['created_by'] = current_user.id
        
        # 创建分享
        share = await service.create_report_share(share_data)
        
        # 构建响应
        response_data = ReportShareResponse(
            id=share.id,
            report_id=share.report_id,
            share_token=share.share_token,
            share_type=share.share_type,
            password_protected=share.password_protected,
            max_access_count=share.max_access_count,
            access_count=share.access_count,
            expires_at=share.expires_at,
            allowed_users=share.allowed_users,
            allowed_roles=share.allowed_roles,
            created_by=share.created_by,
            created_at=share.created_at,
            updated_at=share.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="报告分享创建成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"分享测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# Allure报告集成API
@router.post("/allure/generate", response_model=BaseResponse[AllureReportResponse])
async def generate_allure_report(
    request: GenerateAllureReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成Allure测试报告
    
    根据测试执行结果生成美观的Allure HTML报告。
    """
    try:
        allure_manager = get_allure_manager()
        service = TestReportService(db)
        
        # 获取测试执行数据
        test_executions_data = []
        for execution_id in request.test_execution_ids:
            execution = await get_test_execution_by_id(db, execution_id)
            if execution:
                # 转换为TestExecutionData格式
                execution_data = TestExecutionData(
                    test_case_id=str(execution.test_case_id),
                    test_name=f"Test Case {execution.test_case_id}",
                    status=execution.execution_status.value if execution.execution_status else "UNKNOWN",
                    start_time=execution.started_at or datetime.now(),
                    end_time=execution.completed_at or datetime.now(),
                    description=execution.execution_notes,
                    error_message=execution.failure_reason,
                    error_trace=execution.failure_reason,
                    project_id=request.project_id,
                    test_plan_id=request.test_plan_id,
                    environment=request.environment or execution.test_environment
                )
                test_executions_data.append(execution_data)
        
        if not test_executions_data:
            raise HTTPException(status_code=400, detail="没有找到有效的测试执行数据")
        
        # 生成Allure报告
        report_result = await allure_manager.create_report_from_test_executions(
            test_executions=test_executions_data,
            report_name=request.report_name,
            project_id=request.project_id,
            suite_name=request.suite_name
        )
        
        # 如果需要自动启动服务
        if request.auto_serve:
            background_tasks.add_task(
                allure_manager.serve_report,
                report_result.report_id,
                request.serve_port
            )
        
        # 构建响应
        response_data = AllureReportResponse(
            report_id=report_result.report_id,
            report_name=request.report_name,
            report_path=report_result.report_path,
            report_url=report_result.report_url,
            status=report_result.status,
            generation_time=report_result.generation_time,
            file_size=report_result.file_size,
            test_count=report_result.test_count,
            passed_count=report_result.passed_count,
            failed_count=report_result.failed_count,
            skipped_count=report_result.skipped_count,
            error_message=report_result.error_message
        )
        
        return BaseResponse(
            success=True,
            message="Allure报告生成成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"生成Allure报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成Allure报告失败: {str(e)}")


@router.post("/allure/generate-from-data", response_model=BaseResponse[AllureReportResponse])
async def generate_allure_report_from_data(
    report_name: str = Body(..., description="报告名称"),
    test_executions: List[TestExecutionRequest] = Body(..., description="测试执行数据"),
    project_id: Optional[int] = Body(None, description="项目ID"),
    suite_name: Optional[str] = Body(None, description="测试套件名称"),
    auto_serve: bool = Body(False, description="是否自动启动服务"),
    serve_port: Optional[int] = Body(None, description="服务端口"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从测试数据生成Allure报告
    
    直接从提供的测试执行数据生成Allure报告。
    """
    try:
        allure_manager = get_allure_manager()
        
        # 转换测试执行数据
        test_executions_data = []
        for execution in test_executions:
            execution_data = TestExecutionData(
                test_case_id=execution.test_case_id,
                test_name=execution.test_name,
                status=execution.status,
                start_time=execution.start_time,
                end_time=execution.end_time,
                description=execution.description,
                error_message=execution.error_message,
                error_trace=execution.error_trace,
                attachments=execution.attachments,
                steps=execution.steps,
                labels=execution.labels,
                links=execution.links,
                project_id=project_id,
                environment=execution.environment
            )
            test_executions_data.append(execution_data)
        
        # 生成Allure报告
        report_result = await allure_manager.create_report_from_test_executions(
            test_executions=test_executions_data,
            report_name=report_name,
            project_id=project_id,
            suite_name=suite_name
        )
        
        # 如果需要自动启动服务
        if auto_serve:
            try:
                service_url = await allure_manager.serve_report(
                    report_result.report_id,
                    serve_port
                )
                report_result.report_url = service_url
            except Exception as e:
                logger.warning(f"启动Allure服务失败: {str(e)}")
        
        # 构建响应
        response_data = AllureReportResponse(
            report_id=report_result.report_id,
            report_name=report_name,
            report_path=report_result.report_path,
            report_url=report_result.report_url,
            status=report_result.status,
            generation_time=report_result.generation_time,
            file_size=report_result.file_size,
            test_count=report_result.test_count,
            passed_count=report_result.passed_count,
            failed_count=report_result.failed_count,
            skipped_count=report_result.skipped_count,
            error_message=report_result.error_message
        )
        
        return BaseResponse(
            success=True,
            message="Allure报告生成成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"生成Allure报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成Allure报告失败: {str(e)}")


@router.get("/allure", response_model=BaseResponse[List[AllureReportResponse]])
async def list_allure_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取Allure报告列表

    获取所有可用的Allure报告列表。
    """
    try:
        allure_manager = get_allure_manager()
        reports = allure_manager.list_reports()

        response_data = []
        for report in reports:
            response_data.append(AllureReportResponse(
                report_id=report.report_id,
                report_name="Allure Report",
                report_path=report.report_path,
                report_url=report.report_url,
                status=report.status,
                generation_time=report.generation_time,
                file_size=report.file_size,
                test_count=report.test_count,
                passed_count=report.passed_count,
                failed_count=report.failed_count,
                skipped_count=report.skipped_count,
                error_message=report.error_message
            ))

        return BaseResponse(
            success=True,
            message="获取Allure报告列表成功",
            data=response_data
        )

    except Exception as e:
        logger.error(f"获取Allure报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Allure报告列表失败: {str(e)}")


@router.post("/allure/demo", response_model=BaseResponse[AllureReportResponse])
async def generate_demo_allure_report_static(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await generate_demo_allure_report(current_user=current_user, db=db)


@router.get("/allure/{report_id}", response_model=BaseResponse[AllureReportResponse])
async def get_allure_report(
    report_id: str = Path(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取Allure报告信息
    
    根据报告ID获取Allure报告的详细信息。
    """
    try:
        allure_manager = get_allure_manager()
        
        # 获取报告信息
        report_result = allure_manager.get_report_info(report_id)
        if not report_result:
            raise HTTPException(status_code=404, detail="Allure报告不存在")
        
        # 构建响应
        response_data = AllureReportResponse(
            report_id=report_result.report_id,
            report_name="Allure Report",  # 可以从存储中获取实际名称
            report_path=report_result.report_path,
            report_url=report_result.report_url,
            status=report_result.status,
            generation_time=report_result.generation_time,
            file_size=report_result.file_size,
            test_count=report_result.test_count,
            passed_count=report_result.passed_count,
            failed_count=report_result.failed_count,
            skipped_count=report_result.skipped_count,
            error_message=report_result.error_message
        )
        
        return BaseResponse(
            success=True,
            message="获取Allure报告信息成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取Allure报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/allure/{report_id}/serve", response_model=BaseResponse[Dict[str, str]])
async def serve_allure_report(
    report_id: str = Path(..., description="报告ID"),
    port: Optional[int] = Body(None, description="服务端口"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    启动Allure报告服务
    
    为指定的Allure报告启动HTTP服务。
    """
    try:
        allure_manager = get_allure_manager()
        
        # 启动报告服务
        service_url = await allure_manager.serve_report(report_id, port)
        
        return BaseResponse(
            success=True,
            message="Allure报告服务启动成功",
            data={"service_url": service_url}
        )
        
    except Exception as e:
        logger.error(f"启动Allure报告服务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动Allure报告服务失败: {str(e)}")


@router.get("/allure", response_model=BaseResponse[List[AllureReportResponse]])
async def list_allure_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取Allure报告列表
    
    获取所有可用的Allure报告列表。
    """
    try:
        allure_manager = get_allure_manager()
        
        # 获取报告列表
        reports = allure_manager.list_reports()
        
        # 构建响应数据
        response_data = []
        for report in reports:
            response_data.append(AllureReportResponse(
                report_id=report.report_id,
                report_name="Allure Report",
                report_path=report.report_path,
                report_url=report.report_url,
                status=report.status,
                generation_time=report.generation_time,
                file_size=report.file_size,
                test_count=report.test_count,
                passed_count=report.passed_count,
                failed_count=report.failed_count,
                skipped_count=report.skipped_count,
                error_message=report.error_message
            ))
        
        return BaseResponse(
            success=True,
            message="获取Allure报告列表成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取Allure报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/allure/{report_id}", response_model=BaseResponse[bool])
async def delete_allure_report(
    report_id: str = Path(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除Allure报告
    
    删除指定的Allure报告及其文件。
    """
    try:
        allure_manager = get_allure_manager()
        
        # 删除报告
        result = await allure_manager.delete_report(report_id)
        
        return BaseResponse(
            success=True,
            message="Allure报告删除成功",
            data=result
        )
        
    except Exception as e:
        logger.error(f"删除Allure报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/allure/demo", response_model=BaseResponse[AllureReportResponse])
async def generate_demo_allure_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成演示Allure报告
    
    生成包含示例测试数据的Allure报告，用于演示功能。
    """
    try:
        allure_manager = get_allure_manager()
        
        # 创建示例测试数据
        sample_data = allure_manager.create_sample_test_data()
        
        # 生成演示报告
        report_result = await allure_manager.create_report_from_test_executions(
            test_executions=sample_data,
            report_name="演示报告",
            suite_name="功能测试套件"
        )
        
        # 构建响应
        response_data = AllureReportResponse(
            report_id=report_result.report_id,
            report_name="演示报告",
            report_path=report_result.report_path,
            report_url=report_result.report_url,
            status=report_result.status,
            generation_time=report_result.generation_time,
            file_size=report_result.file_size,
            test_count=report_result.test_count,
            passed_count=report_result.passed_count,
            failed_count=report_result.failed_count,
            skipped_count=report_result.skipped_count,
            error_message=report_result.error_message
        )
        
        return BaseResponse(
            success=True,
            message="演示Allure报告生成成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"生成演示Allure报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成演示Allure报告失败: {str(e)}")


@router.get("/analytics/summary", response_model=BaseResponse[ReportAnalyticsResponse])
async def get_report_analytics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取报告分析数据
    
    获取报告使用情况的统计分析。
    """
    try:
        analysis_service = TestDataAnalysisService(db)
        
        # 构建分析条件
        filters = {}
        if project_id:
            filters['project_id'] = project_id
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        # 获取报告分析
        analytics = await analysis_service.get_report_analytics(filters)
        
        # 构建响应
        response_data = ReportAnalyticsResponse(
            total_reports=analytics.total_reports,
            reports_by_type=analytics.reports_by_type,
            reports_by_status=analytics.reports_by_status,
            generation_time_avg=analytics.generation_time_avg,
            most_viewed_reports=analytics.most_viewed_reports,
            most_downloaded_reports=analytics.most_downloaded_reports,
            report_trends=analytics.report_trends
        )
        
        return BaseResponse(
            success=True,
            message="获取报告分析数据成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取报告分析数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
