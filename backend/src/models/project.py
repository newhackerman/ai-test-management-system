"""
项目管理模块数据模型

本模块定义了项目管理相关的数据模型，包括：
- 项目基本信息管理
- 项目成员管理
- 任务管理
- 里程碑管理
- 工作日志管理
- 项目风险管理
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Date, JSON, Enum, DECIMAL, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from .base import Base
from sqlalchemy.ext.declarative import declarative_base


class ProjectStatus(PyEnum):
    """项目状态枚举"""
    PLANNING = "PLANNING"           # 规划中
    IN_PROGRESS = "IN_PROGRESS"     # 进行中
    ON_HOLD = "ON_HOLD"             # 暂停
    COMPLETED = "COMPLETED"         # 已完成
    CANCELLED = "CANCELLED"         # 已取消
    ARCHIVED = "ARCHIVED"           # 已归档


class ProjectPriority(PyEnum):
    """项目优先级枚举"""
    LOW = "LOW"                     # 低
    MEDIUM = "MEDIUM"               # 中
    HIGH = "HIGH"                   # 高
    URGENT = "URGENT"               # 紧急


class ProjectType(PyEnum):
    """项目类型枚举"""
    BUSINESS_SYSTEM = "BUSINESS_SYSTEM"     # 业务系统
    MOBILE_APP = "MOBILE_APP"               # 移动应用
    API_SERVICE = "API_SERVICE"             # 接口服务
    DATA_AI = "DATA_AI"                     # 数据/AI
    INFRASTRUCTURE = "INFRASTRUCTURE"       # 基础设施
    INTERNAL_TOOL = "INTERNAL_TOOL"         # 内部工具

    # 历史兼容：旧版本把测试类型误用为项目类型
    FUNCTIONAL = "FUNCTIONAL"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    AUTOMATION = "AUTOMATION"
    INTEGRATION = "INTEGRATION"


class RiskLevel(PyEnum):
    """风险等级枚举"""
    LOW = "LOW"                     # 低风险
    MEDIUM = "MEDIUM"               # 中风险
    HIGH = "HIGH"                   # 高风险
    CRITICAL = "CRITICAL"           # 严重风险

class ProjectBaseModel(Base):
    """项目管理模块基础模型类"""
    __abstract__ = True
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

class Project(ProjectBaseModel):
    """项目模型 - 根据项目管理模块规范设计"""
    __tablename__ = 'projects'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='项目ID')
    project_code = Column(String(50), nullable=False, unique=True, comment='项目编码')
    project_name = Column(String(200), nullable=False, comment='项目名称')
    description = Column(Text, comment='项目描述')
    
    # 项目分类
    project_type = Column(Enum(ProjectType), nullable=False, comment='项目类型')
    priority = Column(Enum(ProjectPriority), default=ProjectPriority.MEDIUM, comment='项目优先级')
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING, comment='项目状态')
    
    # 健康度和风险
    health_score = Column(Integer, default=100, comment='项目健康度(0-100)')
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW, comment='风险等级')
    
    # 时间管理
    planned_start_date = Column(Date, comment='计划开始日期')
    planned_end_date = Column(Date, comment='计划结束日期')
    actual_start_date = Column(Date, comment='实际开始日期')
    actual_end_date = Column(Date, comment='实际结束日期')
    
    # 人员管理
    project_manager_id = Column(BigInteger, nullable=False, comment='项目经理ID')
    test_manager_id = Column(BigInteger, comment='测试经理ID')
    client_contact = Column(String(200), comment='客户联系人')
    
    # 预算管理
    budget = Column(DECIMAL(15, 2), comment='项目预算')
    actual_cost = Column(DECIMAL(15, 2), default=0.00, comment='实际成本')
    
    # 进度管理
    progress_percentage = Column(DECIMAL(5, 2), default=0.00, comment='完成百分比')
    task_count = Column(Integer, default=0, comment='任务总数')
    completed_task_count = Column(Integer, default=0, comment='已完成任务数')
    
    # 质量管理
    test_case_count = Column(Integer, default=0, comment='测试用例总数')
    passed_test_count = Column(Integer, default=0, comment='通过测试数')
    defect_count = Column(Integer, default=0, comment='缺陷总数')
    
    # 元数据
    tags = Column(JSON, comment='项目标签')
    custom_fields = Column(JSON, comment='自定义字段')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    deleted_at = Column(DateTime, comment='删除时间')
    
    # 关联关系
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    work_logs = relationship("WorkLog", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("ProjectRisk", back_populates="project", cascade="all, delete-orphan")
    
    # 保留原有关联关系以兼容现有代码
    requirements = relationship("Requirement", back_populates="project")
    
    # 在线会议模块关联关系
    meetings = relationship("Meeting", back_populates="project", cascade="all, delete-orphan")
    
    # 新增测试相关关联关系 - 使用字符串引用避免循环导入
    # test_cases = relationship("TestCase", back_populates="project")
    # defects = relationship("Defect", back_populates="project")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_code': self.project_code,
            'project_name': self.project_name,
            'description': self.description,
            'project_type': self.project_type,
            'priority': self.priority,
            'status': self.status,
            'health_score': self.health_score,
            'risk_level': self.risk_level,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'project_manager_id': self.project_manager_id,
            'test_manager_id': self.test_manager_id,
            'client_contact': self.client_contact,
            'budget': float(self.budget) if self.budget else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else 0.0,
            'progress_percentage': float(self.progress_percentage) if self.progress_percentage else 0.0,
            'task_count': self.task_count,
            'completed_task_count': self.completed_task_count,
            'test_case_count': self.test_case_count,
            'passed_test_count': self.passed_test_count,
            'defect_count': self.defect_count,
            'tags': self.tags,
            'custom_fields': self.custom_fields,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }


class ProjectMember(ProjectBaseModel):
    """项目成员模型"""
    __tablename__ = 'project_members'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='成员关系ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    
    # 角色和权限
    role_in_project = Column(Enum('ADMIN', 'PROJECT_MANAGER', 'REQUIREMENT_MANAGER', 'DESIGNER', 
                                 'ARCHITECT', 'DEVELOPER', 'TESTER', 'DEVOPS', 'THIRD_PARTY'), 
                            nullable=False, comment='项目内角色')
    allocation_percentage = Column(DECIMAL(5, 2), default=100.00, comment='参与度百分比')
    hourly_rate = Column(DECIMAL(8, 2), comment='小时费率')
    
    # 时间管理
    join_date = Column(Date, nullable=False, comment='加入日期')
    leave_date = Column(Date, comment='离开日期')
    status = Column(Enum('ACTIVE', 'INACTIVE', 'ON_LEAVE'), default='ACTIVE', comment='成员状态')
    
    # 技能和职责
    skills = Column(JSON, comment='技能标签')
    responsibilities = Column(Text, comment='职责描述')
    
    # 关联关系
    project = relationship("Project", back_populates="members")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role_in_project': self.role_in_project,
            'allocation_percentage': float(self.allocation_percentage) if self.allocation_percentage else 100.0,
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else None,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'leave_date': self.leave_date.isoformat() if self.leave_date else None,
            'status': self.status,
            'skills': self.skills,
            'responsibilities': self.responsibilities,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Task(ProjectBaseModel):
    """任务模型"""
    __tablename__ = 'project_tasks'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='任务ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    task_code = Column(String(50), comment='任务编码')
    task_name = Column(String(200), nullable=False, comment='任务名称')
    description = Column(Text, comment='任务描述')
    
    # 任务分类
    task_type = Column(Enum('REQUIREMENT_ANALYSIS', 'TEST_DESIGN', 'TEST_EXECUTION', 
                           'AUTOMATION_DEVELOPMENT', 'PERFORMANCE_TEST', 'SECURITY_TEST', 
                           'ENVIRONMENT_SETUP', 'DOCUMENTATION'), 
                      nullable=False, comment='任务类型')
    priority = Column(Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT'), 
                     default='MEDIUM', comment='任务优先级')
    status = Column(Enum('TODO', 'ASSIGNED', 'IN_PROGRESS', 'ON_HOLD', 'BLOCKED', 
                        'PENDING_REVIEW', 'COMPLETED', 'CANCELLED'), 
                   default='TODO', comment='任务状态')
    
    # 人员分配
    assignee_id = Column(BigInteger, comment='执行人ID')
    assignee_ids = Column(JSON, comment='执行人ID列表')
    reporter_id = Column(BigInteger, comment='报告人ID')
    reviewer_id = Column(BigInteger, comment='审核人ID')
    
    # 时间管理
    planned_start_date = Column(Date, comment='计划开始日期')
    planned_end_date = Column(Date, comment='计划结束日期')
    actual_start_date = Column(Date, comment='实际开始日期')
    actual_end_date = Column(Date, comment='实际结束日期')
    
    # 工时管理
    estimated_hours = Column(DECIMAL(6, 2), comment='预估工时')
    actual_hours = Column(DECIMAL(6, 2), default=0.00, comment='实际工时')
    remaining_hours = Column(DECIMAL(6, 2), comment='剩余工时')
    
    # 依赖关系
    parent_task_id = Column(BigInteger, comment='父任务ID')
    dependency_tasks = Column(JSON, comment='依赖任务ID列表')
    
    # 质量管理
    acceptance_criteria = Column(Text, comment='验收标准')
    test_case_count = Column(Integer, default=0, comment='关联测试用例数')
    defect_count = Column(Integer, default=0, comment='发现缺陷数')
    
    # 元数据
    tags = Column(JSON, comment='任务标签')
    attachments = Column(JSON, comment='附件信息')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    # 关联关系
    project = relationship("Project", back_populates="tasks")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_code': self.task_code,
            'task_name': self.task_name,
            'description': self.description,
            'task_type': self.task_type,
            'priority': self.priority,
            'status': self.status,
            'assignee_id': self.assignee_id,
            'assignee_ids': self.assignee_ids,
            'reporter_id': self.reporter_id,
            'reviewer_id': self.reviewer_id,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'estimated_hours': float(self.estimated_hours) if self.estimated_hours else None,
            'actual_hours': float(self.actual_hours) if self.actual_hours else 0.0,
            'remaining_hours': float(self.remaining_hours) if self.remaining_hours else None,
            'parent_task_id': self.parent_task_id,
            'dependency_tasks': self.dependency_tasks,
            'acceptance_criteria': self.acceptance_criteria,
            'test_case_count': self.test_case_count,
            'defect_count': self.defect_count,
            'tags': self.tags,
            'attachments': self.attachments,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Milestone(ProjectBaseModel):
    """里程碑模型"""
    __tablename__ = 'project_milestones'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='里程碑ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    milestone_name = Column(String(200), nullable=False, comment='里程碑名称')
    description = Column(Text, comment='里程碑描述')
    
    # 里程碑类型
    milestone_type = Column(Enum('REQUIREMENT', 'DESIGN', 'EXECUTION', 'DELIVERY'), 
                           nullable=False, comment='里程碑类型')
    
    # 时间管理
    planned_date = Column(Date, nullable=False, comment='计划日期')
    actual_date = Column(Date, comment='实际日期')
    
    # 状态管理
    status = Column(Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE', 'CANCELLED'), 
                   default='PENDING', comment='里程碑状态')
    
    # 交付物
    deliverables = Column(JSON, comment='交付物清单')
    acceptance_criteria = Column(Text, comment='验收标准')
    
    # 负责人
    owner_id = Column(BigInteger, nullable=False, comment='负责人ID')
    
    # 依赖关系
    dependency_milestones = Column(JSON, comment='依赖里程碑ID列表')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    deleted_at = Column(DateTime, nullable=True, comment='软删除时间')

    # 关联关系
    project = relationship("Project", back_populates="milestones")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'milestone_name': self.milestone_name,
            'description': self.description,
            'milestone_type': self.milestone_type,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'status': self.status,
            'deliverables': self.deliverables,
            'acceptance_criteria': self.acceptance_criteria,
            'owner_id': self.owner_id,
            'dependency_milestones': self.dependency_milestones,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkLog(ProjectBaseModel):
    """工作日志模型"""
    __tablename__ = 'work_logs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='工作日志ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    task_id = Column(BigInteger, ForeignKey('project_tasks.id'), comment='任务ID')
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    
    # 工时信息
    work_date = Column(Date, nullable=False, comment='工作日期')
    hours_worked = Column(DECIMAL(4, 2), nullable=False, comment='工作小时数')
    work_type = Column(Enum('DEVELOPMENT', 'TESTING', 'ANALYSIS', 'DESIGN', 'MEETING', 
                           'DOCUMENTATION', 'OTHER'), 
                      nullable=False, comment='工作类型')
    
    # 工作内容
    description = Column(Text, nullable=False, comment='工作描述')
    achievements = Column(Text, comment='工作成果')
    issues_encountered = Column(Text, comment='遇到的问题')
    
    # 状态
    status = Column(Enum('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'), 
                   default='DRAFT', comment='日志状态')
    approved_by = Column(Integer, comment='审批人ID')
    approved_at = Column(DateTime, comment='审批时间')
    
    # 关联关系
    project = relationship("Project", back_populates="work_logs")
    task = relationship("Task")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'work_date': self.work_date.isoformat() if self.work_date else None,
            'hours_worked': float(self.hours_worked) if self.hours_worked else 0.0,
            'work_type': self.work_type,
            'description': self.description,
            'achievements': self.achievements,
            'issues_encountered': self.issues_encountered,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectRisk(ProjectBaseModel):
    """项目风险模型"""
    __tablename__ = 'project_risks'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='风险ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    risk_name = Column(String(200), nullable=False, comment='风险名称')
    description = Column(Text, nullable=False, comment='风险描述')
    
    # 风险分类
    risk_category = Column(Enum('SCHEDULE', 'QUALITY', 'RESOURCE', 'TECHNICAL', 'EXTERNAL'), 
                          nullable=False, comment='风险类别')
    risk_level = Column(Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                       nullable=False, comment='风险等级')
    
    # 概率和影响
    probability = Column(DECIMAL(3, 2), nullable=False, comment='发生概率(0.00-1.00)')
    impact_score = Column(Integer, nullable=False, comment='影响评分(1-10)')
    risk_score = Column(DECIMAL(4, 2), comment='风险评分(计算得出)')
    
    # 应对策略
    mitigation_strategy = Column(Enum('AVOID', 'MITIGATE', 'TRANSFER', 'ACCEPT'), 
                                nullable=False, comment='应对策略')
    mitigation_plan = Column(Text, comment='缓解计划')
    contingency_plan = Column(Text, comment='应急计划')
    
    # 状态管理
    status = Column(Enum('IDENTIFIED', 'ANALYZING', 'MITIGATING', 'MONITORING', 'CLOSED'), 
                   default='IDENTIFIED', comment='风险状态')
    
    # 负责人
    owner_id = Column(BigInteger, nullable=False, comment='风险负责人ID')
    
    # 时间信息
    identified_date = Column(Date, nullable=False, comment='识别日期')
    target_resolution_date = Column(Date, comment='目标解决日期')
    actual_resolution_date = Column(Date, comment='实际解决日期')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    # 关联关系
    project = relationship("Project", back_populates="risks")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'risk_name': self.risk_name,
            'description': self.description,
            'risk_category': self.risk_category,
            'risk_level': self.risk_level,
            'probability': float(self.probability) if self.probability else 0.0,
            'impact_score': self.impact_score,
            'risk_score': float(self.risk_score) if self.risk_score else 0.0,
            'mitigation_strategy': self.mitigation_strategy,
            'mitigation_plan': self.mitigation_plan,
            'contingency_plan': self.contingency_plan,
            'status': self.status,
            'owner_id': self.owner_id,
            'identified_date': self.identified_date.isoformat() if self.identified_date else None,
            'target_resolution_date': self.target_resolution_date.isoformat() if self.target_resolution_date else None,
            'actual_resolution_date': self.actual_resolution_date.isoformat() if self.actual_resolution_date else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# TestCase and Defect models are now in test_case.py to avoid conflicts


class ProjectMetrics(ProjectBaseModel):
    """项目指标模型"""
    __tablename__ = 'project_metrics'
    
    id = Column(BigInteger, primary_key=True, comment='指标ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    metric_date = Column(DateTime, default=datetime.utcnow, comment='指标日期')
    
    # 需求指标
    requirements_total = Column(Integer, default=0, comment='需求总数')
    requirements_completed = Column(Integer, default=0, comment='已完成需求数')
    requirements_coverage = Column(Float, comment='需求覆盖率')
    requirements_quality_score = Column(Float, comment='需求质量评分')
    
    # 测试指标
    test_cases_total = Column(Integer, default=0, comment='测试用例总数')
    test_cases_executed = Column(Integer, default=0, comment='已执行测试用例数')
    test_cases_passed = Column(Integer, default=0, comment='通过的测试用例数')
    test_coverage = Column(Float, comment='测试覆盖率')
    automation_rate = Column(Float, comment='自动化率')
    
    # 质量指标
    defects_total = Column(Integer, default=0, comment='缺陷总数')
    defects_open = Column(Integer, default=0, comment='未解决缺陷数')
    defects_critical = Column(Integer, default=0, comment='严重缺陷数')
    defect_density = Column(Float, comment='缺陷密度')
    defect_resolution_time = Column(Float, comment='平均缺陷解决时间')
    
    # 进度指标
    progress_percentage = Column(Float, comment='项目进度百分比')
    milestone_completion = Column(Float, comment='里程碑完成率')
    schedule_variance = Column(Float, comment='进度偏差')
    
    # 团队指标
    team_velocity = Column(Float, comment='团队速度')
    team_productivity = Column(Float, comment='团队生产力')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'metric_date': self.metric_date.isoformat() if self.metric_date else None,
            'requirements_total': self.requirements_total,
            'requirements_completed': self.requirements_completed,
            'requirements_coverage': self.requirements_coverage,
            'requirements_quality_score': self.requirements_quality_score,
            'test_cases_total': self.test_cases_total,
            'test_cases_executed': self.test_cases_executed,
            'test_cases_passed': self.test_cases_passed,
            'test_coverage': self.test_coverage,
            'automation_rate': self.automation_rate,
            'defects_total': self.defects_total,
            'defects_open': self.defects_open,
            'defects_critical': self.defects_critical,
            'defect_density': self.defect_density,
            'defect_resolution_time': self.defect_resolution_time,
            'progress_percentage': self.progress_percentage,
            'milestone_completion': self.milestone_completion,
            'schedule_variance': self.schedule_variance,
            'team_velocity': self.team_velocity,
            'team_productivity': self.team_productivity,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectChangeHistory(Base):
    """项目变更历史模型"""
    __tablename__ = 'project_change_history'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='变更记录ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    change_type = Column(Enum('CREATE', 'UPDATE', 'DELETE', 'STATUS_CHANGE', 'MEMBER_CHANGE'), 
                        nullable=False, comment='变更类型')
    field_name = Column(String(100), comment='变更字段名')
    old_value = Column(Text, comment='旧值')
    new_value = Column(Text, comment='新值')
    change_reason = Column(Text, comment='变更原因')
    change_description = Column(Text, comment='变更描述')
    
    # 变更人信息
    changed_by = Column(Integer, nullable=False, comment='变更人ID')
    change_time = Column(DateTime, nullable=False, default=datetime.utcnow, comment='变更时间')
    ip_address = Column(String(45), comment='变更IP地址')
    user_agent = Column(String(500), comment='用户代理')
    
    # 关联关系
    project = relationship("Project")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'change_type': self.change_type,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'change_reason': self.change_reason,
            'change_description': self.change_description,
            'changed_by': self.changed_by,
            'change_time': self.change_time.isoformat() if self.change_time else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }


class ProjectStatistics(Base):
    """项目统计模型"""
    __tablename__ = 'project_statistics'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='统计记录ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    stat_date = Column(Date, nullable=False, comment='统计日期')
    stat_type = Column(Enum('DAILY', 'WEEKLY', 'MONTHLY'), nullable=False, comment='统计类型')
    
    # 进度统计
    time_progress = Column(DECIMAL(5, 2), comment='时间进度百分比')
    task_progress = Column(DECIMAL(5, 2), comment='任务进度百分比')
    quality_progress = Column(DECIMAL(5, 2), comment='质量进度百分比')
    overall_progress = Column(DECIMAL(5, 2), comment='整体进度百分比')
    
    # 任务统计
    total_tasks = Column(Integer, default=0, comment='任务总数')
    completed_tasks = Column(Integer, default=0, comment='已完成任务数')
    in_progress_tasks = Column(Integer, default=0, comment='进行中任务数')
    overdue_tasks = Column(Integer, default=0, comment='逾期任务数')
    
    # 人员统计
    total_members = Column(Integer, default=0, comment='团队成员总数')
    active_members = Column(Integer, default=0, comment='活跃成员数')
    total_work_hours = Column(DECIMAL(8, 2), default=0.00, comment='总工时')
    avg_utilization_rate = Column(DECIMAL(5, 2), comment='平均利用率')
    
    # 质量统计
    total_defects = Column(Integer, default=0, comment='缺陷总数')
    open_defects = Column(Integer, default=0, comment='未解决缺陷数')
    critical_defects = Column(Integer, default=0, comment='严重缺陷数')
    defect_density = Column(DECIMAL(6, 3), comment='缺陷密度')
    
    # 风险统计
    total_risks = Column(Integer, default=0, comment='风险总数')
    high_risks = Column(Integer, default=0, comment='高风险数')
    avg_risk_score = Column(DECIMAL(4, 2), comment='平均风险评分')
    
    # 成本统计
    planned_cost = Column(DECIMAL(15, 2), comment='计划成本')
    actual_cost = Column(DECIMAL(15, 2), comment='实际成本')
    cost_variance = Column(DECIMAL(15, 2), comment='成本偏差')
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment='创建时间')
    
    # 关联关系
    project = relationship("Project")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'stat_date': self.stat_date.isoformat() if self.stat_date else None,
            'stat_type': self.stat_type,
            'time_progress': float(self.time_progress) if self.time_progress else None,
            'task_progress': float(self.task_progress) if self.task_progress else None,
            'quality_progress': float(self.quality_progress) if self.quality_progress else None,
            'overall_progress': float(self.overall_progress) if self.overall_progress else None,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'in_progress_tasks': self.in_progress_tasks,
            'overdue_tasks': self.overdue_tasks,
            'total_members': self.total_members,
            'active_members': self.active_members,
            'total_work_hours': float(self.total_work_hours) if self.total_work_hours else 0.0,
            'avg_utilization_rate': float(self.avg_utilization_rate) if self.avg_utilization_rate else None,
            'total_defects': self.total_defects,
            'open_defects': self.open_defects,
            'critical_defects': self.critical_defects,
            'defect_density': float(self.defect_density) if self.defect_density else None,
            'total_risks': self.total_risks,
            'high_risks': self.high_risks,
            'avg_risk_score': float(self.avg_risk_score) if self.avg_risk_score else None,
            'planned_cost': float(self.planned_cost) if self.planned_cost else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else None,
            'cost_variance': float(self.cost_variance) if self.cost_variance else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
