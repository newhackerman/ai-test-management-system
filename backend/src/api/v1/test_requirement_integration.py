"""
测试需求集成API接口

本模块提供测试管理系统与需求管理系统集成的API接口，包括：
- 需求测试用例创建
- 测试执行管理
- 缺陷关联管理
- 测试覆盖率分析
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...services.test_requirement_integration_service import (
    TestRequirementIntegrationService,
    get_test_requirement_integration_service
)
from ...services.auth import get_current_user
from ...models.user import User

router = APIRouter(prefix="/test-requirement-integration", tags=["测试需求集成"])


# 请求模型
class CreateTestCaseFromRequirementRequest(BaseModel):
    """从需求创建测试用例请求"""
    title: Optional[str] = Field(None, description="测试用例标题")
    description: Optional[str] = Field(None, description="测试用例描述")
    preconditions: Optional[str] = Field(None, description="前置条件")
    test_type: str = Field("FUNCTIONAL", description="测试类型")
    assignee_id: Optional[int] = Field(None, description="指派人ID")
    estimated_execution_time: Optional[int] = Field(30, description="预估执行时间(分钟)")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    tags: Optional[Dict[str, Any]] = Field(None, description="标签")

class ExecuteTestCaseRequest(BaseModel):
    """执行测试用例请求"""
    execution_status: str = Field(..., description="执行状态")
    actual_result: Optional[str] = Field(None, description="实际结果")
    execution_notes: Optional[str] = Field(None, description="执行备注")
    execution_time: Optional[int] = Field(None, description="执行时间(分钟)")
    test_environment: Optional[str] = Field(None, description="测试环境")
    browser_version: Optional[str] = Field(None, description="浏览器版本")
    os_version: Optional[str] = Field(None, description="操作系统版本")
    defects_found: Optional[int] = Field(0, description="发现缺陷数")
    screenshots: Optional[List[Dict[str, Any]]] = Field(None, description="截图信息")
    logs: Optional[List[Dict[str, Any]]] = Field(None, description="日志信息")
    execution_date: Optional[datetime] = Field(None, description="执行日期")

class CreateDefectFromTestFailureRequest(BaseModel):
    """从测试失败创建缺陷请求"""
    title: Optional[str] = Field(None, description="缺陷标题")
    description: str = Field(..., description="缺陷描述")
    severity: str = Field(..., description="严重程度")
    priority: Optional[str] = Field(None, description="优先级")
    defect_type: Optional[str] = Field("FUNCTIONAL", description="缺陷类型")
    steps_to_reproduce: Optional[str] = Field(None, description="重现步骤")
    actual_result: Optional[str] = Field(None, description="实际结果")
    environment: Optional[str] = Field(None, description="发现环境")
    browser_version: Optional[str] = Field(None, description="浏览器版本")
    os_version: Optional[str] = Field(None, description="操作系统版本")
    assignee_id: Optional[int] = Field(None, description="指派人ID")
    tags: Optional[Dict[str, Any]] = Field(None, description="标签")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


# 响应模型
class TestCaseCreationResponse(BaseModel):
    """测试用例创建响应"""
    test_case_id: int
    test_case_code: str
    title: str
    requirement_id: int
    project_id: int
    created_at: str

class TestExecutionResponse(BaseModel):
    """测试执行响应"""
    execution_id: int
    test_case_id: int
    execution_status: str
    execution_date: str
    executor_id: int

class DefectCreationResponse(BaseModel):
    """缺陷创建响应"""
    defect_id: int
    defect_code: str
    title: str
    test_case_id: int
    requirement_id: Optional[int]
    project_id: int
    created_at: str

class TestCoverageResponse(BaseModel):
    """测试覆盖率响应"""
    project_id: int
    requirement_id: Optional[int]
    total_test_cases: int
    executed_test_cases: int
    passed_test_cases: int
    failed_test_cases: int
    execution_coverage: float
    pass_rate: float
    requirements_covered: int
    requirements_total: int
    requirement_coverage: float
    coverage_date: str

class RequirementTestTraceabilityResponse(BaseModel):
    """需求测试追溯响应"""
    requirement_id: int
    requirement_title: str
    requirement_status: str
    test_cases: List[Dict[str, Any]]
    test_case_count: int
    execution_stats: Dict[str, Any]
    defects: List[Dict[str, Any]]
    defect_count: int
    coverage_metrics: Dict[str, float]
    traceability_complete: bool


@router.post("/requirements/{requirement_id}/create-test-case", response_model=TestCaseCreationResponse)
async def create_test_case_from_requirement(
    requirement_id: int = Path(..., description="需求ID"),
    request: CreateTestCaseFromRequirementRequest = Body(...),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    从需求创建测试用例
    
    基于需求信息创建对应的测试用例，并建立追溯关系
    """
    try:
        test_case_data = request.dict(exclude_unset=True)
        test_case = await service.create_test_case_from_requirement(requirement_id, test_case_data, current_user.id)
        
        return TestCaseCreationResponse(
            test_case_id=test_case.id,
            test_case_code=test_case.test_case_code,
            title=test_case.title,
            requirement_id=requirement_id,
            project_id=test_case.project_id,
            created_at=test_case.created_at.isoformat()
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建测试用例失败: {str(e)}")


@router.post("/test-cases/{test_case_id}/execute", response_model=TestExecutionResponse)
async def execute_test_case(
    test_case_id: int = Path(..., description="测试用例ID"),
    request: ExecuteTestCaseRequest = Body(...),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    执行测试用例
    
    执行测试用例并记录执行结果，自动更新相关需求状态
    """
    try:
        execution_data = request.dict(exclude_unset=True)
        execution = await service.execute_test_case(test_case_id, execution_data, current_user.id)
        
        return TestExecutionResponse(
            execution_id=execution.id,
            test_case_id=test_case_id,
            execution_status=execution.execution_status.value,
            execution_date=execution.execution_date.isoformat(),
            executor_id=execution.executor_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行测试用例失败: {str(e)}")


@router.post("/test-cases/{test_case_id}/create-defect", response_model=DefectCreationResponse)
async def create_defect_from_test_failure(
    test_case_id: int = Path(..., description="测试用例ID"),
    request: CreateDefectFromTestFailureRequest = Body(...),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    从测试失败创建缺陷
    
    基于测试失败结果创建缺陷记录，并建立与需求的关联
    """
    try:
        defect_data = request.dict(exclude_unset=True)
        defect = await service.create_defect_from_test_failure(test_case_id, defect_data, current_user.id)
        
        return DefectCreationResponse(
            defect_id=defect.id,
            defect_code=defect.defect_code,
            title=defect.title,
            test_case_id=test_case_id,
            requirement_id=defect.requirement_id,
            project_id=defect.project_id,
            created_at=defect.created_at.isoformat()
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建缺陷失败: {str(e)}")


@router.get("/projects/{project_id}/test-coverage", response_model=TestCoverageResponse)
async def calculate_test_coverage(
    project_id: int = Path(..., description="项目ID"),
    requirement_id: Optional[int] = Query(None, description="需求ID（可选）"),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    计算测试覆盖率
    
    计算项目或特定需求的测试覆盖率
    """
    try:
        coverage = await service.calculate_test_coverage(project_id, requirement_id)
        
        return TestCoverageResponse(
            project_id=coverage.project_id,
            requirement_id=coverage.requirement_id,
            total_test_cases=coverage.total_test_cases,
            executed_test_cases=coverage.executed_test_cases,
            passed_test_cases=coverage.passed_test_cases,
            failed_test_cases=coverage.failed_test_cases,
            execution_coverage=float(coverage.execution_coverage),
            pass_rate=float(coverage.pass_rate),
            requirements_covered=coverage.requirements_covered,
            requirements_total=coverage.requirements_total,
            requirement_coverage=float(coverage.requirement_coverage),
            coverage_date=coverage.coverage_date.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算测试覆盖率失败: {str(e)}")


@router.get("/requirements/{requirement_id}/test-traceability", response_model=RequirementTestTraceabilityResponse)
async def get_requirement_test_traceability(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    获取需求测试追溯关系
    
    获取需求与测试用例、测试执行、缺陷的完整追溯关系
    """
    try:
        traceability = await service.get_requirement_test_traceability(requirement_id)
        
        return RequirementTestTraceabilityResponse(**traceability)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取追溯关系失败: {str(e)}")


@router.put("/defects/{defect_id}/sync-resolution")
async def sync_defect_resolution_to_requirement(
    defect_id: int = Path(..., description="缺陷ID"),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    同步缺陷解决状态到需求
    
    将缺陷解决状态同步到关联的需求
    """
    try:
        success = await service.sync_defect_resolution_to_requirement(defect_id, current_user.id)
        
        return {
            "defect_id": defect_id,
            "sync_success": success,
            "message": "缺陷状态同步成功" if success else "缺陷状态同步失败"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/projects/{project_id}/test-metrics")
async def get_project_test_metrics(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    获取项目测试指标
    
    获取项目的测试执行统计、覆盖率分析等指标
    """
    try:
        # 计算项目整体覆盖率
        coverage = await service.calculate_test_coverage(project_id)
        
        return {
            "project_id": project_id,
            "test_coverage": {
                "total_test_cases": coverage.total_test_cases,
                "executed_test_cases": coverage.executed_test_cases,
                "execution_coverage": float(coverage.execution_coverage),
                "pass_rate": float(coverage.pass_rate),
                "requirement_coverage": float(coverage.requirement_coverage)
            },
            "generated_at": coverage.coverage_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取测试指标失败: {str(e)}")


@router.get("/requirements/{requirement_id}/test-summary")
async def get_requirement_test_summary(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: TestRequirementIntegrationService = Depends(get_test_requirement_integration_service)
):
    """
    获取需求测试汇总
    
    获取需求的测试用例数量、执行情况、缺陷情况等汇总信息
    """
    try:
        traceability = await service.get_requirement_test_traceability(requirement_id)
        
        return {
            "requirement_id": requirement_id,
            "test_case_count": traceability['test_case_count'],
            "execution_stats": traceability['execution_stats'],
            "defect_count": traceability['defect_count'],
            "coverage_metrics": traceability['coverage_metrics'],
            "traceability_complete": traceability['traceability_complete']
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取测试汇总失败: {str(e)}")


@router.get("/health")
async def health_check():
    """
    健康检查接口
    """
    return {
        "status": "healthy",
        "service": "test-requirement-integration",
        "timestamp": "2024-01-01T00:00:00Z"
    }