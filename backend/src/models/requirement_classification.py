"""
需求分类管理模块数据模型

本模块定义了需求分类相关的数据模型，包括：
- 需求分类维度管理
- 需求分类标签管理
- 智能分类建议管理
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Enum, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import Base
from .requirement import RequirementBaseModel

class ClassificationDimension(PyEnum):
    """分类维度枚举"""
    REQUIREMENT_TYPE = "REQUIREMENT_TYPE"      # 需求类型
    BUSINESS_DOMAIN = "BUSINESS_DOMAIN"        # 业务领域
    USER_ROLE = "USER_ROLE"                    # 用户角色
    IMPLEMENTATION_PHASE = "IMPLEMENTATION_PHASE"  # 实现阶段
    TECHNICAL_COMPLEXITY = "TECHNICAL_COMPLEXITY"  # 技术复杂度
    BUSINESS_VALUE = "BUSINESS_VALUE"          # 业务价值

class ClassificationStatus(PyEnum):
    """分类状态枚举"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEPRECATED = "DEPRECATED"

class RequirementClassificationDimension(RequirementBaseModel):
    """需求分类维度表"""
    __tablename__ = 'requirement_classification_dimensions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='维度ID')
    dimension_code = Column(String(50), unique=True, nullable=False, comment='维度编码')
    dimension_name = Column(String(100), nullable=False, comment='维度名称')
    dimension_type = Column(Enum(ClassificationDimension), nullable=False, comment='维度类型')
    description = Column(Text, comment='维度描述')
    
    # 配置信息
    is_hierarchical = Column(Boolean, default=False, comment='是否支持层级结构')
    is_multi_select = Column(Boolean, default=False, comment='是否支持多选')
    is_required = Column(Boolean, default=False, comment='是否必填')
    sort_order = Column(Integer, default=0, comment='排序顺序')
    
    # 状态管理
    status = Column(Enum(ClassificationStatus), default=ClassificationStatus.ACTIVE, comment='状态')
    
    # 元数据
    config_data = Column(JSON, comment='配置数据')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    # 关联关系
    categories = relationship("RequirementClassificationCategory", back_populates="dimension", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'dimension_code': self.dimension_code,
            'dimension_name': self.dimension_name,
            'dimension_type': self.dimension_type.value if self.dimension_type else None,
            'description': self.description,
            'is_hierarchical': self.is_hierarchical,
            'is_multi_select': self.is_multi_select,
            'is_required': self.is_required,
            'sort_order': self.sort_order,
            'status': self.status.value if self.status else None,
            'config_data': self.config_data,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementClassificationCategory(RequirementBaseModel):
    """需求分类类别表"""
    __tablename__ = 'requirement_classification_categories'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='类别ID')
    dimension_id = Column(BigInteger, ForeignKey('requirement_classification_dimensions.id'), nullable=False, comment='所属维度ID')
    parent_id = Column(BigInteger, ForeignKey('requirement_classification_categories.id'), nullable=True, comment='父类别ID')
    
    # 基本信息
    category_code = Column(String(50), nullable=False, comment='类别编码')
    category_name = Column(String(100), nullable=False, comment='类别名称')
    description = Column(Text, comment='类别描述')
    
    # 层级信息
    level = Column(Integer, default=1, comment='层级级别')
    path = Column(String(500), comment='层级路径')
    sort_order = Column(Integer, default=0, comment='排序顺序')
    
    # 状态管理
    status = Column(Enum(ClassificationStatus), default=ClassificationStatus.ACTIVE, comment='状态')
    
    # 统计信息
    usage_count = Column(Integer, default=0, comment='使用次数')
    
    # 元数据
    attributes = Column(JSON, comment='类别属性')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    # 关联关系
    dimension = relationship("RequirementClassificationDimension", back_populates="categories")
    parent = relationship("RequirementClassificationCategory", remote_side=[id], back_populates="children")
    children = relationship("RequirementClassificationCategory", back_populates="parent")
    
    # 需求分类关系
    requirement_classifications = relationship("RequirementClassification", back_populates="category", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'dimension_id': self.dimension_id,
            'parent_id': self.parent_id,
            'category_code': self.category_code,
            'category_name': self.category_name,
            'description': self.description,
            'level': self.level,
            'path': self.path,
            'sort_order': self.sort_order,
            'status': self.status.value if self.status else None,
            'usage_count': self.usage_count,
            'attributes': self.attributes,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementClassification(RequirementBaseModel):
    """需求分类关联表"""
    __tablename__ = 'requirement_classifications'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='分类关联ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    category_id = Column(BigInteger, ForeignKey('requirement_classification_categories.id'), nullable=False, comment='类别ID')
    
    # 分类信息
    confidence_score = Column(Float, comment='置信度评分(0-1)')
    is_auto_classified = Column(Boolean, default=False, comment='是否自动分类')
    classification_reason = Column(Text, comment='分类原因')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    # 关联关系
    requirement = relationship("Requirement")
    category = relationship("RequirementClassificationCategory", back_populates="requirement_classifications")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'category_id': self.category_id,
            'confidence_score': self.confidence_score,
            'is_auto_classified': self.is_auto_classified,
            'classification_reason': self.classification_reason,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ClassificationSuggestionStatus(PyEnum):
    """分类建议状态枚举"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class RequirementClassificationSuggestion(RequirementBaseModel):
    """需求分类建议表"""
    __tablename__ = 'requirement_classification_suggestions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='建议ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    category_id = Column(BigInteger, ForeignKey('requirement_classification_categories.id'), nullable=False, comment='建议类别ID')
    
    # 建议信息
    suggestion_type = Column(String(50), default='AI_SUGGESTION', comment='建议类型')
    confidence_score = Column(Float, nullable=False, comment='置信度评分(0-1)')
    reasoning = Column(Text, comment='建议理由')
    
    # 状态管理
    status = Column(Enum(ClassificationSuggestionStatus), default=ClassificationSuggestionStatus.PENDING, comment='建议状态')
    
    # 处理信息
    processed_by = Column(BigInteger, comment='处理人ID')
    processed_at = Column(DateTime, comment='处理时间')
    feedback = Column(Text, comment='处理反馈')
    
    # 过期时间
    expires_at = Column(DateTime, comment='过期时间')
    
    # 审计字段
    created_by = Column(BigInteger, comment='创建人ID')
    
    # 关联关系
    requirement = relationship("Requirement")
    category = relationship("RequirementClassificationCategory")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'category_id': self.category_id,
            'suggestion_type': self.suggestion_type,
            'confidence_score': self.confidence_score,
            'reasoning': self.reasoning,
            'status': self.status.value if self.status else None,
            'processed_by': self.processed_by,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'feedback': self.feedback,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementTag(RequirementBaseModel):
    """需求标签表"""
    __tablename__ = 'requirement_tags'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='标签ID')
    tag_name = Column(String(50), unique=True, nullable=False, comment='标签名称')
    tag_color = Column(String(7), comment='标签颜色(HEX)')
    description = Column(Text, comment='标签描述')
    
    # 统计信息
    usage_count = Column(Integer, default=0, comment='使用次数')
    
    # 状态管理
    status = Column(Enum(ClassificationStatus), default=ClassificationStatus.ACTIVE, comment='状态')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, comment='更新人ID')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'tag_name': self.tag_name,
            'tag_color': self.tag_color,
            'description': self.description,
            'usage_count': self.usage_count,
            'status': self.status.value if self.status else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementTagAssignment(RequirementBaseModel):
    """需求标签分配表"""
    __tablename__ = 'requirement_tag_assignments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='分配ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    tag_id = Column(BigInteger, ForeignKey('requirement_tags.id'), nullable=False, comment='标签ID')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    # 关联关系
    requirement = relationship("Requirement")
    tag = relationship("RequirementTag")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'tag_id': self.tag_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }