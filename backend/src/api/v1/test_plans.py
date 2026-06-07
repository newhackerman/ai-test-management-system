"""
测试计划管理API接口

本模块实现测试计划相关的RESTful API接口，包括：
- 测试计划的CRUD操作和查询接口
- 计划进度监控和统计API
- API参数验证和错误处理
- 集成主系统的认证和权限控制
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ...services.test_plan_service import TestPlanService, TestPlanAnalyticsService
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...models.test_plan import TestPlan, TestType, TestPlanStatus
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-plans", tags=["测试计划管理"])
security = HTTPBearer()


def _is_missing_table_error(error: Exception) -> bool:
    text = str(error).lower()
    return "doesn't exist" in text or "no such table" in text


def _build_test_plan_response(test_plan):
    return TestPlanResponse(
        id=test_plan.id,
        plan_code=test_plan.plan_code,
        project_id=test_plan.project_id,
        plan_name=test_plan.plan_name,
        description=test_plan.description,
        test_type=test_plan.test_type,
        test_strategy=test_plan.test_strategy,
        test_scope=test_plan.test_scope,
        status=test_plan.status,
        planned_start_date=test_plan.planned_start_date,
        planned_end_date=test_plan.planned_end_date,
        actual_start_date=test_plan.actual_start_date,
        actual_end_date=test_plan.actual_end_date,
        test_manager_id=test_plan.test_manager_id,
        created_by=test_plan.created_by,
        total_cases=test_plan.total_cases,
        executed_cases=test_plan.executed_cases,
        passed_cases=test_plan.passed_cases,
        failed_cases=test_plan.failed_cases,
        pass_rate=float(test_plan.pass_rate) if test_plan.pass_rate else 0.0,
        execution_rate=float(test_plan.execution_rate) if test_plan.execution_rate else 0.0,
        created_at=test_plan.created_at,
        updated_at=test_plan.updated_at
    )


# 请求模式
class CreateTestPlanRequest(BaseModel):
    """创建测试计划请求"""
    project_id: int = Field(..., description="项目ID")
    plan_name: str = Field(..., min_length=1, max_length=200, description="测试计划名称")
    description: Optional[str] = Field(None, description="测试计划描述")
    test_type: TestType = Field(..., description="测试类型")
    test_strategy: Optional[str] = Field(None, description="测试策略")
    test_scope: Optional[str] = Field(None, description="测试范围")
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    test_manager_id: Optional[int] = Field(None, description="测试经理ID")
    phases: Optional[List[Dict[str, Any]]] = Field(None, description="测试阶段")
    resources: Optional[List[Dict[str, Any]]] = Field(None, description="测试资源")


class UpdateTestPlanRequest(BaseModel):
    """更新测试计划请求"""
    plan_name: Optional[str] = Field(None, min_length=1, max_length=200, description="测试计划名称")
    description: Optional[str] = Field(None, description="测试计划描述")
    test_strategy: Optional[str] = Field(None, description="测试策略")
    test_scope: Optional[str] = Field(None, description="测试范围")
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    actual_start_date: Optional[date] = Field(None, description="实际开始日期")
    actual_end_date: Optional[date] = Field(None, description="实际结束日期")
    test_manager_id: Optional[int] = Field(None, description="测试经理ID")
    status: Optional[TestPlanStatus] = Field(None, description="计划状态")


class TestPlanQueryParams(BaseModel):
    """测试计划查询参数"""
    project_id: Optional[int] = Field(None, description="项目ID")
    status: Optional[TestPlanStatus] = Field(None, description="计划状态")
    test_type: Optional[TestType] = Field(None, description="测试类型")
    test_manager_id: Optional[int] = Field(None, description="测试经理ID")
    search: Optional[str] = Field(None, description="搜索关键词")
    start_date: Optional[date] = Field(None, description="开始日期范围")
    end_date: Optional[date] = Field(None, description="结束日期范围")


# 响应模式
class TestPlanResponse(BaseModel):
    """测试计划响应"""
    id: int = Field(..., description="测试计划ID")
    plan_code: str = Field(..., description="测试计划编码")
    project_id: int = Field(..., description="项目ID")
    plan_name: str = Field(..., description="测试计划名称")
    description: Optional[str] = Field(None, description="测试计划描述")
    test_type: TestType = Field(..., description="测试类型")
    test_strategy: Optional[str] = Field(None, description="测试策略")
    test_scope: Optional[str] = Field(None, description="测试范围")
    status: TestPlanStatus = Field(..., description="计划状态")
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    actual_start_date: Optional[date] = Field(None, description="实际开始日期")
    actual_end_date: Optional[date] = Field(None, description="实际结束日期")
    test_manager_id: int = Field(..., description="测试经理ID")
    created_by: int = Field(..., description="创建人ID")
    total_cases: int = Field(..., description="总用例数")
    executed_cases: int = Field(..., description="已执行用例数")
    passed_cases: int = Field(..., description="通过用例数")
    failed_cases: int = Field(..., description="失败用例数")
    pass_rate: float = Field(..., description="通过率")
    execution_rate: float = Field(..., description="执行率")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TestPlanProgressResponse(BaseModel):
    """测试计划进度响应"""
    plan_id: int = Field(..., description="测试计划ID")
    total_cases: int = Field(..., description="总用例数")
    executed_cases: int = Field(..., description="已执行用例数")
    passed_cases: int = Field(..., description="通过用例数")
    failed_cases: int = Field(..., description="失败用例数")
    blocked_cases: int = Field(..., description="阻塞用例数")
    skipped_cases: int = Field(..., description="跳过用例数")
    execution_rate: float = Field(..., description="执行率")
    pass_rate: float = Field(..., description="通过率")
    updated_at: str = Field(..., description="更新时间")


class TestPlanStatisticsResponse(BaseModel):
    """测试计划统计响应"""
    plan_id: int = Field(..., description="测试计划ID")
    total_cases: int = Field(..., description="总用例数")
    priority_distribution: Dict[str, int] = Field(..., description="优先级分布")
    complexity_distribution: Dict[str, int] = Field(..., description="复杂度分布")
    execution_distribution: Dict[str, int] = Field(..., description="执行状态分布")
    defect_distribution: Dict[str, int] = Field(..., description="缺陷分布")
    generated_at: str = Field(..., description="生成时间")


# API接口实现
@router.post("/", response_model=BaseResponse[TestPlanResponse])
async def create_test_plan(
    request: CreateTestPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建测试计划
    
    创建新的测试计划，包括基本信息、测试策略、阶段和资源分配。
    支持AI辅助策略建议。
    """
    try:
        service = TestPlanService(db)
        
        # 转换请求数据
        plan_data = request.dict()
        
        # 创建测试计划
        test_plan = await service.create_test_plan(plan_data, current_user.id)
        
        # 构建响应
        response_data = TestPlanResponse(
            id=test_plan.id,
            plan_code=test_plan.plan_code,
            project_id=test_plan.project_id,
            plan_name=test_plan.plan_name,
            description=test_plan.description,
            test_type=test_plan.test_type,
            test_strategy=test_plan.test_strategy,
            test_scope=test_plan.test_scope,
            status=test_plan.status,
            planned_start_date=test_plan.planned_start_date,
            planned_end_date=test_plan.planned_end_date,
            actual_start_date=test_plan.actual_start_date,
            actual_end_date=test_plan.actual_end_date,
            test_manager_id=test_plan.test_manager_id,
            created_by=test_plan.created_by,
            total_cases=test_plan.total_cases,
            executed_cases=test_plan.executed_cases,
            passed_cases=test_plan.passed_cases,
            failed_cases=test_plan.failed_cases,
            pass_rate=float(test_plan.pass_rate) if test_plan.pass_rate else 0.0,
            execution_rate=float(test_plan.execution_rate) if test_plan.execution_rate else 0.0,
            created_at=test_plan.created_at,
            updated_at=test_plan.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试计划创建成功",
            data=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"创建测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/templates", response_model=BaseResponse[List[Dict[str, Any]]])
async def get_test_plan_templates(
    current_user: User = Depends(get_current_user)
):
    """获取测试计划模板列表"""
    return BaseResponse(
        success=True,
        message="获取测试计划模板成功",
        data=[]
    )


@router.patch("/{plan_id}/status", response_model=BaseResponse[TestPlanResponse])
async def update_test_plan_status(
    plan_id: int = Path(..., description="测试计划ID"),
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新测试计划状态（兼容前端列表页操作）。"""
    try:
        status_value = request.get("status")
        if not status_value:
            raise HTTPException(status_code=400, detail="状态不能为空")

        test_plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
        if not test_plan:
            raise HTTPException(status_code=404, detail="测试计划不存在")

        test_plan.status = TestPlanStatus(status_value)
        if test_plan.status == TestPlanStatus.IN_PROGRESS and not test_plan.actual_start_date:
            test_plan.actual_start_date = date.today()
        if test_plan.status == TestPlanStatus.COMPLETED and not test_plan.actual_end_date:
            test_plan.actual_end_date = date.today()
        test_plan.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(test_plan)

        return BaseResponse(success=True, message="测试计划状态更新成功", data=_build_test_plan_response(test_plan))
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的测试计划状态")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新测试计划状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{plan_id}/duplicate", response_model=BaseResponse[TestPlanResponse])
async def duplicate_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """复制测试计划。"""
    try:
        source = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="测试计划不存在")

        today = datetime.now().strftime("%Y%m%d")
        count = db.query(TestPlan).filter(TestPlan.plan_code.like(f"TP-COPY-{today}-%")).count()
        new_plan = TestPlan(
            plan_code=f"TP-COPY-{today}-{count + 1:03d}",
            project_id=source.project_id,
            plan_name=request.get("plan_name") or request.get("plan_code") or request.get("plan_name") or f"{source.plan_name} - 副本",
            description=source.description,
            test_type=source.test_type,
            test_strategy=source.test_strategy,
            test_scope=source.test_scope,
            status=TestPlanStatus.DRAFT,
            planned_start_date=source.planned_start_date,
            planned_end_date=source.planned_end_date,
            test_manager_id=source.test_manager_id or current_user.id,
            created_by=current_user.id,
            total_cases=0,
            executed_cases=0,
            passed_cases=0,
            failed_cases=0,
            pass_rate=0,
            execution_rate=0
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return BaseResponse(success=True, message="测试计划复制成功", data=_build_test_plan_response(new_plan))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"复制测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{plan_id}/export")
async def export_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    format: str = Query("csv", description="导出格式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出测试计划基础信息。"""
    test_plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not test_plan:
        raise HTTPException(status_code=404, detail="测试计划不存在")

    data = _build_test_plan_response(test_plan).dict()
    lines = ["字段,值"] + [f"{key},{str(value or '').replace(',', '，')}" for key, value in data.items()]
    content = "\ufeff" + "\n".join(lines)
    suffix = "csv" if format not in {"txt", "csv"} else format
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=test-plan-{plan_id}.{suffix}"}
    )


