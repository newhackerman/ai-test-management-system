"""
测试用例管理模块数据模型

本模块定义了测试用例管理相关的数据模型，包括：
- 测试用例基本信息管理
- 测试执行记录管理
- 缺陷管理
- 测试覆盖率管理
- 自动化脚本管理
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Date, JSON, Enum, DECIMAL, Boolean, ForeignKey, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

from .base import Base

class TestCaseType(PyEnum):
    """测试用例类型枚举"""
    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"
    INTEGRATION = "INTEGRATION"
    SYSTEM = "SYSTEM"
    ACCEPTANCE = "ACCEPTANCE"
    REGRESSION = "REGRESSION"
    SMOKE = "SMOKE"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    USABILITY = "USABILITY"

class TestCasePriority(PyEnum):
    """测试用例优先级枚举"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TestCaseStatus(PyEnum):
    """测试用例状态枚举"""
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class ExecutionStatus(PyEnum):
    """执行状态枚举"""
    NOT_EXECUTED = "NOT_EXECUTED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    IN_PROGRESS = "IN_PROGRESS"

class DefectSeverity(PyEnum):
    """缺陷严重程度枚举"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    TRIVIAL = "TRIVIAL"

class DefectStatus(PyEnum):
    """缺陷状态枚举"""
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"
    REJECTED = "REJECTED"

class TestCaseBaseModel(Base):
    """测试用例管理模块基础模型类"""
    __abstract__ = True
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

class TestCase(TestCaseBaseModel):
    """测试用例模型"""
    __tablename__ = 'test_cases'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='测试用例ID')
    case_code = Column(String(50), unique=True, nullable=False, comment='测试用例编码')
    test_plan_id = Column(BigInteger, ForeignKey('test_plans.id'), comment='所属测试计划ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), comment='关联需求ID')
    
    # 测试用例内容
    case_title = Column(String(200), nullable=False, comment='测试用例标题')
    case_description = Column(Text, comment='测试用例描述')
    case_type = Column(Enum(TestCaseType), nullable=False, comment='用例类型')
    
    # 分类信息
    module = Column(String(100), comment='功能模块')
    priority = Column(Enum(TestCasePriority), default=TestCasePriority.MEDIUM, comment='优先级')
    complexity = Column(Enum('SIMPLE', 'MEDIUM', 'COMPLEX'), default='MEDIUM', comment='复杂度')
    automation_level = Column(Enum('MANUAL', 'SEMI_AUTO', 'FULL_AUTO'), default='MANUAL', comment='自动化程度')
    
    # 执行信息
    preconditions = Column(Text, comment='前置条件')
    test_steps = Column(JSON, comment='测试步骤')
    expected_result = Column(Text, comment='预期结果')
    test_data = Column(JSON, comment='测试数据')
    
    # 状态管理
    status = Column(Enum(TestCaseStatus), default=TestCaseStatus.DRAFT, comment='用例状态')
    
    # 人员管理
    creator_id = Column(BigInteger, nullable=False, comment='创建人ID')
    assignee_id = Column(BigInteger, comment='负责人ID')
    reviewer_id = Column(BigInteger, comment='评审人ID')
    
    # 执行统计
    execution_count = Column(Integer, default=0, comment='执行次数')
    pass_count = Column(Integer, default=0, comment='通过次数')
    fail_count = Column(Integer, default=0, comment='失败次数')
    last_execution_date = Column(DateTime, comment='最后执行日期')
    last_execution_status = Column(Enum(ExecutionStatus), default=ExecutionStatus.NOT_EXECUTED, comment='最后执行状态')
    
    # 时间管理
    estimated_execution_time = Column(Integer, comment='预估执行时间(分钟)')
    actual_execution_time = Column(Integer, comment='实际执行时间(分钟)')
    
    # 元数据
    tags = Column(JSON, comment='标签')
    attachments = Column(JSON, comment='附件信息')
    
    # 审计字段
    updated_by = Column(BigInteger, comment='更新人ID')
    version = Column(Integer, default=1, comment='版本号')
    
    # 关联关系
    test_plan = relationship("TestPlan", back_populates="test_cases")
    executions = relationship("TestExecution", back_populates="test_case", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="test_case")
    automation_scripts = relationship("AutomationScript", back_populates="test_case", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_test_cases_code', 'case_code'),
        Index('idx_test_cases_plan', 'test_plan_id'),
        Index('idx_test_cases_requirement', 'requirement_id'),
        Index('idx_test_cases_type', 'case_type'),
        Index('idx_test_cases_priority', 'priority'),
        Index('idx_test_cases_status', 'status'),
        Index('idx_test_cases_assignee', 'assignee_id'),
        Index('idx_test_cases_module', 'module'),
    )
    
    def generate_case_code(self, test_plan_code: str) -> str:
        """生成测试用例编码"""
        import random
        sequence = random.randint(1, 9999)
        return f"TC-{test_plan_code}-{sequence:04d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'case_code': self.case_code,
            'test_plan_id': self.test_plan_id,
            'requirement_id': self.requirement_id,
            'case_title': self.case_title,
            'case_description': self.case_description,
            'case_type': self.case_type.value if self.case_type else None,
            'module': self.module,
            'priority': self.priority.value if self.priority else None,
            'complexity': self.complexity,
            'automation_level': self.automation_level,
            'preconditions': self.preconditions,
            'test_steps': self.test_steps,
            'expected_result': self.expected_result,
            'test_data': self.test_data,
            'status': self.status.value if self.status else None,
            'creator_id': self.creator_id,
            'assignee_id': self.assignee_id,
            'reviewer_id': self.reviewer_id,
            'execution_count': self.execution_count,
            'pass_count': self.pass_count,
            'fail_count': self.fail_count,
            'last_execution_date': self.last_execution_date.isoformat() if self.last_execution_date else None,
            'last_execution_status': self.last_execution_status.value if self.last_execution_status else None,
            'estimated_execution_time': self.estimated_execution_time,
            'actual_execution_time': self.actual_execution_time,
            'tags': self.tags,
            'attachments': self.attachments,
            'updated_by': self.updated_by,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AutomationScript(TestCaseBaseModel):
    """自动化脚本模型"""
    __tablename__ = 'automation_scripts'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='脚本ID')
    test_case_id = Column(BigInteger, ForeignKey('test_cases.id'), nullable=False, comment='测试用例ID')
    
    # 脚本信息
    script_name = Column(String(200), nullable=False, comment='脚本名称')
    framework = Column(Enum('PLAYWRIGHT', 'SELENIUM', 'CYPRESS', 'PYTEST', 'JEST'), 
                      nullable=False, comment='自动化框架')
    language = Column(Enum('PYTHON', 'JAVASCRIPT', 'JAVA', 'CSHARP'), 
                     nullable=False, comment='编程语言')
    
    # 脚本内容
    script_content = Column(Text, nullable=False, comment='脚本内容')
    script_path = Column(String(500), comment='脚本文件路径')
    
    # 配置信息
    browser = Column(String(50), comment='目标浏览器')
    environment_config = Column(JSON, comment='环境配置')
    dependencies = Column(JSON, comment='依赖项')
    
    # 执行信息
    is_active = Column(Boolean, default=True, comment='是否启用')
    last_execution_date = Column(DateTime, comment='最后执行日期')
    last_execution_status = Column(Enum(ExecutionStatus), comment='最后执行状态')
    execution_count = Column(Integer, default=0, comment='执行次数')
    success_count = Column(Integer, default=0, comment='成功次数')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    # 关联关系
    test_case = relationship("TestCase", back_populates="automation_scripts")
    
    # 索引
    __table_args__ = (
        Index('idx_automation_scripts_case', 'test_case_id'),
        Index('idx_automation_scripts_framework', 'framework'),
        Index('idx_automation_scripts_language', 'language'),
        Index('idx_automation_scripts_active', 'is_active'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'test_case_id': self.test_case_id,
            'script_name': self.script_name,
            'framework': self.framework.value if self.framework else None,
            'language': self.language.value if self.language else None,
            'script_content': self.script_content,
            'script_path': self.script_path,
            'browser': self.browser,
            'environment_config': self.environment_config,
            'dependencies': self.dependencies,
            'is_active': self.is_active,
            'last_execution_date': self.last_execution_date.isoformat() if self.last_execution_date else None,
            'last_execution_status': self.last_execution_status.value if self.last_execution_status else None,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TestExecution(TestCaseBaseModel):
    """测试执行记录模型"""
    __tablename__ = 'test_executions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='执行记录ID')
    execution_code = Column(String(50), unique=True, nullable=False, comment='执行编码')
    test_case_id = Column(BigInteger, ForeignKey('test_cases.id'), nullable=False, comment='测试用例ID')
    test_plan_id = Column(BigInteger, ForeignKey('test_plans.id'), comment='测试计划ID')
    
    # 执行信息
    execution_type = Column(Enum('MANUAL', 'AUTOMATED'), nullable=False, comment='执行类型')
    execution_status = Column(Enum(ExecutionStatus), default=ExecutionStatus.NOT_EXECUTED, comment='执行状态')
    
    # 结果信息
    actual_result = Column(Text, comment='实际结果')
    failure_reason = Column(Text, comment='失败原因')
    execution_notes = Column(Text, comment='执行备注')
    
    # 环境信息
    test_environment = Column(String(100), comment='测试环境')
    browser_info = Column(String(200), comment='浏览器信息')
    os_info = Column(String(100), comment='操作系统信息')
    
    # 时间信息
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    duration = Column(Integer, comment='执行时长(秒)')
    
    # 人员信息
    executor_id = Column(BigInteger, nullable=False, comment='执行人ID')
    
    # 附件信息
    screenshots = Column(JSON, comment='截图信息')
    logs = Column(JSON, comment='日志信息')
    videos = Column(JSON, comment='视频信息')
    
    # 关联关系
    test_case = relationship("TestCase", back_populates="executions")
    test_plan = relationship("TestPlan", back_populates="test_executions")
    
    # 索引
    __table_args__ = (
        Index('idx_test_executions_code', 'execution_code'),
        Index('idx_test_executions_case', 'test_case_id'),
        Index('idx_test_executions_plan', 'test_plan_id'),
        Index('idx_test_executions_status', 'execution_status'),
        Index('idx_test_executions_executor', 'executor_id'),
        Index('idx_test_executions_started', 'started_at'),
        Index('idx_test_executions_type', 'execution_type'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )
    
    def generate_execution_code(self, test_case_code: str) -> str:
        """生成执行编码"""
        import random
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        sequence = random.randint(1, 999)
        return f"EX-{test_case_code}-{timestamp}-{sequence:03d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'execution_code': self.execution_code,
            'test_case_id': self.test_case_id,
            'test_plan_id': self.test_plan_id,
            'execution_type': self.execution_type.value if self.execution_type else None,
            'execution_status': self.execution_status.value if self.execution_status else None,
            'actual_result': self.actual_result,
            'failure_reason': self.failure_reason,
            'execution_notes': self.execution_notes,
            'test_environment': self.test_environment,
            'browser_info': self.browser_info,
            'os_info': self.os_info,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'executor_id': self.executor_id,
            'screenshots': self.screenshots,
            'logs': self.logs,
            'videos': self.videos,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DefectType(PyEnum):
    """缺陷类型枚举"""
    FUNCTIONAL = "FUNCTIONAL"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    USABILITY = "USABILITY"
    COMPATIBILITY = "COMPATIBILITY"
    DATA = "DATA"
    INTERFACE = "INTERFACE"


class DefectResolution(PyEnum):
    """缺陷解决方案枚举"""
    FIXED = "FIXED"
    DUPLICATE = "DUPLICATE"
    NOT_A_BUG = "NOT_A_BUG"
    WONT_FIX = "WONT_FIX"
    CANNOT_REPRODUCE = "CANNOT_REPRODUCE"
    DEFERRED = "DEFERRED"


class Defect(TestCaseBaseModel):
    """缺陷模型"""
    __tablename__ = 'defects'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='缺陷ID')
    defect_code = Column(String(50), unique=True, nullable=False, comment='缺陷编码')
    test_execution_id = Column(BigInteger, ForeignKey('test_executions.id'), comment='关联测试执行ID')
    test_case_id = Column(BigInteger, ForeignKey('test_cases.id'), comment='关联测试用例ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), comment='关联需求ID')
    
    # 缺陷内容
    title = Column(String(200), nullable=False, comment='缺陷标题')
    description = Column(Text, nullable=False, comment='缺陷描述')
    steps_to_reproduce = Column(Text, comment='重现步骤')
    
    # 分类信息
    defect_type = Column(Enum(DefectType), nullable=False, comment='缺陷类型')
    severity = Column(Enum(DefectSeverity), nullable=False, comment='严重程度')
    priority = Column(Enum(TestCasePriority), nullable=False, comment='优先级')
    
    # 状态管理
    status = Column(Enum(DefectStatus), default=DefectStatus.NEW, comment='缺陷状态')
    resolution = Column(Enum(DefectResolution), comment='解决方案')
    
    # 环境信息
    found_in_version = Column(String(50), comment='发现版本')
    fixed_in_version = Column(String(50), comment='修复版本')
    test_environment = Column(String(100), comment='测试环境')
    
    # 人员管理
    reporter_id = Column(BigInteger, nullable=False, comment='报告人ID')
    assignee_id = Column(BigInteger, comment='分配人ID')
    resolver_id = Column(BigInteger, comment='解决人ID')
    
    # 时间管理
    reported_at = Column(DateTime, default=datetime.utcnow, comment='报告时间')
    assigned_at = Column(DateTime, comment='分配时间')
    resolved_at = Column(DateTime, comment='解决时间')
    verified_at = Column(DateTime, comment='验证时间')
    
    # 附件信息
    attachments = Column(JSON, comment='附件信息')
    
    # 关联关系
    test_case = relationship("TestCase", back_populates="defects")
    test_execution = relationship("TestExecution")
    comments = relationship("DefectComment", back_populates="defect", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_defects_code', 'defect_code'),
        Index('idx_defects_execution', 'test_execution_id'),
        Index('idx_defects_case', 'test_case_id'),
        Index('idx_defects_requirement', 'requirement_id'),
        Index('idx_defects_status', 'status'),
        Index('idx_defects_severity', 'severity'),
        Index('idx_defects_priority', 'priority'),
        Index('idx_defects_assignee', 'assignee_id'),
        Index('idx_defects_reported', 'reported_at'),
        Index('idx_defects_type', 'defect_type'),
    )
    
    def generate_defect_code(self, project_code: str) -> str:
        """生成缺陷编码"""
        today = datetime.now().strftime("%Y%m%d")
        import random
        sequence = random.randint(1, 9999)
        return f"BUG-{project_code}-{today}-{sequence:04d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'defect_code': self.defect_code,
            'test_execution_id': self.test_execution_id,
            'test_case_id': self.test_case_id,
            'requirement_id': self.requirement_id,
            'title': self.title,
            'description': self.description,
            'steps_to_reproduce': self.steps_to_reproduce,
            'defect_type': self.defect_type.value if self.defect_type else None,
            'severity': self.severity.value if self.severity else None,
            'priority': self.priority.value if self.priority else None,
            'status': self.status.value if self.status else None,
            'resolution': self.resolution.value if self.resolution else None,
            'found_in_version': self.found_in_version,
            'fixed_in_version': self.fixed_in_version,
            'test_environment': self.test_environment,
            'reporter_id': self.reporter_id,
            'assignee_id': self.assignee_id,
            'resolver_id': self.resolver_id,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TestCoverage(TestCaseBaseModel):
    """测试覆盖率模型"""
    __tablename__ = 'test_coverage'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='覆盖率记录ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), comment='需求ID')
    
    # 覆盖率统计
    total_test_cases = Column(Integer, default=0, comment='总测试用例数')
    executed_test_cases = Column(Integer, default=0, comment='已执行测试用例数')
    passed_test_cases = Column(Integer, default=0, comment='通过测试用例数')
    failed_test_cases = Column(Integer, default=0, comment='失败测试用例数')
    
    # 覆盖率百分比
    execution_coverage = Column(DECIMAL(5, 2), default=0.00, comment='执行覆盖率')
    pass_rate = Column(DECIMAL(5, 2), default=0.00, comment='通过率')
    
    # 需求覆盖率
    requirements_covered = Column(Integer, default=0, comment='已覆盖需求数')
    requirements_total = Column(Integer, default=0, comment='总需求数')
    requirement_coverage = Column(DECIMAL(5, 2), default=0.00, comment='需求覆盖率')
    
    # 统计时间
    coverage_date = Column(Date, nullable=False, comment='统计日期')
    
    # 关联关系
    # project = relationship("Project")  # 避免循环导入
    # requirement = relationship("Requirement")  # 避免循环导入
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'requirement_id': self.requirement_id,
            'total_test_cases': self.total_test_cases,
            'executed_test_cases': self.executed_test_cases,
            'passed_test_cases': self.passed_test_cases,
            'failed_test_cases': self.failed_test_cases,
            'execution_coverage': float(self.execution_coverage) if self.execution_coverage else 0.0,
            'pass_rate': float(self.pass_rate) if self.pass_rate else 0.0,
            'requirements_covered': self.requirements_covered,
            'requirements_total': self.requirements_total,
            'requirement_coverage': float(self.requirement_coverage) if self.requirement_coverage else 0.0,
            'coverage_date': self.coverage_date.isoformat() if self.coverage_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
