"""
需求状态流转配置和管理

本模块定义了需求状态流转的规则、前置条件检查和后置动作执行。
根据需求文档中定义的13种状态和流转规则实现。
"""
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Callable
from sqlalchemy import Column, BigInteger, String, Text, DateTime, JSON, Boolean, Enum
from enum import Enum as PyEnum

from .base import Base
from .requirement import RequirementStatus


class StatusTransitionType(PyEnum):
    """状态流转类型"""
    MANUAL = "MANUAL"      # 手动流转
    AUTOMATIC = "AUTOMATIC"  # 自动流转
    CONDITIONAL = "CONDITIONAL"  # 条件流转


class RequirementStatusFlowRule(Base):
    """需求状态流转规则配置表"""
    __tablename__ = 'requirement_status_flow_rules'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='规则ID')
    from_status = Column(Enum(RequirementStatus), nullable=False, comment='源状态')
    to_status = Column(Enum(RequirementStatus), nullable=False, comment='目标状态')
    transition_type = Column(Enum(StatusTransitionType), default=StatusTransitionType.MANUAL, comment='流转类型')
    
    # 流转条件
    preconditions = Column(JSON, comment='前置条件配置')
    required_roles = Column(JSON, comment='需要的角色权限')
    required_fields = Column(JSON, comment='必填字段')
    
    # 流转动作
    post_actions = Column(JSON, comment='后置动作配置')
    
    # 通知配置
    notification_config = Column(JSON, comment='通知配置')
    
    # 规则属性
    is_active = Column(Boolean, default=True, comment='是否启用')
    priority = Column(BigInteger, default=0, comment='优先级')
    description = Column(Text, comment='规则描述')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'from_status': self.from_status.value if self.from_status else None,
            'to_status': self.to_status.value if self.to_status else None,
            'transition_type': self.transition_type.value if self.transition_type else None,
            'preconditions': self.preconditions,
            'required_roles': self.required_roles,
            'required_fields': self.required_fields,
            'post_actions': self.post_actions,
            'notification_config': self.notification_config,
            'is_active': self.is_active,
            'priority': self.priority,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }


class RequirementStatusFlowConfig:
    """需求状态流转配置类 - 定义所有合法的状态流转"""
    
    # 根据需求文档定义的状态流转规则
    VALID_TRANSITIONS: Dict[RequirementStatus, Set[RequirementStatus]] = {
        RequirementStatus.DRAFT: {
            RequirementStatus.PENDING_REVIEW,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.PENDING_REVIEW: {
            RequirementStatus.REVIEWING,
            RequirementStatus.DRAFT,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.REVIEWING: {
            RequirementStatus.APPROVED,
            RequirementStatus.NEEDS_REVISION,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.NEEDS_REVISION: {
            RequirementStatus.PENDING_REVIEW,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.APPROVED: {
            RequirementStatus.IN_DEVELOPMENT,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.IN_DEVELOPMENT: {
            RequirementStatus.TESTING,
            RequirementStatus.PAUSED,
            RequirementStatus.NEEDS_REVISION
        },
        RequirementStatus.PAUSED: {
            RequirementStatus.IN_DEVELOPMENT,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.TESTING: {
            RequirementStatus.COMPLETED,
            RequirementStatus.TEST_FAILED
        },
        RequirementStatus.TEST_FAILED: {
            RequirementStatus.IN_DEVELOPMENT,
            RequirementStatus.CANCELLED
        },
        RequirementStatus.COMPLETED: {
            RequirementStatus.DEPLOYED,
            RequirementStatus.NEEDS_REVISION
        },
        RequirementStatus.DEPLOYED: {
            RequirementStatus.CLOSED
        },
        RequirementStatus.CLOSED: {
            RequirementStatus.DRAFT  # 重新打开
        },
        RequirementStatus.CANCELLED: {
            RequirementStatus.DRAFT  # 重新打开
        }
    }
    
    # 状态描述和触发条件
    STATUS_DESCRIPTIONS: Dict[RequirementStatus, Dict[str, Any]] = {
        RequirementStatus.DRAFT: {
            "description": "需求初始创建状态，内容可能不完整",
            "trigger_conditions": ["需求创建"],
            "preconditions": ["基本信息完整性"],
            "post_actions": ["保存草稿"],
            "notification_targets": ["创建人"]
        },
        RequirementStatus.PENDING_REVIEW: {
            "description": "需求已完成编写，等待评审",
            "trigger_conditions": ["提交评审"],
            "preconditions": ["必填字段完整性检查"],
            "post_actions": ["发送评审通知"],
            "notification_targets": ["评审人员"]
        },
        RequirementStatus.REVIEWING: {
            "description": "需求正在评审过程中",
            "trigger_conditions": ["开始评审"],
            "preconditions": ["评审人员分配"],
            "post_actions": ["启动评审流程"],
            "notification_targets": ["需求负责人", "评审人"]
        },
        RequirementStatus.NEEDS_REVISION: {
            "description": "评审发现问题，需要修改",
            "trigger_conditions": ["评审提出修改意见"],
            "preconditions": ["修改意见记录"],
            "post_actions": ["返回修改，记录意见"],
            "notification_targets": ["需求负责人"]
        },
        RequirementStatus.APPROVED: {
            "description": "需求评审通过，可以开始实现",
            "trigger_conditions": ["评审批准"],
            "preconditions": ["所有评审意见处理完成"],
            "post_actions": ["激活相关任务"],
            "notification_targets": ["开发团队", "项目经理"]
        },
        RequirementStatus.IN_DEVELOPMENT: {
            "description": "需求正在开发实现",
            "trigger_conditions": ["开始开发"],
            "preconditions": ["开发任务分配"],
            "post_actions": ["开始开发跟踪"],
            "notification_targets": ["开发人员", "测试人员"]
        },
        RequirementStatus.PAUSED: {
            "description": "需求开发暂时停止",
            "trigger_conditions": ["手动暂停或阻塞"],
            "preconditions": ["暂停原因必填"],
            "post_actions": ["暂停相关任务"],
            "notification_targets": ["项目团队"]
        },
        RequirementStatus.TESTING: {
            "description": "开发完成，等待测试验证",
            "trigger_conditions": ["开发完成提交"],
            "preconditions": ["开发完成确认"],
            "post_actions": ["创建测试任务"],
            "notification_targets": ["测试人员"]
        },
        RequirementStatus.TEST_FAILED: {
            "description": "测试发现问题，需要修复",
            "trigger_conditions": ["测试发现缺陷"],
            "preconditions": ["缺陷记录和分析"],
            "post_actions": ["创建缺陷任务"],
            "notification_targets": ["开发人员"]
        },
        RequirementStatus.COMPLETED: {
            "description": "需求开发和测试全部完成",
            "trigger_conditions": ["测试通过"],
            "preconditions": ["验收标准全部满足"],
            "post_actions": ["更新项目进度"],
            "notification_targets": ["项目团队", "干系人"]
        },
        RequirementStatus.DEPLOYED: {
            "description": "需求已部署到生产环境",
            "trigger_conditions": ["生产部署完成"],
            "preconditions": ["部署验证通过"],
            "post_actions": ["生产监控"],
            "notification_targets": ["运维人员", "用户"]
        },
        RequirementStatus.CLOSED: {
            "description": "需求生命周期结束",
            "trigger_conditions": ["手动关闭或自动关闭"],
            "preconditions": ["无遗留问题"],
            "post_actions": ["归档处理"],
            "notification_targets": ["相关人员"]
        },
        RequirementStatus.CANCELLED: {
            "description": "需求被取消，不再实现",
            "trigger_conditions": ["手动取消"],
            "preconditions": ["取消原因和影响评估"],
            "post_actions": ["释放资源，通知干系人"],
            "notification_targets": ["项目团队"]
        }
    }
    
    @classmethod
    def is_valid_transition(cls, from_status: RequirementStatus, to_status: RequirementStatus) -> bool:
        """检查状态流转是否合法"""
        if from_status not in cls.VALID_TRANSITIONS:
            return False
        return to_status in cls.VALID_TRANSITIONS[from_status]
    
    @classmethod
    def get_valid_next_statuses(cls, current_status: RequirementStatus) -> Set[RequirementStatus]:
        """获取当前状态可以流转到的所有状态"""
        return cls.VALID_TRANSITIONS.get(current_status, set())
    
    @classmethod
    def get_status_description(cls, status: RequirementStatus) -> Dict[str, Any]:
        """获取状态描述信息"""
        return cls.STATUS_DESCRIPTIONS.get(status, {})
    
    @classmethod
    def get_all_transitions(cls) -> List[Dict[str, Any]]:
        """获取所有状态流转规则"""
        transitions = []
        for from_status, to_statuses in cls.VALID_TRANSITIONS.items():
            for to_status in to_statuses:
                transitions.append({
                    'from_status': from_status.value,
                    'to_status': to_status.value,
                    'from_description': cls.STATUS_DESCRIPTIONS.get(from_status, {}).get('description', ''),
                    'to_description': cls.STATUS_DESCRIPTIONS.get(to_status, {}).get('description', ''),
                    'trigger_conditions': cls.STATUS_DESCRIPTIONS.get(to_status, {}).get('trigger_conditions', []),
                    'preconditions': cls.STATUS_DESCRIPTIONS.get(to_status, {}).get('preconditions', []),
                    'post_actions': cls.STATUS_DESCRIPTIONS.get(to_status, {}).get('post_actions', []),
                    'notification_targets': cls.STATUS_DESCRIPTIONS.get(to_status, {}).get('notification_targets', [])
                })
        return transitions


class StatusTransitionError(Exception):
    """状态流转错误异常"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class PreconditionCheckResult:
    """前置条件检查结果"""
    
    def __init__(self, is_valid: bool, error_messages: List[str] = None, warnings: List[str] = None, details: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.error_messages = error_messages or []
        self.warnings = warnings or []
        self.details = details or {}
    
    def add_error(self, message: str):
        """添加错误信息"""
        self.error_messages.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """添加警告信息"""
        self.warnings.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'error_messages': self.error_messages,
            'warnings': self.warnings,
            'details': self.details
        }


class PostActionResult:
    """后置动作执行结果"""
    
    def __init__(self, success: bool, executed_actions: List[str] = None, failed_actions: List[str] = None, details: Dict[str, Any] = None):
        self.success = success
        self.executed_actions = executed_actions or []
        self.failed_actions = failed_actions or []
        self.details = details or {}
    
    def add_executed_action(self, action: str):
        """添加已执行的动作"""
        self.executed_actions.append(action)
    
    def add_failed_action(self, action: str):
        """添加失败的动作"""
        self.failed_actions.append(action)
        self.success = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': self.success,
            'executed_actions': self.executed_actions,
            'failed_actions': self.failed_actions,
            'details': self.details
        }