@router.get("/{plan_id}", response_model=BaseResponse[TestPlanResponse])
async def get_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试计划详情
    
    根据测试计划ID获取详细信息，包括进度统计和关联数据。
    """
    try:
        service = TestPlanService(db)
        
        # 获取测试计划
        test_plan = await service.get_test_plan_by_id(plan_id)
        if not test_plan:
            raise HTTPException(status_code=404, detail="测试计划不存在")
        
        # 构建响应
        response_data = TestPlanResponse(
            id=test_plan.id,
            plan_code=test_plan.plan_code,
            project_id=test_plan.project_id,
            plan_name=test_plan.plan_name,
            description=test_plan.description,
            test_type=test_plan.test_type,
            test_strategy=test_plan.test_strategy,
            test_scope=test_plan.test_scope,
            status=test_plan.status,
            planned_start_date=test_plan.planned_start_date,
            planned_end_date=test_plan.planned_end_date,
            actual_start_date=test_plan.actual_start_date,
            actual_end_date=test_plan.actual_end_date,
            test_manager_id=test_plan.test_manager_id,
            created_by=test_plan.created_by,
            total_cases=test_plan.total_cases,
            executed_cases=test_plan.executed_cases,
            passed_cases=test_plan.passed_cases,
            failed_cases=test_plan.failed_cases,
            pass_rate=float(test_plan.pass_rate) if test_plan.pass_rate else 0.0,
            execution_rate=float(test_plan.execution_rate) if test_plan.execution_rate else 0.0,
            created_at=test_plan.created_at,
            updated_at=test_plan.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="获取测试计划成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.put("/{plan_id}", response_model=BaseResponse[TestPlanResponse])
async def update_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    request: UpdateTestPlanRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新测试计划
    
    更新测试计划的基本信息、状态和配置。
    支持业务规则验证和权限控制。
    """
    try:
        service = TestPlanService(db)
        
        # 转换请求数据，过滤None值
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        # 更新测试计划
        test_plan = await service.update_test_plan(plan_id, update_data, current_user.id)
        
        # 构建响应
        response_data = TestPlanResponse(
            id=test_plan.id,
            plan_code=test_plan.plan_code,
            project_id=test_plan.project_id,
            plan_name=test_plan.plan_name,
            description=test_plan.description,
            test_type=test_plan.test_type,
            test_strategy=test_plan.test_strategy,
            test_scope=test_plan.test_scope,
            status=test_plan.status,
            planned_start_date=test_plan.planned_start_date,
            planned_end_date=test_plan.planned_end_date,
            actual_start_date=test_plan.actual_start_date,
            actual_end_date=test_plan.actual_end_date,
            test_manager_id=test_plan.test_manager_id,
            created_by=test_plan.created_by,
            total_cases=test_plan.total_cases,
            executed_cases=test_plan.executed_cases,
            passed_cases=test_plan.passed_cases,
            failed_cases=test_plan.failed_cases,
            pass_rate=float(test_plan.pass_rate) if test_plan.pass_rate else 0.0,
            execution_rate=float(test_plan.execution_rate) if test_plan.execution_rate else 0.0,
            created_at=test_plan.created_at,
            updated_at=test_plan.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试计划更新成功",
            data=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"更新测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/{plan_id}", response_model=BaseResponse[bool])
