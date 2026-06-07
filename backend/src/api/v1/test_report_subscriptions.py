"""
测试报告订阅和分发API接口

本模块实现了测试报告订阅和分发的RESTful API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.user import User
from ...schemas.test_report_subscription import (
    TestReportSubscriptionRequest, TestReportSubscriptionResponse, TestReportSubscriptionUpdate,
    TestReportDistributionRequest, TestReportDistributionResponse,
    TestReportVersionRequest, TestReportVersionResponse,
    SubscriptionListRequest, SubscriptionListResponse,
    DistributionListRequest, DistributionListResponse,
    DistributionStatistics, SubscriptionStatistics
)
from ...services.test_report_distribution_service import TestReportDistributionService
from ...utils.redis_client import RedisClient
from ...services.email_service import EmailService, EmailConfig
from ...services.webhook_service import WebhookService, WebhookConfig

router = APIRouter(prefix="/test-report-subscriptions", tags=["测试报告订阅"])

# 依赖注入
def get_distribution_service(db: Session = Depends(get_db)) -> TestReportDistributionService:
    """获取分发服务实例"""
    redis_client = RedisClient()
    
    # 邮件服务配置（实际应该从配置文件读取）
    email_config = EmailConfig(
        smtp_server="smtp.example.com",
        smtp_port=587,
        username="noreply@example.com",
        password="password",
        use_tls=True,
        from_name="测试管理系统"
    )
    email_service = EmailService(email_config)
    
    # Webhook服务配置
    webhook_config = WebhookConfig(timeout=30, max_retries=3)
    webhook_service = WebhookService(webhook_config)
    
    return TestReportDistributionService(db, redis_client, email_service, webhook_service)

# 订阅管理接口
@router.post("/", response_model=TestReportSubscriptionResponse, summary="创建报告订阅")
async def create_subscription(
    subscription_request: TestReportSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    创建测试报告订阅
    
    - **name**: 订阅名称
    - **subscription_type**: 订阅类型
    - **delivery_channels**: 分发渠道列表
    - **project_ids**: 项目ID列表（可选）
    - **report_types**: 报告类型列表（可选）
    - **email_recipients**: 邮件接收人列表（邮件渠道必需）
    - **webhook_url**: Webhook URL（Webhook渠道必需）
    """
    try:
        return await service.create_subscription(subscription_request, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=SubscriptionListResponse, summary="获取订阅列表")
async def get_subscriptions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """获取当前用户的订阅列表"""
    try:
        result = await service.get_user_subscriptions(current_user.id, page, page_size)
        return SubscriptionListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{subscription_id}", response_model=TestReportSubscriptionResponse, summary="获取订阅详情")
async def get_subscription(
    subscription_id: int = Path(..., description="订阅ID"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """获取指定订阅的详细信息"""
    try:
        # 这里需要在service中添加get_subscription_by_id方法
        # 暂时返回错误
        raise HTTPException(status_code=501, detail="功能待实现")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{subscription_id}", response_model=TestReportSubscriptionResponse, summary="更新订阅")
async def update_subscription(
    subscription_id: int = Path(..., description="订阅ID"),
    subscription_update: TestReportSubscriptionUpdate = None,
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    更新测试报告订阅
    
    - 只能更新自己创建的订阅
    - 可以部分更新字段
    """
    try:
        return await service.update_subscription(subscription_id, subscription_update, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{subscription_id}", summary="删除订阅")
async def delete_subscription(
    subscription_id: int = Path(..., description="订阅ID"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    删除测试报告订阅
    
    - 只能删除自己创建的订阅
    - 删除后相关的分发记录也会被删除
    """
    try:
        await service.delete_subscription(subscription_id, current_user.id)
        return {"message": "订阅删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 报告分发接口
@router.post("/distribute", response_model=List[TestReportDistributionResponse], summary="分发报告")
async def distribute_report(
    distribution_request: TestReportDistributionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    手动分发测试报告
    
    - **report_id**: 要分发的报告ID
    - **delivery_channel**: 分发渠道
    - **recipients**: 接收人列表
    - **scheduled_at**: 计划分发时间（可选，默认立即发送）
    """
    try:
        return await service.distribute_report(distribution_request, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reports/{report_id}/auto-distribute", summary="自动分发报告")
async def auto_distribute_report(
    background_tasks: BackgroundTasks,
    report_id: int = Path(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    根据订阅规则自动分发报告
    
    - 系统会查找匹配的订阅并自动创建分发任务
    - 分发任务在后台异步执行
    """
    try:
        # 在后台任务中执行自动分发
        background_tasks.add_task(service.auto_distribute_report, report_id)
        return {"message": "自动分发任务已启动"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/distributions/", response_model=DistributionListResponse, summary="获取分发记录")
async def get_distributions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    subscription_id: Optional[int] = Query(None, description="订阅ID筛选"),
    report_id: Optional[int] = Query(None, description="报告ID筛选"),
    delivery_channel: Optional[str] = Query(None, description="分发渠道筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """获取分发记录列表"""
    try:
        # 这里需要在service中添加get_distributions方法
        # 暂时返回空结果
        return DistributionListResponse(
            distributions=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 版本管理接口
@router.post("/reports/{report_id}/versions", response_model=TestReportVersionResponse, summary="创建报告版本")
async def create_report_version(
    report_id: int = Path(..., description="报告ID"),
    version_request: TestReportVersionRequest = None,
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    创建测试报告版本
    
    - **version_number**: 版本号
    - **version_name**: 版本名称（可选）
    - **description**: 版本描述（可选）
    - **change_log**: 变更日志（可选）
    - **access_level**: 访问级别（private/internal/public）
    """
    try:
        # 设置报告ID
        version_request.report_id = report_id
        return await service.create_report_version(version_request, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports/{report_id}/versions", response_model=List[TestReportVersionResponse], summary="获取报告版本列表")
async def get_report_versions(
    report_id: int = Path(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """获取指定报告的版本列表"""
    try:
        return await service.get_report_versions(report_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/versions/{version1_id}/compare/{version2_id}", summary="比较报告版本")
async def compare_report_versions(
    version1_id: int = Path(..., description="版本1 ID"),
    version2_id: int = Path(..., description="版本2 ID"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    比较两个报告版本的差异
    
    - 返回版本间的详细对比信息
    - 包括文件大小、哈希值、访问级别等变化
    """
    try:
        return await service.compare_report_versions(version1_id, version2_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 访问控制接口
@router.post("/reports/{report_id}/access-log", summary="记录报告访问")
async def log_report_access(
    report_id: int = Path(..., description="报告ID"),
    version_id: Optional[int] = Query(None, description="版本ID"),
    access_type: str = Query(..., description="访问类型"),
    access_method: Optional[str] = Query(None, description="访问方式"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """记录报告访问日志"""
    try:
        success = await service.log_report_access(
            report_id=report_id,
            version_id=version_id,
            user_id=current_user.id,
            access_type=access_type,
            access_method=access_method
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports/{report_id}/access-check", summary="检查报告访问权限")
async def check_report_access(
    report_id: int = Path(..., description="报告ID"),
    version_id: Optional[int] = Query(None, description="版本ID"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """检查当前用户是否有权限访问指定报告"""
    try:
        has_access = await service.check_report_access_permission(
            report_id=report_id,
            version_id=version_id,
            user_id=current_user.id
        )
        return {"has_access": has_access}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 统计分析接口
@router.get("/statistics/distributions", response_model=DistributionStatistics, summary="获取分发统计")
async def get_distribution_statistics(
    project_id: Optional[int] = Query(None, description="项目ID筛选"),
    time_range: str = Query("30d", description="时间范围"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    获取报告分发统计信息
    
    - **project_id**: 项目ID筛选（可选）
    - **time_range**: 时间范围（7d/30d/90d）
    """
    try:
        return await service.get_distribution_statistics(project_id, time_range)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/statistics/subscriptions", response_model=SubscriptionStatistics, summary="获取订阅统计")
async def get_subscription_statistics(
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """获取当前用户的订阅统计信息"""
    try:
        return await service.get_subscription_statistics(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 管理接口
@router.post("/process-scheduled", summary="处理定时分发任务")
async def process_scheduled_distributions(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """
    处理定时分发任务（管理员接口）
    
    - 检查并处理所有到期的定时分发任务
    - 通常由定时任务调用
    """
    try:
        # 检查管理员权限（简化实现）
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        # 在后台任务中处理
        background_tasks.add_task(service.process_scheduled_distributions)
        return {"message": "定时分发任务处理已启动"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/test-email", summary="测试邮件服务")
async def test_email_service(
    test_email: str = Query(..., description="测试邮箱地址"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """测试邮件服务连接和发送功能"""
    try:
        # 发送测试邮件
        success = await service.email_service.send_email(
            to=[test_email],
            subject="测试邮件 - 测试管理系统",
            body="这是一封测试邮件，用于验证邮件服务配置是否正确。",
            is_html=False
        )
        
        return {
            "success": success,
            "message": "测试邮件发送成功" if success else "测试邮件发送失败"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/test-webhook", summary="测试Webhook服务")
async def test_webhook_service(
    webhook_url: str = Query(..., description="Webhook URL"),
    current_user: User = Depends(get_current_user),
    service: TestReportDistributionService = Depends(get_distribution_service)
):
    """测试Webhook服务连接和发送功能"""
    try:
        result = await service.webhook_service.test_webhook(webhook_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))