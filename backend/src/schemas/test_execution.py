"""
测试执行相关的Pydantic模式定义
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .base import BaseResponse


class ExecutionType(str, Enum):
    """执行类型枚举"""
    MANUAL = "MANUAL"
    AUTOMATED = "AUTOMATED"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    NOT_EXECUTED = "NOT_EXECUTED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class TestEnvironmentStatus(str, Enum):
    """测试环境状态枚举"""
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"
    UNAVAILABLE = "UNAVAILABLE"


# 请求模式
class StartManualExecutionRequest(BaseModel):
    """开始手动测试执行请求"""
    test_case_id: int = Field(..., description="测试用例ID")
    test_environment: str = Field(..., description="测试环境")
    browser_info: Optional[str] = Field(None, description="浏览器信息")
    os_info: Optional[str] = Field(None, description="操作系统信息")
    execution_notes: Optional[str] = Field(None, description="执行备注")


class CompleteManualExecutionRequest(BaseModel):
    """完成手动测试执行请求"""
    execution_id: int = Field(..., description="执行记录ID")
    execution_status: ExecutionStatus = Field(..., description="执行状态")
    actual_result: Optional[str] = Field(None, description="实际结果")
    failure_reason: Optional[str] = Field(None, description="失败原因")
    execution_notes: Optional[str] = Field(None, description="执行备注")
    screenshots: Optional[List[Dict[str, Any]]] = Field(None, description="截图信息")
    logs: Optional[List[Dict[str, Any]]] = Field(None, description="日志信息")
    videos: Optional[List[Dict[str, Any]]] = Field(None, description="视频信息")
    create_defect: bool = Field(False, description="是否创建缺陷")
    defect_data: Optional[Dict[str, Any]] = Field(None, description="缺陷数据")


class UpdateExecutionStepRequest(BaseModel):
    """更新执行步骤请求"""
    execution_id: int = Field(..., description="执行记录ID")
    step_index: int = Field(..., description="步骤索引")
    step_status: ExecutionStatus = Field(..., description="步骤状态")
    step_result: Optional[str] = Field(None, description="步骤结果")
    step_notes: Optional[str] = Field(None, description="步骤备注")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


class PauseExecutionRequest(BaseModel):
    """暂停执行请求"""
    execution_id: int = Field(..., description="执行记录ID")
    pause_reason: Optional[str] = Field(None, description="暂停原因")


class ResumeExecutionRequest(BaseModel):
    """恢复执行请求"""
    execution_id: int = Field(..., description="执行记录ID")
    resume_notes: Optional[str] = Field(None, description="恢复备注")


class BatchExecutionRequest(BaseModel):
    """批量执行请求"""
    test_case_ids: List[int] = Field(..., description="测试用例ID列表")
    test_environment: str = Field(..., description="测试环境")
    execution_type: ExecutionType = Field(..., description="执行类型")
    parallel_count: Optional[int] = Field(1, description="并发数量")
    retry_count: Optional[int] = Field(0, description="重试次数")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")


class AutomationExecutionRequest(BaseModel):
    """自动化执行请求"""
    test_case_ids: List[int] = Field(..., description="测试用例ID列表")
    framework: str = Field(..., description="自动化框架")
    test_environment: str = Field(..., description="测试环境")
    browser: Optional[str] = Field("chrome", description="浏览器类型")
    parallel_count: Optional[int] = Field(1, description="并发数量")
    retry_count: Optional[int] = Field(0, description="重试次数")
    timeout: Optional[int] = Field(300, description="超时时间(秒)")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")


# 响应模式
class ExecutionStepResponse(BaseModel):
    """执行步骤响应"""
    step_index: int = Field(..., description="步骤索引")
    step_description: str = Field(..., description="步骤描述")
    expected_result: str = Field(..., description="预期结果")
    actual_result: Optional[str] = Field(None, description="实际结果")
    step_status: ExecutionStatus = Field(..., description="步骤状态")
    step_notes: Optional[str] = Field(None, description="步骤备注")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")
    executed_at: Optional[datetime] = Field(None, description="执行时间")


class TestExecutionResponse(BaseModel):
    """测试执行响应"""
    id: int = Field(..., description="执行记录ID")
    execution_code: str = Field(..., description="执行编码")
    test_case_id: int = Field(..., description="测试用例ID")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    execution_type: ExecutionType = Field(..., description="执行类型")
    execution_status: ExecutionStatus = Field(..., description="执行状态")
    
    # 结果信息
    actual_result: Optional[str] = Field(None, description="实际结果")
    failure_reason: Optional[str] = Field(None, description="失败原因")
    execution_notes: Optional[str] = Field(None, description="执行备注")
    
    # 环境信息
    test_environment: Optional[str] = Field(None, description="测试环境")
    browser_info: Optional[str] = Field(None, description="浏览器信息")
    os_info: Optional[str] = Field(None, description="操作系统信息")
    
    # 时间信息
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    duration: Optional[int] = Field(None, description="执行时长(秒)")
    
    # 人员信息
    executor_id: int = Field(..., description="执行人ID")
    
    # 附件信息
    screenshots: Optional[List[Dict[str, Any]]] = Field(None, description="截图信息")
    logs: Optional[List[Dict[str, Any]]] = Field(None, description="日志信息")
    videos: Optional[List[Dict[str, Any]]] = Field(None, description="视频信息")
    
    # 步骤信息
    execution_steps: Optional[List[ExecutionStepResponse]] = Field(None, description="执行步骤")
    
    # 审计信息
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ExecutionProgressResponse(BaseModel):
    """执行进度响应"""
    execution_id: int = Field(..., description="执行记录ID")
    total_steps: int = Field(..., description="总步骤数")
    completed_steps: int = Field(..., description="已完成步骤数")
    passed_steps: int = Field(..., description="通过步骤数")
    failed_steps: int = Field(..., description="失败步骤数")
    current_step: Optional[int] = Field(None, description="当前步骤")
    progress_percentage: float = Field(..., description="进度百分比")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")


class BatchExecutionResponse(BaseModel):
    """批量执行响应"""
    batch_id: str = Field(..., description="批次ID")
    total_cases: int = Field(..., description="总用例数")
    completed_cases: int = Field(..., description="已完成用例数")
    passed_cases: int = Field(..., description="通过用例数")
    failed_cases: int = Field(..., description="失败用例数")
    blocked_cases: int = Field(..., description="阻塞用例数")
    skipped_cases: int = Field(..., description="跳过用例数")
    execution_status: str = Field(..., description="批次执行状态")
    started_at: datetime = Field(..., description="开始时间")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    executions: List[TestExecutionResponse] = Field(..., description="执行记录列表")


class AutomationExecutionResponse(BaseModel):
    """自动化执行响应"""
    execution_id: str = Field(..., description="执行ID")
    framework: str = Field(..., description="自动化框架")
    test_environment: str = Field(..., description="测试环境")
    status: str = Field(..., description="执行状态")
    total_cases: int = Field(..., description="总用例数")
    completed_cases: int = Field(..., description="已完成用例数")
    passed_cases: int = Field(..., description="通过用例数")
    failed_cases: int = Field(..., description="失败用例数")
    progress_percentage: float = Field(..., description="进度百分比")
    started_at: datetime = Field(..., description="开始时间")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    execution_logs: Optional[List[Dict[str, Any]]] = Field(None, description="执行日志")
    test_results: Optional[List[Dict[str, Any]]] = Field(None, description="测试结果")


class ExecutionStatisticsResponse(BaseModel):
    """执行统计响应"""
    total_executions: int = Field(..., description="总执行数")
    manual_executions: int = Field(..., description="手动执行数")
    automated_executions: int = Field(..., description="自动化执行数")
    passed_executions: int = Field(..., description="通过执行数")
    failed_executions: int = Field(..., description="失败执行数")
    blocked_executions: int = Field(..., description="阻塞执行数")
    skipped_executions: int = Field(..., description="跳过执行数")
    pass_rate: float = Field(..., description="通过率")
    average_duration: Optional[float] = Field(None, description="平均执行时长")
    execution_trend: Optional[List[Dict[str, Any]]] = Field(None, description="执行趋势")


# 测试环境相关模式
class TestEnvironmentRequest(BaseModel):
    """测试环境请求"""
    environment_name: str = Field(..., description="环境名称")
    environment_type: str = Field(..., description="环境类型")
    description: Optional[str] = Field(None, description="环境描述")
    configuration: Dict[str, Any] = Field(..., description="环境配置")
    is_active: bool = Field(True, description="是否激活")


class TestEnvironmentResponse(BaseModel):
    """测试环境响应"""
    id: int = Field(..., description="环境ID")
    environment_name: str = Field(..., description="环境名称")
    environment_type: str = Field(..., description="环境类型")
    description: Optional[str] = Field(None, description="环境描述")
    status: TestEnvironmentStatus = Field(..., description="环境状态")
    configuration: Dict[str, Any] = Field(..., description="环境配置")
    is_active: bool = Field(..., description="是否激活")
    current_user: Optional[str] = Field(None, description="当前使用者")
    reserved_until: Optional[datetime] = Field(None, description="预约到期时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class EnvironmentReservationRequest(BaseModel):
    """环境预约请求"""
    environment_id: int = Field(..., description="环境ID")
    reserved_from: datetime = Field(..., description="预约开始时间")
    reserved_until: datetime = Field(..., description="预约结束时间")
    purpose: str = Field(..., description="使用目的")
    notes: Optional[str] = Field(None, description="备注")


class EnvironmentReservationResponse(BaseModel):
    """环境预约响应"""
    id: int = Field(..., description="预约ID")
    environment_id: int = Field(..., description="环境ID")
    user_id: int = Field(..., description="用户ID")
    reserved_from: datetime = Field(..., description="预约开始时间")
    reserved_until: datetime = Field(..., description="预约结束时间")
    purpose: str = Field(..., description="使用目的")
    notes: Optional[str] = Field(None, description="备注")
    status: str = Field(..., description="预约状态")
    created_at: datetime = Field(..., description="创建时间")


# 列表响应
class TestExecutionListResponse(BaseResponse):
    """测试执行列表响应"""
    data: List[TestExecutionResponse] = Field(..., description="执行记录列表")


class TestEnvironmentListResponse(BaseResponse):
    """测试环境列表响应"""
    data: List[TestEnvironmentResponse] = Field(..., description="环境列表")


class EnvironmentReservationListResponse(BaseResponse):
    """环境预约列表响应"""
    data: List[EnvironmentReservationResponse] = Field(..., description="预约列表")