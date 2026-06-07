"""
缺陷管理API接口

本模块实现缺陷管理相关的RESTful API接口，包括：
- 缺陷的CRUD操作和状态流转
- 缺陷分析和统计API
- 缺陷搜索和过滤功能
- 缺陷协作和通知功能
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, UploadFile, File, Response
from fastapi.security import HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ...services.defect_service import DefectService
from ...services.defect_analysis_service import DefectAnalysisService
from ...services.defect_trend_service import DefectTrendService
from ...services.defect_notification_service import DefectNotificationService
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...models.test_case import Defect, DefectType, DefectSeverity, DefectStatus, DefectResolution, TestCasePriority, TestCase, TestExecution
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/defects", tags=["缺陷管理"])
security = HTTPBearer()


def _is_missing_table_error(error: Exception) -> bool:
    text = str(error).lower()
    return "doesn't exist" in text or "no such table" in text


def _build_defect_response(defect):
    return DefectResponse(
        id=defect.id,
        defect_code=defect.defect_code,
        test_execution_id=defect.test_execution_id,
        test_case_id=defect.test_case_id,
        requirement_id=defect.requirement_id,
        title=defect.title,
        description=defect.description,
        steps_to_reproduce=defect.steps_to_reproduce,
        defect_type=defect.defect_type,
        severity=defect.severity,
        priority=defect.priority,
        status=defect.status,
        resolution=defect.resolution,
        found_in_version=defect.found_in_version,
        fixed_in_version=defect.fixed_in_version,
        test_environment=defect.test_environment,
        reporter_id=defect.reporter_id,
        assignee_id=defect.assignee_id,
        resolver_id=defect.resolver_id,
        reported_at=defect.reported_at,
        assigned_at=defect.assigned_at,
        resolved_at=defect.resolved_at,
        verified_at=defect.verified_at,
        attachments=defect.attachments,
        created_at=defect.created_at,
        updated_at=defect.updated_at
    )


def _generate_defect_code(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(Defect).filter(Defect.defect_code.like(f"BUG-{today}-%")).count()
    return f"BUG-{today}-{count + 1:04d}"


# 请求模式
class CreateDefectRequest(BaseModel):
    """创建缺陷请求"""
    test_execution_id: Optional[int] = Field(None, description="关联测试执行ID")
    test_case_id: Optional[int] = Field(None, description="关联测试用例ID")
    requirement_id: Optional[int] = Field(None, description="关联需求ID")
    title: str = Field(..., min_length=1, max_length=200, description="缺陷标题")
    description: str = Field(..., min_length=1, description="缺陷描述")
    steps_to_reproduce: Optional[str] = Field(None, description="重现步骤")
    defect_type: DefectType = Field(..., description="缺陷类型")
    severity: DefectSeverity = Field(..., description="严重程度")
    priority: TestCasePriority = Field(..., description="优先级")
    found_in_version: Optional[str] = Field(None, description="发现版本")
    test_environment: Optional[str] = Field(None, description="测试环境")
    assignee_id: Optional[int] = Field(None, description="分配人ID")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


class UpdateDefectRequest(BaseModel):
    """更新缺陷请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="缺陷标题")
    description: Optional[str] = Field(None, min_length=1, description="缺陷描述")
    steps_to_reproduce: Optional[str] = Field(None, description="重现步骤")
    defect_type: Optional[DefectType] = Field(None, description="缺陷类型")
    severity: Optional[DefectSeverity] = Field(None, description="严重程度")
    priority: Optional[TestCasePriority] = Field(None, description="优先级")
    found_in_version: Optional[str] = Field(None, description="发现版本")
    fixed_in_version: Optional[str] = Field(None, description="修复版本")
    test_environment: Optional[str] = Field(None, description="测试环境")
    assignee_id: Optional[int] = Field(None, description="分配人ID")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


class UpdateDefectStatusRequest(BaseModel):
    """更新缺陷状态请求"""
    status: DefectStatus = Field(..., description="新状态")
    resolution: Optional[DefectResolution] = Field(None, description="解决方案")
    notes: Optional[str] = Field(None, description="状态变更备注")
    fixed_in_version: Optional[str] = Field(None, description="修复版本")


class BatchUpdateDefectsRequest(BaseModel):
    """批量更新缺陷请求"""
    defect_ids: List[int] = Field(..., description="缺陷ID列表")
    update_data: UpdateDefectRequest = Field(..., description="更新数据")


class DefectCommentRequest(BaseModel):
    """缺陷评论请求"""
    content: str = Field(..., min_length=1, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论ID")


class DefectQueryParams(BaseModel):
    """缺陷查询参数"""
    test_execution_id: Optional[int] = Field(None, description="测试执行ID")
    test_case_id: Optional[int] = Field(None, description="测试用例ID")
    requirement_id: Optional[int] = Field(None, description="需求ID")
    defect_type: Optional[DefectType] = Field(None, description="缺陷类型")
    severity: Optional[DefectSeverity] = Field(None, description="严重程度")
    priority: Optional[TestCasePriority] = Field(None, description="优先级")
    status: Optional[DefectStatus] = Field(None, description="缺陷状态")
    reporter_id: Optional[int] = Field(None, description="报告人ID")
    assignee_id: Optional[int] = Field(None, description="分配人ID")
    resolver_id: Optional[int] = Field(None, description="解决人ID")
    found_in_version: Optional[str] = Field(None, description="发现版本")
    fixed_in_version: Optional[str] = Field(None, description="修复版本")
    search: Optional[str] = Field(None, description="搜索关键词")


# 响应模式
class DefectResponse(BaseModel):
    """缺陷响应"""
    id: int = Field(..., description="缺陷ID")
    defect_code: str = Field(..., description="缺陷编码")
    test_execution_id: Optional[int] = Field(None, description="关联测试执行ID")
    test_case_id: Optional[int] = Field(None, description="关联测试用例ID")
    requirement_id: Optional[int] = Field(None, description="关联需求ID")
    title: str = Field(..., description="缺陷标题")
    description: str = Field(..., description="缺陷描述")
    steps_to_reproduce: Optional[str] = Field(None, description="重现步骤")
    defect_type: DefectType = Field(..., description="缺陷类型")
    severity: DefectSeverity = Field(..., description="严重程度")
    priority: TestCasePriority = Field(..., description="优先级")
    status: DefectStatus = Field(..., description="缺陷状态")
    resolution: Optional[DefectResolution] = Field(None, description="解决方案")
    found_in_version: Optional[str] = Field(None, description="发现版本")
    fixed_in_version: Optional[str] = Field(None, description="修复版本")
    test_environment: Optional[str] = Field(None, description="测试环境")
    reporter_id: int = Field(..., description="报告人ID")
    assignee_id: Optional[int] = Field(None, description="分配人ID")
    resolver_id: Optional[int] = Field(None, description="解决人ID")
    reported_at: datetime = Field(..., description="报告时间")
    assigned_at: Optional[datetime] = Field(None, description="分配时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    verified_at: Optional[datetime] = Field(None, description="验证时间")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class DefectCommentResponse(BaseModel):
    """缺陷评论响应"""
    id: int = Field(..., description="评论ID")
    defect_id: int = Field(..., description="缺陷ID")
    user_id: int = Field(..., description="用户ID")
    content: str = Field(..., description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class DefectStatisticsResponse(BaseModel):
    """缺陷统计响应"""
    total_defects: int = Field(..., description="总缺陷数")
    defects_by_severity: Dict[str, int] = Field(..., description="按严重程度分布")
    defects_by_type: Dict[str, int] = Field(..., description="按类型分布")
    defects_by_status: Dict[str, int] = Field(..., description="按状态分布")
    defects_by_module: Dict[str, int] = Field(..., description="按模块分布")
    resolution_time_avg: Optional[float] = Field(None, description="平均解决时间")
    defect_density: Optional[float] = Field(None, description="缺陷密度")
    escape_rate: Optional[float] = Field(None, description="缺陷逃逸率")


class DefectTrendResponse(BaseModel):
    """缺陷趋势响应"""
    project_id: int = Field(..., description="项目ID")
    time_range: str = Field(..., description="时间范围")
    trend_data: DefectStatisticsResponse = Field(..., description="趋势数据")
    predictions: Optional[Dict[str, Any]] = Field(None, description="趋势预测")
    suggestions: Optional[List[str]] = Field(None, description="改进建议")
    generated_at: str = Field(..., description="生成时间")


# API接口实现
@router.post("/", response_model=BaseResponse[DefectResponse])
async def create_defect(
    request: CreateDefectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建缺陷
    
    创建新的缺陷记录，支持AI辅助分类和智能分配。
    """
    try:
        now = datetime.utcnow()
        defect = Defect(
            defect_code=_generate_defect_code(db),
            test_execution_id=request.test_execution_id,
            test_case_id=request.test_case_id,
            requirement_id=request.requirement_id,
            title=request.title,
            description=request.description,
            steps_to_reproduce=request.steps_to_reproduce,
            defect_type=request.defect_type,
            severity=request.severity,
            priority=request.priority,
            found_in_version=request.found_in_version,
            test_environment=request.test_environment,
            reporter_id=current_user.id,
            assignee_id=request.assignee_id,
            assigned_at=now if request.assignee_id else None,
            attachments=request.attachments,
            status=DefectStatus.ASSIGNED if request.assignee_id else DefectStatus.NEW
        )
        db.add(defect)
        db.commit()
        db.refresh(defect)
        
        return BaseResponse(
            success=True,
            message="缺陷创建成功",
            data=_build_defect_response(defect)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"创建缺陷失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/statistics", response_model=BaseResponse[Dict[str, Any]])
async def get_defect_statistics_alias(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取缺陷统计信息（兼容前端旧路径，使用真实数据库统计）。"""
    try:
        total = db.query(Defect).count()
        status_counts = {
            status.value: db.query(Defect).filter(Defect.status == status).count()
            for status in DefectStatus
        }
        severity_counts = {
            severity.value: db.query(Defect).filter(Defect.severity == severity).count()
            for severity in DefectSeverity
        }
        type_counts = {
            defect_type.value: db.query(Defect).filter(Defect.defect_type == defect_type).count()
            for defect_type in DefectType
        }

        new_count = status_counts.get(DefectStatus.NEW.value, 0)
        resolved = sum(status_counts.get(status.value, 0) for status in [DefectStatus.RESOLVED, DefectStatus.VERIFIED, DefectStatus.CLOSED])
        critical = severity_counts.get(DefectSeverity.CRITICAL.value, 0)
        high = severity_counts.get(DefectSeverity.HIGH.value, 0)
        resolution_rate = round(resolved / total * 100, 1) if total else 0
        resolved_rows = db.query(Defect).filter(
            Defect.resolved_at.isnot(None),
            Defect.reported_at.isnot(None)
        ).all()
        avg_resolution_time = 0
        if resolved_rows:
            total_seconds = sum((row.resolved_at - row.reported_at).total_seconds() for row in resolved_rows)
            avg_resolution_time = round(total_seconds / len(resolved_rows) / 86400, 1)
    except Exception as e:
        if not _is_missing_table_error(e):
            raise
        total = new_count = resolved = critical = high = resolution_rate = avg_resolution_time = 0
        status_counts = {status.value: 0 for status in DefectStatus}
        severity_counts = {severity.value: 0 for severity in DefectSeverity}
        type_counts = {defect_type.value: 0 for defect_type in DefectType}
    return BaseResponse(
        success=True,
        message="获取缺陷统计成功",
        data={
            "total_defects": total,
            "new_defects": new_count,
            "resolved_defects": resolved,
            "critical_defects": critical,
            "high_defects": high,
            "medium_defects": severity_counts.get(DefectSeverity.MEDIUM.value, 0),
            "low_defects": severity_counts.get(DefectSeverity.LOW.value, 0),
            "trivial_defects": severity_counts.get(getattr(DefectSeverity, "TRIVIAL").value, 0) if hasattr(DefectSeverity, "TRIVIAL") else 0,
            "resolution_rate": resolution_rate,
            "avg_resolution_time": avg_resolution_time,
            "defect_density": 0,
            "reopen_rate": round(status_counts.get(DefectStatus.REOPENED.value, 0) / total * 100, 1) if total else 0,
            "defects_by_status": status_counts,
            "defects_by_severity": severity_counts,
            "defects_by_type": type_counts
        }
    )


@router.get("/trends", response_model=BaseResponse[List[Dict[str, Any]]])
async def get_defect_trends_alias(
    time_range: str = Query("30d", description="时间范围"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取缺陷趋势（兼容前端旧路径）"""
    days_by_range = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = days_by_range.get(time_range, 30)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        defects = db.query(Defect).filter(Defect.reported_at >= start_datetime).all()
        running_total = db.query(Defect).filter(Defect.reported_at < start_datetime).count()
        trend_rows = []
        for index in range(days):
            current_date = start_date + timedelta(days=index)
            created_today = [
                defect for defect in defects
                if defect.reported_at and defect.reported_at.date() == current_date
            ]
            resolved_today = [
                defect for defect in defects
                if defect.resolved_at and defect.resolved_at.date() == current_date
            ]
            running_total += len(created_today)
            trend_rows.append({
                "date": current_date.isoformat(),
                "new_defects": len(created_today),
                "resolved_defects": len(resolved_today),
                "total_defects": running_total
            })
    except Exception as e:
        if not _is_missing_table_error(e):
            raise
        trend_rows = []

    return BaseResponse(
        success=True,
        message="获取缺陷趋势成功",
        data=trend_rows
    )


@router.get("/export")
async def export_defects(
    status: Optional[DefectStatus] = Query(None, description="缺陷状态"),
    severity: Optional[DefectSeverity] = Query(None, description="严重程度"),
    defect_type: Optional[DefectType] = Query(None, description="缺陷类型"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    format: str = Query("csv", description="导出格式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出缺陷列表为CSV。"""
    query = db.query(Defect)
    if status:
        query = query.filter(Defect.status == status)
    if severity:
        query = query.filter(Defect.severity == severity)
    if defect_type:
        query = query.filter(Defect.defect_type == defect_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter((Defect.title.like(search_term)) | (Defect.defect_code.like(search_term)))

    rows = ["缺陷编号,标题,类型,严重程度,优先级,状态,报告时间"]
    for defect in query.order_by(Defect.reported_at.desc()).all():
        rows.append(",".join([
            defect.defect_code or "",
            (defect.title or "").replace(",", "，"),
            defect.defect_type.value if defect.defect_type else "",
            defect.severity.value if defect.severity else "",
            defect.priority.value if defect.priority else "",
            defect.status.value if defect.status else "",
            defect.reported_at.isoformat() if defect.reported_at else ""
        ]))
    return Response(
        content="\ufeff" + "\n".join(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=defects.{format if format in {'csv', 'txt'} else 'csv'}"}
    )


@router.get("/{defect_id}", response_model=BaseResponse[DefectResponse])
async def get_defect(
    defect_id: int = Path(..., description="缺陷ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取缺陷详情
    
    根据缺陷ID获取详细信息。
    """
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise HTTPException(status_code=404, detail="缺陷不存在")
        
        return BaseResponse(
            success=True,
            message="获取缺陷详情成功",
            data=_build_defect_response(defect)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缺陷详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.put("/{defect_id}", response_model=BaseResponse[DefectResponse])
async def update_defect(
    defect_id: int = Path(..., description="缺陷ID"),
    request: UpdateDefectRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新缺陷
    
    更新缺陷的基本信息。
    """
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise HTTPException(status_code=404, detail="缺陷不存在")

        update_data = {k: v for k, v in request.dict().items() if v is not None}
        for key, value in update_data.items():
            if hasattr(defect, key):
                setattr(defect, key, value)
        defect.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(defect)
        
        return BaseResponse(
            success=True,
            message="缺陷更新成功",
            data=_build_defect_response(defect)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新缺陷失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.put("/{defect_id}/status", response_model=BaseResponse[DefectResponse])
@router.patch("/{defect_id}/status", response_model=BaseResponse[DefectResponse])
async def update_defect_status(
    defect_id: int = Path(..., description="缺陷ID"),
    request: UpdateDefectStatusRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新缺陷状态
    
    更新缺陷的状态，支持状态流转验证。
    """
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise HTTPException(status_code=404, detail="缺陷不存在")

        defect.status = request.status
        if request.resolution:
            defect.resolution = request.resolution
        if request.fixed_in_version:
            defect.fixed_in_version = request.fixed_in_version
        now = datetime.utcnow()
        if request.status == DefectStatus.ASSIGNED:
            defect.assigned_at = defect.assigned_at or now
        elif request.status == DefectStatus.RESOLVED:
            defect.resolved_at = defect.resolved_at or now
            defect.resolver_id = current_user.id
        elif request.status in [DefectStatus.VERIFIED, DefectStatus.CLOSED]:
            defect.verified_at = defect.verified_at or now
        defect.updated_at = now
        db.commit()
        db.refresh(defect)
        
        return BaseResponse(
            success=True,
            message="缺陷状态更新成功",
            data=_build_defect_response(defect)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新缺陷状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/{defect_id}", response_model=BaseResponse[bool])
async def delete_defect(
    defect_id: int = Path(..., description="缺陷ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除缺陷
    
    删除指定的缺陷记录。
    """
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise HTTPException(status_code=404, detail="缺陷不存在")
        if defect.status not in [DefectStatus.NEW, DefectStatus.REJECTED]:
            raise HTTPException(status_code=422, detail="只能删除新建或已拒绝状态的缺陷")

        db.query(Defect).filter(Defect.id == defect_id).delete(synchronize_session=False)
        db.commit()
        
        return BaseResponse(
            success=True,
            message="缺陷删除成功",
            data=True
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除缺陷失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/", response_model=PaginatedResponse[DefectResponse])
async def list_defects(
    test_execution_id: Optional[int] = Query(None, description="测试执行ID"),
    test_case_id: Optional[int] = Query(None, description="测试用例ID"),
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    requirement_id: Optional[int] = Query(None, description="需求ID"),
    defect_type: Optional[DefectType] = Query(None, description="缺陷类型"),
    severity: Optional[DefectSeverity] = Query(None, description="严重程度"),
    priority: Optional[TestCasePriority] = Query(None, description="优先级"),
    status: Optional[DefectStatus] = Query(None, description="缺陷状态"),
    reporter_id: Optional[int] = Query(None, description="报告人ID"),
    assignee_id: Optional[int] = Query(None, description="分配人ID"),
    resolver_id: Optional[int] = Query(None, description="解决人ID"),
    found_in_version: Optional[str] = Query(None, description="发现版本"),
    fixed_in_version: Optional[str] = Query(None, description="修复版本"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取缺陷列表
    
    支持多条件过滤和分页查询。
    """
    try:
        query = db.query(Defect)
        if test_execution_id:
            query = query.filter(Defect.test_execution_id == test_execution_id)
        if test_case_id:
            query = query.filter(Defect.test_case_id == test_case_id)
        if test_plan_id:
            query = (
                query.outerjoin(TestCase, Defect.test_case_id == TestCase.id)
                .outerjoin(TestExecution, Defect.test_execution_id == TestExecution.id)
                .filter(or_(TestCase.test_plan_id == test_plan_id, TestExecution.test_plan_id == test_plan_id))
            )
        if requirement_id:
            query = query.filter(Defect.requirement_id == requirement_id)
        if defect_type:
            query = query.filter(Defect.defect_type == defect_type)
        if severity:
            query = query.filter(Defect.severity == severity)
        if priority:
            query = query.filter(Defect.priority == priority)
        if status:
            query = query.filter(Defect.status == status)
        if reporter_id:
            query = query.filter(Defect.reporter_id == reporter_id)
        if assignee_id:
            query = query.filter(Defect.assignee_id == assignee_id)
        if resolver_id:
            query = query.filter(Defect.resolver_id == resolver_id)
        if found_in_version:
            query = query.filter(Defect.found_in_version == found_in_version)
        if fixed_in_version:
            query = query.filter(Defect.fixed_in_version == fixed_in_version)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Defect.title.like(search_term)) |
                (Defect.description.like(search_term)) |
                (Defect.defect_code.like(search_term))
            )

        total = query.count()
        defects = query.order_by(Defect.reported_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()
        
        # 构建响应数据
        response_data = []
        for defect in defects:
            response_data.append(_build_defect_response(defect))
        
        return PaginatedResponse(
            success=True,
            message="获取缺陷列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        if _is_missing_table_error(e):
            return PaginatedResponse(
                success=True,
                message="缺陷表未初始化，当前无数据",
                data=[],
                total=0,
                page=page,
                page_size=page_size
            )
        logger.error(f"获取缺陷列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/batch-update", response_model=BaseResponse[List[DefectResponse]])
async def batch_update_defects(
    request: BatchUpdateDefectsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量更新缺陷
    
    批量更新多个缺陷的信息。
    """
    try:
        service = DefectService(db)
        
        # 转换更新数据
        update_data = {k: v for k, v in request.update_data.dict().items() if v is not None}
        
        # 批量更新缺陷
        updated_defects = await service.batch_update_defects(request.defect_ids, update_data, current_user.id)
        
        # 构建响应数据
        response_data = []
        for defect in updated_defects:
            response_data.append(DefectResponse(
                id=defect.id,
                defect_code=defect.defect_code,
                test_execution_id=defect.test_execution_id,
                test_case_id=defect.test_case_id,
                requirement_id=defect.requirement_id,
                title=defect.title,
                description=defect.description,
                steps_to_reproduce=defect.steps_to_reproduce,
                defect_type=defect.defect_type,
                severity=defect.severity,
                priority=defect.priority,
                status=defect.status,
                resolution=defect.resolution,
                found_in_version=defect.found_in_version,
                fixed_in_version=defect.fixed_in_version,
                test_environment=defect.test_environment,
                reporter_id=defect.reporter_id,
                assignee_id=defect.assignee_id,
                resolver_id=defect.resolver_id,
                reported_at=defect.reported_at,
                assigned_at=defect.assigned_at,
                resolved_at=defect.resolved_at,
                verified_at=defect.verified_at,
                attachments=defect.attachments,
                created_at=defect.created_at,
                updated_at=defect.updated_at
            ))
        
        return BaseResponse(
            success=True,
            message=f"批量更新缺陷成功，共更新{len(response_data)}个缺陷",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"批量更新缺陷失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{defect_id}/comments", response_model=BaseResponse[DefectCommentResponse])
async def add_defect_comment(
    defect_id: int = Path(..., description="缺陷ID"),
    request: DefectCommentRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    添加缺陷评论
    
    为缺陷添加评论或回复。
    """
    try:
        service = DefectService(db)
        
        # 添加评论
        comment = await service.add_defect_comment(
            defect_id,
            current_user.id,
            request.content,
            request.parent_id
        )
        
        # 构建响应
        response_data = DefectCommentResponse(
            id=comment.id,
            defect_id=comment.defect_id,
            user_id=comment.user_id,
            content=comment.content,
            parent_id=comment.parent_id,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="缺陷评论添加成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"添加缺陷评论失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{defect_id}/comments", response_model=PaginatedResponse[DefectCommentResponse])
async def get_defect_comments(
    defect_id: int = Path(..., description="缺陷ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取缺陷评论列表
    
    获取指定缺陷的评论列表。
    """
    try:
        service = DefectService(db)
        
        # 获取评论列表
        comments, total = await service.get_defect_comments(defect_id, page, page_size)
        
        # 构建响应数据
        response_data = []
        for comment in comments:
            response_data.append(DefectCommentResponse(
                id=comment.id,
                defect_id=comment.defect_id,
                user_id=comment.user_id,
                content=comment.content,
                parent_id=comment.parent_id,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            ))
        
        return PaginatedResponse(
            success=True,
            message="获取缺陷评论列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取缺陷评论列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/statistics/summary", response_model=BaseResponse[DefectStatisticsResponse])
async def get_defect_statistics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取缺陷统计信息
    
    获取缺陷的统计数据和分布情况。
    """
    try:
        analysis_service = DefectAnalysisService(db)
        
        # 构建统计条件
        filters = {}
        if project_id:
            filters['project_id'] = project_id
        if test_plan_id:
            filters['test_plan_id'] = test_plan_id
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        # 获取缺陷统计
        statistics = await analysis_service.get_defect_statistics(filters)
        
        # 构建响应
        response_data = DefectStatisticsResponse(
            total_defects=statistics.total_defects,
            defects_by_severity=statistics.defects_by_severity,
            defects_by_type=statistics.defects_by_type,
            defects_by_status=statistics.defects_by_status,
            defects_by_module=statistics.defects_by_module,
            resolution_time_avg=statistics.resolution_time_avg,
            defect_density=statistics.defect_density,
            escape_rate=statistics.escape_rate
        )
        
        return BaseResponse(
            success=True,
            message="获取缺陷统计成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取缺陷统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/trends/analysis", response_model=BaseResponse[DefectTrendResponse])
async def get_defect_trends(
    project_id: int = Query(..., description="项目ID"),
    time_range: str = Query("30d", description="时间范围"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取缺陷趋势分析
    
    分析缺陷趋势和预测未来走向。
    """
    try:
        trend_service = DefectTrendService(db)
        
        # 分析缺陷趋势
        trend_analysis = await trend_service.analyze_defect_trends(project_id, time_range)
        
        # 构建响应
        response_data = DefectTrendResponse(
            project_id=trend_analysis.project_id,
            time_range=trend_analysis.time_range,
            trend_data=DefectStatisticsResponse(**trend_analysis.trend_data),
            predictions=trend_analysis.predictions,
            suggestions=trend_analysis.suggestions,
            generated_at=trend_analysis.generated_at.isoformat()
        )
        
        return BaseResponse(
            success=True,
            message="获取缺陷趋势分析成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取缺陷趋势分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{defect_id}/assign", response_model=BaseResponse[DefectResponse])
async def assign_defect(
    defect_id: int = Path(..., description="缺陷ID"),
    payload: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    分配缺陷
    
    将缺陷分配给指定的处理人员。
    """
    try:
        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise HTTPException(status_code=404, detail="缺陷不存在")
        assignee_id = payload.get("assignee_id") or payload.get("assigneeId")
        if not assignee_id:
            raise HTTPException(status_code=400, detail="分配人不能为空")
        defect.assignee_id = int(assignee_id)
        defect.status = DefectStatus.ASSIGNED
        defect.assigned_at = datetime.utcnow()
        defect.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(defect)
        
        return BaseResponse(
            success=True,
            message="缺陷分配成功",
            data=_build_defect_response(defect)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"分配缺陷失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{defect_id}/duplicate", response_model=BaseResponse[DefectResponse])
async def mark_defect_duplicate(
    defect_id: int = Path(..., description="缺陷ID"),
    duplicate_of: int = Body(..., description="重复的原始缺陷ID"),
    notes: Optional[str] = Body(None, description="备注"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    标记缺陷为重复
    
    将缺陷标记为另一个缺陷的重复。
    """
    try:
        service = DefectService(db)
        
        # 标记为重复
        defect = await service.mark_defect_duplicate(defect_id, duplicate_of, current_user.id, notes)
        
        # 构建响应
        response_data = DefectResponse(
            id=defect.id,
            defect_code=defect.defect_code,
            test_execution_id=defect.test_execution_id,
            test_case_id=defect.test_case_id,
            requirement_id=defect.requirement_id,
            title=defect.title,
            description=defect.description,
            steps_to_reproduce=defect.steps_to_reproduce,
            defect_type=defect.defect_type,
            severity=defect.severity,
            priority=defect.priority,
            status=defect.status,
            resolution=defect.resolution,
            found_in_version=defect.found_in_version,
            fixed_in_version=defect.fixed_in_version,
            test_environment=defect.test_environment,
            reporter_id=defect.reporter_id,
            assignee_id=defect.assignee_id,
            resolver_id=defect.resolver_id,
            reported_at=defect.reported_at,
            assigned_at=defect.assigned_at,
            resolved_at=defect.resolved_at,
            verified_at=defect.verified_at,
            attachments=defect.attachments,
            created_at=defect.created_at,
            updated_at=defect.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="缺陷标记为重复成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"标记缺陷为重复失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