async def delete_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除测试计划
    
    删除或取消测试计划。已开始的计划只能取消，不能删除。
    """
    try:
        service = TestPlanService(db)
        
        # 删除测试计划
        result = await service.delete_test_plan(plan_id, current_user.id)
        
        return BaseResponse(
            success=True,
            message="测试计划删除成功",
            data=result
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"删除测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/", response_model=PaginatedResponse[TestPlanResponse])
async def list_test_plans(
    project_id: Optional[int] = Query(None, description="项目ID"),
    status: Optional[TestPlanStatus] = Query(None, description="计划状态"),
    test_type: Optional[TestType] = Query(None, description="测试类型"),
    test_manager_id: Optional[int] = Query(None, description="测试经理ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[date] = Query(None, description="开始日期范围"),
    end_date: Optional[date] = Query(None, description="结束日期范围"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试计划列表
    
    支持多条件过滤和分页查询。
    """
    try:
        service = TestPlanService(db)
        
        # 构建查询条件
        filters = {}
        if project_id:
            filters['project_id'] = project_id
        if status:
            filters['status'] = status.value
        if test_type:
            filters['test_type'] = test_type.value
        if test_manager_id:
            filters['test_manager_id'] = test_manager_id
        if search:
            filters['search'] = search
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        # 查询测试计划列表
        if project_id:
            plans, total = await service.get_test_plans_by_project(
                project_id, status.value if status else None, page, page_size
            )
        else:
            query = db.query(TestPlan)
            if status:
                query = query.filter(TestPlan.status == status)
            if test_type:
                query = query.filter(TestPlan.test_type == test_type)
            if test_manager_id:
                query = query.filter(TestPlan.test_manager_id == test_manager_id)
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (TestPlan.plan_name.like(search_term)) |
                    (TestPlan.plan_code.like(search_term)) |
                    (TestPlan.description.like(search_term))
                )
            if start_date:
                query = query.filter(TestPlan.planned_start_date >= start_date)
            if end_date:
                query = query.filter(TestPlan.planned_end_date <= end_date)

            total = query.count()
            plans = query.order_by(TestPlan.created_at.desc()) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()
        
        # 构建响应数据
        response_data = []
        for plan in plans:
            response_data.append(_build_test_plan_response(plan))
        
        return PaginatedResponse(
            success=True,
            message="获取测试计划列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        if _is_missing_table_error(e):
            return PaginatedResponse(
                success=True,
                message="测试计划表未初始化，当前无数据",
                data=[],
                total=0,
                page=page,
                page_size=page_size
            )
        logger.error(f"获取测试计划列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{plan_id}/progress", response_model=BaseResponse[TestPlanProgressResponse])
async def get_test_plan_progress(
    plan_id: int = Path(..., description="测试计划ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试计划进度
    
    实时计算和返回测试计划的执行进度信息。
    """
    try:
        service = TestPlanService(db)
        
        # 更新并获取进度信息
        progress_info = await service.update_plan_progress(plan_id)
        
        # 构建响应
        response_data = TestPlanProgressResponse(**progress_info)
        
        return BaseResponse(
            success=True,
            message="获取测试计划进度成功",
            data=response_data
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取测试计划进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{plan_id}/statistics", response_model=BaseResponse[TestPlanStatisticsResponse])
async def get_test_plan_statistics(
    plan_id: int = Path(..., description="测试计划ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试计划统计信息
    
    获取测试计划的详细统计数据，包括用例分布、执行情况、缺陷统计等。
    """
    try:
        analytics_service = TestPlanAnalyticsService(db)
        
        # 获取统计信息
        statistics = await analytics_service.get_plan_statistics(plan_id)
        
        # 构建响应
        response_data = TestPlanStatisticsResponse(**statistics)
        
        return BaseResponse(
            success=True,
            message="获取测试计划统计成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取测试计划统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{plan_id}/trends", response_model=BaseResponse[Dict[str, Any]])
async def get_test_plan_trends(
    plan_id: int = Path(..., description="测试计划ID"),
    days: int = Query(30, ge=1, le=365, description="天数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试计划趋势数据
    
    获取指定时间范围内的测试执行趋势和通过率变化。
    """
    try:
        analytics_service = TestPlanAnalyticsService(db)
        
        # 获取趋势数据
        trends = await analytics_service.get_plan_trends(plan_id, days)
        
        return BaseResponse(
            success=True,
            message="获取测试计划趋势成功",
            data=trends
        )
        
    except Exception as e:
        logger.error(f"获取测试计划趋势失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{plan_id}/start", response_model=BaseResponse[TestPlanResponse])
async def start_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    启动测试计划
    
    将测试计划状态从已批准变更为进行中。
    """
    try:
        service = TestPlanService(db)
        
        # 启动测试计划
        update_data = {
            'status': TestPlanStatus.IN_PROGRESS,
            'actual_start_date': date.today()
        }
        
        test_plan = await service.update_test_plan(plan_id, update_data, current_user.id)
        
        # 构建响应
        response_data = TestPlanResponse(
            id=test_plan.id,
            plan_code=test_plan.plan_code,
            project_id=test_plan.project_id,
            plan_name=test_plan.plan_name,
            description=test_plan.description,
            test_type=test_plan.test_type,
            test_strategy=test_plan.test_strategy,
            test_scope=test_plan.test_scope,
            status=test_plan.status,
            planned_start_date=test_plan.planned_start_date,
            planned_end_date=test_plan.planned_end_date,
            actual_start_date=test_plan.actual_start_date,
            actual_end_date=test_plan.actual_end_date,
            test_manager_id=test_plan.test_manager_id,
            created_by=test_plan.created_by,
            total_cases=test_plan.total_cases,
            executed_cases=test_plan.executed_cases,
            passed_cases=test_plan.passed_cases,
            failed_cases=test_plan.failed_cases,
            pass_rate=float(test_plan.pass_rate) if test_plan.pass_rate else 0.0,
            execution_rate=float(test_plan.execution_rate) if test_plan.execution_rate else 0.0,
            created_at=test_plan.created_at,
            updated_at=test_plan.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试计划启动成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"启动测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{plan_id}/complete", response_model=BaseResponse[TestPlanResponse])
async def complete_test_plan(
    plan_id: int = Path(..., description="测试计划ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    完成测试计划
    
    将测试计划状态变更为已完成。
    """
    try:
        service = TestPlanService(db)
        
        # 完成测试计划
        update_data = {
            'status': TestPlanStatus.COMPLETED,
            'actual_end_date': date.today()
        }
        
        test_plan = await service.update_test_plan(plan_id, update_data, current_user.id)
        
        # 构建响应
        response_data = TestPlanResponse(
            id=test_plan.id,
            plan_code=test_plan.plan_code,
            project_id=test_plan.project_id,
            plan_name=test_plan.plan_name,
            description=test_plan.description,
            test_type=test_plan.test_type,
            test_strategy=test_plan.test_strategy,
            test_scope=test_plan.test_scope,
            status=test_plan.status,
            planned_start_date=test_plan.planned_start_date,
            planned_end_date=test_plan.planned_end_date,
            actual_start_date=test_plan.actual_start_date,
            actual_end_date=test_plan.actual_end_date,
            test_manager_id=test_plan.test_manager_id,
            created_by=test_plan.created_by,
            total_cases=test_plan.total_cases,
            executed_cases=test_plan.executed_cases,
            passed_cases=test_plan.passed_cases,
            failed_cases=test_plan.failed_cases,
            pass_rate=float(test_plan.pass_rate) if test_plan.pass_rate else 0.0,
            execution_rate=float(test_plan.execution_rate) if test_plan.execution_rate else 0.0,
            created_at=test_plan.created_at,
            updated_at=test_plan.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试计划完成成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"完成测试计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
