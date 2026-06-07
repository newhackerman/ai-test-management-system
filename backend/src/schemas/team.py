"""
团队管理模块的Pydantic模式定义

本模块定义了团队管理相关的请求和响应模式，包括：
- 团队成员添加、更新、删除的请求模式
- 团队成员相关的响应模式
- 工作负载分析和技能匹配模式
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import constr, condecimal


class ProjectMemberRole(str, Enum):
    """项目成员角色枚举"""
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    REQUIREMENT_MANAGER = "REQUIREMENT_MANAGER"
    DESIGNER = "DESIGNER"
    ARCHITECT = "ARCHITECT"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    DEVOPS = "DEVOPS"
    THIRD_PARTY = "THIRD_PARTY"


class MemberStatus(str, Enum):
    """成员状态枚举"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"


# 请求模式
class AddMemberRequest(BaseModel):
    """添加团队成员请求模式"""
    user_id: int = Field(..., description="用户ID")
    role_in_project: ProjectMemberRole = Field(..., description="项目内角色")
    allocation_percentage: condecimal(max_digits=5, decimal_places=2, ge=0, le=100) = Field(
        100.00, description="参与度百分比(0-100)"
    )
    hourly_rate: Optional[condecimal(max_digits=8, decimal_places=2, ge=0)] = Field(
        None, description="小时费率"
    )
    join_date: date = Field(..., description="加入日期")
    skills: Optional[List[str]] = Field(None, description="技能标签")
    responsibilities: Optional[str] = Field(None, description="职责描述")
    
    @validator('join_date')
    def validate_join_date(cls, v):
        """验证加入日期不能是未来日期"""
        if v > date.today():
            raise ValueError('加入日期不能是未来日期')
        return v


class UpdateMemberRequest(BaseModel):
    """更新团队成员请求模式"""
    role_in_project: Optional[ProjectMemberRole] = Field(None, description="项目内角色")
    allocation_percentage: Optional[condecimal(max_digits=5, decimal_places=2, ge=0, le=100)] = Field(
        None, description="参与度百分比(0-100)"
    )
    hourly_rate: Optional[condecimal(max_digits=8, decimal_places=2, ge=0)] = Field(
        None, description="小时费率"
    )
    leave_date: Optional[date] = Field(None, description="离开日期")
    status: Optional[MemberStatus] = Field(None, description="成员状态")
    skills: Optional[List[str]] = Field(None, description="技能标签")
    responsibilities: Optional[str] = Field(None, description="职责描述")
    
    @validator('leave_date')
    def validate_leave_date(cls, v):
        """验证离开日期不能早于今天"""
        if v and v < date.today():
            raise ValueError('离开日期不能早于今天')
        return v


class InviteMemberRequest(BaseModel):
    """邀请成员请求模式"""
    email: str = Field(..., description="邮箱地址")
    role_in_project: ProjectMemberRole = Field(..., description="项目内角色")
    allocation_percentage: condecimal(max_digits=5, decimal_places=2, ge=0, le=100) = Field(
        100.00, description="参与度百分比(0-100)"
    )
    hourly_rate: Optional[condecimal(max_digits=8, decimal_places=2, ge=0)] = Field(
        None, description="小时费率"
    )
    skills: Optional[List[str]] = Field(None, description="技能标签")
    responsibilities: Optional[str] = Field(None, description="职责描述")
    invitation_message: Optional[str] = Field(None, description="邀请消息")
    
    @validator('email')
    def validate_email(cls, v):
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('邮箱格式不正确')
        return v.lower()


class MemberQueryParams(BaseModel):
    """成员查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")
    role: Optional[List[ProjectMemberRole]] = Field(None, description="角色过滤")
    status: Optional[List[MemberStatus]] = Field(None, description="状态过滤")
    skills: Optional[List[str]] = Field(None, description="技能过滤")
    search: Optional[str] = Field(None, description="搜索关键词")
    sort_by: Optional[str] = Field("join_date", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")


# 响应模式
class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    email: str
    nickname: Optional[str]
    avatar: Optional[str]
    phone: Optional[str]
    
    class Config:
        from_attributes = True


class ProjectMemberResponse(BaseModel):
    """项目成员响应模式"""
    id: int
    project_id: int
    user_id: int
    user_info: Optional[UserInfo] = None
    role_in_project: ProjectMemberRole
    allocation_percentage: Decimal
    hourly_rate: Optional[Decimal]
    join_date: date
    leave_date: Optional[date]
    status: MemberStatus
    skills: Optional[List[str]]
    responsibilities: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    """成员列表响应模式"""
    members: List[ProjectMemberResponse]
    total: int
    page: int
    size: int
    total_pages: int


class AddMemberResponse(BaseModel):
    """添加成员响应模式"""
    success: bool
    message: str
    member: ProjectMemberResponse


class UpdateMemberResponse(BaseModel):
    """更新成员响应模式"""
    success: bool
    message: str
    member: ProjectMemberResponse


class RemoveMemberResponse(BaseModel):
    """移除成员响应模式"""
    success: bool
    message: str
    member_id: int
    removed_at: datetime


class InviteMemberResponse(BaseModel):
    """邀请成员响应模式"""
    success: bool
    message: str
    invitation_id: str
    invited_email: str
    expires_at: datetime


# 工作负载分析相关模式
class MemberWorkload(BaseModel):
    """成员工作负载"""
    user_id: int
    user_info: UserInfo
    current_projects: int
    total_allocation: Decimal
    current_workload: Decimal
    capacity: Decimal
    utilization_rate: Decimal
    overloaded: bool
    available_capacity: Decimal
    
    class Config:
        from_attributes = True


class TeamWorkloadAnalysis(BaseModel):
    """团队工作负载分析"""
    project_id: int
    total_members: int
    total_capacity: Decimal
    total_workload: Decimal
    utilization_rate: Decimal
    member_workloads: List[MemberWorkload]
    overloaded_members: List[MemberWorkload]
    underloaded_members: List[MemberWorkload]
    recommendations: List[str]
    analyzed_at: datetime


# 技能匹配相关模式
class SkillRequirement(BaseModel):
    """技能需求"""
    skill_name: str
    required_level: int = Field(ge=1, le=5, description="技能等级要求(1-5)")
    is_mandatory: bool = Field(True, description="是否必需")
    weight: float = Field(1.0, ge=0, le=1, description="权重(0-1)")


class MemberRecommendation(BaseModel):
    """成员推荐"""
    user_id: int
    user_info: UserInfo
    skill_match_score: float
    workload_score: float
    performance_score: float
    overall_score: float
    recommended_role: ProjectMemberRole
    matching_skills: List[str]
    missing_skills: List[str]
    availability: Dict[str, Any]
    
    class Config:
        from_attributes = True


class SkillMatchRequest(BaseModel):
    """技能匹配请求"""
    skill_requirements: List[SkillRequirement] = Field(..., description="技能需求列表")
    max_recommendations: int = Field(10, ge=1, le=50, description="最大推荐数量")
    include_current_members: bool = Field(False, description="是否包含当前成员")
    min_score_threshold: float = Field(0.6, ge=0, le=1, description="最低评分阈值")


class SkillMatchResponse(BaseModel):
    """技能匹配响应"""
    success: bool
    message: str
    recommendations: List[MemberRecommendation]
    total_candidates: int
    match_criteria: SkillMatchRequest


# 团队统计相关模式
class TeamStatistics(BaseModel):
    """团队统计信息"""
    project_id: int
    total_members: int
    active_members: int
    members_by_role: Dict[str, int]
    members_by_status: Dict[str, int]
    average_allocation: float
    total_hourly_cost: Optional[Decimal]
    skill_distribution: Dict[str, int]
    experience_distribution: Dict[str, int]
    calculated_at: datetime


class TeamPerformanceMetrics(BaseModel):
    """团队绩效指标"""
    project_id: int
    productivity_score: float
    collaboration_score: float
    quality_score: float
    efficiency_score: float
    overall_performance: float
    performance_trends: Dict[str, List[float]]
    top_performers: List[UserInfo]
    improvement_areas: List[str]
    calculated_at: datetime