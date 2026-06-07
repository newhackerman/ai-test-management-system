"""
测试计划管理数据模型

本模块定义了测试计划管理相关的数据模型，包括：
- 测试计划基本信息管理
- 测试阶段管理
- 测试资源分配
- 测试进度跟踪
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Date, JSON, Enum, DECIMAL, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import Base


class TestType(PyEnum):
    """测试类型枚举"""
    FUNCTIONAL = "FUNCTIONAL"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    INTEGRATION = "INTEGRATION"
    REGRESSION = "REGRESSION"
    ACCEPTANCE = "ACCEPTANCE"


class TestPlanStatus(PyEnum):
    """测试计划状态枚举"""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TestPhaseStatus(PyEnum):
    """测试阶段状态枚举"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class TestPlan(Base):
    """测试计划模型"""
    __tablename__ = 'test_plans'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='测试计划ID')
    plan_code = Column(String(50), unique=True, nullable=False, comment='测试计划编码')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='所属项目ID')
    plan_name = Column(String(200), nullable=False, comment='测试计划名称')
    description = Column(Text, comment='测试计划描述')
    
    # 计划信息
    test_type = Column(Enum(TestType), nullable=False, comment='测试类型')
    test_strategy = Column(Text, comment='测试策略')
    test_scope = Column(Text, comment='测试范围')
    
    # 状态管理
    status = Column(Enum(TestPlanStatus), default=TestPlanStatus.DRAFT, comment='计划状态')
    
    # 时间管理
    planned_start_date = Column(Date, comment='计划开始日期')
    planned_end_date = Column(Date, comment='计划结束日期')
    actual_start_date = Column(Date, comment='实际开始日期')
    actual_end_date = Column(Date, comment='实际结束日期')
    
    # 人员管理
    test_manager_id = Column(BigInteger, nullable=False, comment='测试经理ID')
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    # 进度管理
    total_cases = Column(Integer, default=0, comment='总用例数')
    executed_cases = Column(Integer, default=0, comment='已执行用例数')
    passed_cases = Column(Integer, default=0, comment='通过用例数')
    failed_cases = Column(Integer, default=0, comment='失败用例数')
    
    # 质量指标
    pass_rate = Column(DECIMAL(5, 2), default=0.00, comment='通过率')
    execution_rate = Column(DECIMAL(5, 2), default=0.00, comment='执行率')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    test_cases = relationship("TestCase", back_populates="test_plan", cascade="all, delete-orphan")
    test_phases = relationship("TestPhase", back_populates="test_plan", cascade="all, delete-orphan")
    test_executions = relationship("TestExecution", back_populates="test_plan")
    
    # 索引
    __table_args__ = (
        Index('idx_test_plans_code', 'plan_code'),
        Index('idx_test_plans_project', 'project_id'),
        Index('idx_test_plans_status', 'status'),
        Index('idx_test_plans_type', 'test_type'),
        Index('idx_test_plans_manager', 'test_manager_id'),
        Index('idx_test_plans_created_at', 'created_at'),
    )
    
    def generate_plan_code(self, project_code: str) -> str:
        """生成测试计划编码"""
        today = datetime.now().strftime("%Y%m%d")
        # 这里应该查询数据库获取当天的计划数量，简化处理
        import random
        sequence = random.randint(1, 999)
        return f"TP-{project_code}-{today}-{sequence:03d}"
    
    def update_progress(self):
        """更新测试进度"""
        if self.total_cases > 0:
            self.execution_rate = (self.executed_cases / self.total_cases) * 100
            if self.executed_cases > 0:
                self.pass_rate = (self.passed_cases / self.executed_cases) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'plan_code': self.plan_code,
            'project_id': self.project_id,
            'plan_name': self.plan_name,
            'description': self.description,
            'test_type': self.test_type.value if self.test_type else None,
            'test_strategy': self.test_strategy,
            'test_scope': self.test_scope,
            'status': self.status.value if self.status else None,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'test_manager_id': self.test_manager_id,
            'created_by': self.created_by,
            'total_cases': self.total_cases,
            'executed_cases': self.executed_cases,
            'passed_cases': self.passed_cases,
            'failed_cases': self.failed_cases,
            'pass_rate': float(self.pass_rate) if self.pass_rate else 0.0,
            'execution_rate': float(self.execution_rate) if self.execution_rate else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TestPhase(Base):
    """测试阶段模型"""
    __tablename__ = 'test_phases'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='测试阶段ID')
    test_plan_id = Column(BigInteger, ForeignKey('test_plans.id'), nullable=False, comment='测试计划ID')
    phase_name = Column(String(100), nullable=False, comment='阶段名称')
    description = Column(Text, comment='阶段描述')
    
    # 阶段类型
    phase_type = Column(Enum('UNIT_TEST', 'INTEGRATION_TEST', 'SYSTEM_TEST', 'ACCEPTANCE_TEST', 'REGRESSION_TEST'), 
                       nullable=False, comment='阶段类型')
    
    # 状态管理
    status = Column(Enum(TestPhaseStatus), default=TestPhaseStatus.PENDING, comment='阶段状态')
    
    # 时间管理
    planned_start_date = Column(Date, comment='计划开始日期')
    planned_end_date = Column(Date, comment='计划结束日期')
    actual_start_date = Column(Date, comment='实际开始日期')
    actual_end_date = Column(Date, comment='实际结束日期')
    
    # 进入和退出标准
    entry_criteria = Column(Text, comment='进入标准')
    exit_criteria = Column(Text, comment='退出标准')
    
    # 进度管理
    total_cases = Column(Integer, default=0, comment='阶段用例总数')
    executed_cases = Column(Integer, default=0, comment='已执行用例数')
    passed_cases = Column(Integer, default=0, comment='通过用例数')
    failed_cases = Column(Integer, default=0, comment='失败用例数')
    
    # 负责人
    phase_manager_id = Column(BigInteger, comment='阶段负责人ID')
    
    # 依赖关系
    dependency_phases = Column(JSON, comment='依赖阶段ID列表')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    test_plan = relationship("TestPlan", back_populates="test_phases")
    
    # 索引
    __table_args__ = (
        Index('idx_test_phases_plan', 'test_plan_id'),
        Index('idx_test_phases_status', 'status'),
        Index('idx_test_phases_type', 'phase_type'),
        Index('idx_test_phases_manager', 'phase_manager_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'test_plan_id': self.test_plan_id,
            'phase_name': self.phase_name,
            'description': self.description,
            'phase_type': self.phase_type,
            'status': self.status.value if self.status else None,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'entry_criteria': self.entry_criteria,
            'exit_criteria': self.exit_criteria,
            'total_cases': self.total_cases,
            'executed_cases': self.executed_cases,
            'passed_cases': self.passed_cases,
            'failed_cases': self.failed_cases,
            'phase_manager_id': self.phase_manager_id,
            'dependency_phases': self.dependency_phases,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TestResource(Base):
    """测试资源模型"""
    __tablename__ = 'test_resources'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='资源ID')
    test_plan_id = Column(BigInteger, ForeignKey('test_plans.id'), nullable=False, comment='测试计划ID')
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    
    # 资源分配
    role_in_test = Column(Enum('TEST_MANAGER', 'TEST_LEAD', 'TEST_ENGINEER', 'AUTOMATION_ENGINEER', 
                              'PERFORMANCE_TESTER', 'SECURITY_TESTER'), 
                         nullable=False, comment='测试角色')
    allocation_percentage = Column(DECIMAL(5, 2), default=100.00, comment='分配百分比')
    
    # 时间管理
    start_date = Column(Date, comment='开始日期')
    end_date = Column(Date, comment='结束日期')
    
    # 技能和职责
    skills = Column(JSON, comment='技能标签')
    responsibilities = Column(Text, comment='职责描述')
    
    # 工作负载
    estimated_hours = Column(DECIMAL(6, 2), comment='预估工时')
    actual_hours = Column(DECIMAL(6, 2), default=0.00, comment='实际工时')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_test_resources_plan', 'test_plan_id'),
        Index('idx_test_resources_user', 'user_id'),
        Index('idx_test_resources_role', 'role_in_test'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'test_plan_id': self.test_plan_id,
            'user_id': self.user_id,
            'role_in_test': self.role_in_test,
            'allocation_percentage': float(self.allocation_percentage) if self.allocation_percentage else 100.0,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'skills': self.skills,
            'responsibilities': self.responsibilities,
            'estimated_hours': float(self.estimated_hours) if self.estimated_hours else None,
            'actual_hours': float(self.actual_hours) if self.actual_hours else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }