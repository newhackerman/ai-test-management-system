"""
需求优先级管理模块数据模型

本模块定义了需求优先级相关的数据模型，包括：
- 优先级评估算法配置
- 动态优先级调整
- 优先级冲突检测和解决
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Enum, Boolean, ForeignKey, Float, DECIMAL
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import Base
from .requirement import RequirementBaseModel, Priority

class PriorityCalculationMethod(PyEnum):
    """优先级计算方法枚举"""
    MANUAL = "MANUAL"                    # 手动设置
    WEIGHTED_SCORE = "WEIGHTED_SCORE"    # 加权评分
    AI_ANALYSIS = "AI_ANALYSIS"          # AI分析
    HYBRID = "HYBRID"                    # 混合方式

class PriorityFactorType(PyEnum):
    """优先级因子类型枚举"""
    BUSINESS_VALUE = "BUSINESS_VALUE"      # 商业价值
    USER_IMPACT = "USER_IMPACT"           # 用户影响
    TECHNICAL_RISK = "TECHNICAL_RISK"     # 技术风险
    IMPLEMENTATION_COST = "IMPLEMENTATION_COST"  # 实现成本
    TIME_URGENCY = "TIME_URGENCY"         # 时间紧迫性
    STRATEGIC_ALIGNMENT = "STRATEGIC_ALIGNMENT"  # 战略一致性
    COMPLIANCE_REQUIREMENT = "COMPLIANCE_REQUIREMENT"  # 合规要求

class ConflictResolutionStrategy(PyEnum):
    """冲突解决策略枚举"""
    MANUAL_REVIEW = "MANUAL_REVIEW"      # 手动评审
    HIGHEST_PRIORITY = "HIGHEST_PRIORITY"  # 取最高优先级
    WEIGHTED_AVERAGE = "WEIGHTED_AVERAGE"  # 加权平均
    STAKEHOLDER_VOTE = "STAKEHOLDER_VOTE"  # 干系人投票

class RequirementPriorityConfig(RequirementBaseModel):
    """需求优先级配置表"""
    __tablename__ = 'requirement_priority_configs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='配置ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='项目ID')
    
    # 配置信息
    config_name = Column(String(100), nullable=False, comment='配置名称')
    description = Column(Text, comment='配置描述')
    calculation_method = Column(Enum(PriorityCalculationMethod), default=PriorityCalculationMethod.WEIGHTED_SCORE, comment='计算方法')
    
    # 权重配置
    business_value_weight = Column(DECIMAL(3, 2), default=0.30, comment='商业价值权重')
    user_impact_weight = Column(DECIMAL(3, 2), default=0.25, comment='用户影响权重')
    technical_risk_weight = Column(DECIMAL(3, 2), default=0.20, comment='技术风险权重')
    implementation_cost_weight = Column(DECIMAL(3, 2), default=0.15, comment='实现成本权重')
    time_urgency_weight = Column(DECIMAL(3, 2), default=0.10, comment='时间紧迫性权重')
    
    # 阈值配置
    critical_threshold = Column(DECIMAL(3, 2), default=0.90, comment='紧急优先级阈值')
    high_threshold = Column(DECIMAL(3, 2), default=0.70, comment='高优先级阈值')
    medium_threshold = Column(DECIMAL(3, 2), default=0.40, comment='中优先级阈值')
    low_threshold = Column(DECIMAL(3, 2), default=0.20, comment='低优先级阈值')
    
    # 冲突解决配置
    conflict_resolution_strategy = Column(Enum(ConflictResolutionStrategy), default=ConflictResolutionStrategy.MANUAL_REVIEW, comment='冲突解决策略')
    
    # 状态管理
    is_active = Column(Boolean, default=True, comment='是否激活')
    is_default = Column(Boolean, default=False, comment='是否默认配置')
    
    # 元数据
    additional_config = Column(JSON, comment='额外配置数据')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    # 关联关系
    project = relationship("Project")
    priority_evaluations = relationship("RequirementPriorityEvaluation", back_populates="config", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'config_name': self.config_name,
            'description': self.description,
            'calculation_method': self.calculation_method.value if self.calculation_method else None,
            'business_value_weight': float(self.business_value_weight) if self.business_value_weight else None,
            'user_impact_weight': float(self.user_impact_weight) if self.user_impact_weight else None,
            'technical_risk_weight': float(self.technical_risk_weight) if self.technical_risk_weight else None,
            'implementation_cost_weight': float(self.implementation_cost_weight) if self.implementation_cost_weight else None,
            'time_urgency_weight': float(self.time_urgency_weight) if self.time_urgency_weight else None,
            'critical_threshold': float(self.critical_threshold) if self.critical_threshold else None,
            'high_threshold': float(self.high_threshold) if self.high_threshold else None,
            'medium_threshold': float(self.medium_threshold) if self.medium_threshold else None,
            'low_threshold': float(self.low_threshold) if self.low_threshold else None,
            'conflict_resolution_strategy': self.conflict_resolution_strategy.value if self.conflict_resolution_strategy else None,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'additional_config': self.additional_config,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementPriorityEvaluation(RequirementBaseModel):
    """需求优先级评估表"""
    __tablename__ = 'requirement_priority_evaluations'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='评估ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    config_id = Column(BigInteger, ForeignKey('requirement_priority_configs.id'), nullable=False, comment='配置ID')
    
    # 评估因子得分 (0-10分)
    business_value_score = Column(DECIMAL(3, 1), comment='商业价值得分')
    user_impact_score = Column(DECIMAL(3, 1), comment='用户影响得分')
    technical_risk_score = Column(DECIMAL(3, 1), comment='技术风险得分')
    implementation_cost_score = Column(DECIMAL(3, 1), comment='实现成本得分')
    time_urgency_score = Column(DECIMAL(3, 1), comment='时间紧迫性得分')
    
    # 计算结果
    weighted_score = Column(DECIMAL(5, 2), comment='加权总分')
    calculated_priority = Column(Enum(Priority), comment='计算得出的优先级')
    final_priority = Column(Enum(Priority), comment='最终优先级')
    
    # 评估信息
    evaluation_method = Column(Enum(PriorityCalculationMethod), comment='评估方法')
    evaluation_reason = Column(Text, comment='评估理由')
    manual_adjustment_reason = Column(Text, comment='手动调整原因')
    
    # 评估人员
    evaluator_id = Column(BigInteger, comment='评估人ID')
    approver_id = Column(BigInteger, comment='审批人ID')
    
    # 时间信息
    evaluated_at = Column(DateTime, comment='评估时间')
    approved_at = Column(DateTime, comment='审批时间')
    
    # 状态管理
    is_current = Column(Boolean, default=True, comment='是否当前有效')
    
    # 元数据
    evaluation_data = Column(JSON, comment='评估详细数据')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    # 关联关系
    requirement = relationship("Requirement")
    config = relationship("RequirementPriorityConfig", back_populates="priority_evaluations")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'config_id': self.config_id,
            'business_value_score': float(self.business_value_score) if self.business_value_score else None,
            'user_impact_score': float(self.user_impact_score) if self.user_impact_score else None,
            'technical_risk_score': float(self.technical_risk_score) if self.technical_risk_score else None,
            'implementation_cost_score': float(self.implementation_cost_score) if self.implementation_cost_score else None,
            'time_urgency_score': float(self.time_urgency_score) if self.time_urgency_score else None,
            'weighted_score': float(self.weighted_score) if self.weighted_score else None,
            'calculated_priority': self.calculated_priority.value if self.calculated_priority else None,
            'final_priority': self.final_priority.value if self.final_priority else None,
            'evaluation_method': self.evaluation_method.value if self.evaluation_method else None,
            'evaluation_reason': self.evaluation_reason,
            'manual_adjustment_reason': self.manual_adjustment_reason,
            'evaluator_id': self.evaluator_id,
            'approver_id': self.approver_id,
            'evaluated_at': self.evaluated_at.isoformat() if self.evaluated_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'is_current': self.is_current,
            'evaluation_data': self.evaluation_data,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PriorityConflictStatus(PyEnum):
    """优先级冲突状态枚举"""
    DETECTED = "DETECTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class RequirementPriorityConflict(RequirementBaseModel):
    """需求优先级冲突表"""
    __tablename__ = 'requirement_priority_conflicts'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='冲突ID')
    
    # 冲突需求
    requirement_ids = Column(JSON, nullable=False, comment='冲突需求ID列表')
    
    # 冲突信息
    conflict_type = Column(String(50), nullable=False, comment='冲突类型')
    conflict_description = Column(Text, comment='冲突描述')
    severity_level = Column(Integer, default=1, comment='严重程度(1-5)')
    
    # 冲突检测
    detected_by_system = Column(Boolean, default=True, comment='是否系统检测')
    detection_algorithm = Column(String(100), comment='检测算法')
    detection_confidence = Column(DECIMAL(3, 2), comment='检测置信度')
    
    # 解决方案
    resolution_strategy = Column(Enum(ConflictResolutionStrategy), comment='解决策略')
    resolution_description = Column(Text, comment='解决方案描述')
    recommended_priorities = Column(JSON, comment='推荐优先级')
    
    # 状态管理
    status = Column(Enum(PriorityConflictStatus), default=PriorityConflictStatus.DETECTED, comment='冲突状态')
    
    # 处理信息
    assigned_to = Column(BigInteger, comment='分配给')
    resolved_by = Column(BigInteger, comment='解决人ID')
    resolved_at = Column(DateTime, comment='解决时间')
    resolution_notes = Column(Text, comment='解决备注')
    
    # 审计字段
    created_by = Column(BigInteger, comment='创建人ID')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_ids': self.requirement_ids,
            'conflict_type': self.conflict_type,
            'conflict_description': self.conflict_description,
            'severity_level': self.severity_level,
            'detected_by_system': self.detected_by_system,
            'detection_algorithm': self.detection_algorithm,
            'detection_confidence': float(self.detection_confidence) if self.detection_confidence else None,
            'resolution_strategy': self.resolution_strategy.value if self.resolution_strategy else None,
            'resolution_description': self.resolution_description,
            'recommended_priorities': self.recommended_priorities,
            'status': self.status.value if self.status else None,
            'assigned_to': self.assigned_to,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementPriorityHistory(RequirementBaseModel):
    """需求优先级历史表"""
    __tablename__ = 'requirement_priority_history'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='历史记录ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    
    # 优先级变更
    old_priority = Column(Enum(Priority), comment='变更前优先级')
    new_priority = Column(Enum(Priority), nullable=False, comment='变更后优先级')
    
    # 变更信息
    change_reason = Column(Text, comment='变更原因')
    change_method = Column(Enum(PriorityCalculationMethod), comment='变更方法')
    change_trigger = Column(String(100), comment='变更触发器')
    
    # 评估数据
    old_weighted_score = Column(DECIMAL(5, 2), comment='变更前加权得分')
    new_weighted_score = Column(DECIMAL(5, 2), comment='变更后加权得分')
    
    # 审计字段
    changed_by = Column(BigInteger, nullable=False, comment='变更人ID')
    changed_at = Column(DateTime, default=datetime.utcnow, comment='变更时间')
    
    # 关联关系
    requirement = relationship("Requirement")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'old_priority': self.old_priority.value if self.old_priority else None,
            'new_priority': self.new_priority.value if self.new_priority else None,
            'change_reason': self.change_reason,
            'change_method': self.change_method.value if self.change_method else None,
            'change_trigger': self.change_trigger,
            'old_weighted_score': float(self.old_weighted_score) if self.old_weighted_score else None,
            'new_weighted_score': float(self.new_weighted_score) if self.new_weighted_score else None,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }