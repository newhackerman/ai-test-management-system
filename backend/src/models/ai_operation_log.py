"""
AI助手操作日志模型

记录AI助手模块的所有操作活动，包括：
- 用户对话记录
- AI模型调用记录
- 建议生成记录
- 配置变更记录
- 权限操作记录
- 系统事件记录
"""
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Text, Enum, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from typing import Optional, Dict, Any

from .base import BaseModel


class AIOperationType(PyEnum):
    """AI操作类型"""
    # 对话相关
    CONVERSATION_CREATE = "conversation_create"
    CONVERSATION_DELETE = "conversation_delete"
    MESSAGE_SEND = "message_send"
    MESSAGE_RECEIVE = "message_receive"
    
    # AI服务调用
    AI_MODEL_CALL = "ai_model_call"
    AI_STREAMING_START = "ai_streaming_start"
    AI_STREAMING_COMPLETE = "ai_streaming_complete"
    
    # 建议系统
    SUGGESTION_GENERATE = "suggestion_generate"
    SUGGESTION_ACCEPT = "suggestion_accept"
    SUGGESTION_REJECT = "suggestion_reject"
    SUGGESTION_IMPLEMENT = "suggestion_implement"
    
    # 模板管理
    TEMPLATE_CREATE = "template_create"
    TEMPLATE_UPDATE = "template_update"
    TEMPLATE_DELETE = "template_delete"
    TEMPLATE_USE = "template_use"
    TEMPLATE_SHARE = "template_share"
    
    # 配置管理
    AI_CONFIG_UPDATE = "ai_config_update"
    MODEL_CONFIG_CHANGE = "model_config_change"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    
    # 系统事件
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    HEALTH_CHECK = "health_check"
    ERROR_OCCURRED = "error_occurred"
    
    # 数据操作
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    DATA_BACKUP = "data_backup"
    DATA_RESTORE = "data_restore"
    
    # 安全事件
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AIOperationResult(PyEnum):
    """AI操作结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AIOperationPriority(PyEnum):
    """操作优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIOperationLog(BaseModel):
    """AI助手操作日志模型"""
    __tablename__ = "ai_operation_logs"

    # 基本信息
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="操作用户ID")
    session_id = Column(String(100), nullable=True, comment="会话ID")
    operation_type = Column(Enum(AIOperationType), nullable=False, comment="操作类型")
    operation_name = Column(String(100), nullable=False, comment="操作名称")
    operation_description = Column(Text, nullable=True, comment="操作描述")
    
    # 操作结果
    result = Column(Enum(AIOperationResult), nullable=False, comment="操作结果")
    result_message = Column(Text, nullable=True, comment="结果消息")
    error_code = Column(String(50), nullable=True, comment="错误代码")
    error_details = Column(Text, nullable=True, comment="错误详情")
    
    # 资源信息
    resource_type = Column(String(50), nullable=True, comment="资源类型")
    resource_id = Column(String(100), nullable=True, comment="资源ID")
    resource_name = Column(String(200), nullable=True, comment="资源名称")
    
    # AI相关信息
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="AI模型")
    tokens_used = Column(Integer, nullable=True, comment="使用的Token数")
    cost_amount = Column(Float, nullable=True, comment="成本金额")
    
    # 性能指标
    processing_time = Column(Float, nullable=True, comment="处理时间(秒)")
    response_size = Column(Integer, nullable=True, comment="响应大小(字节)")
    confidence_score = Column(Float, nullable=True, comment="置信度分数")
    
    # 请求信息
    request_ip = Column(String(45), nullable=True, comment="请求IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    request_headers = Column(JSON, nullable=True, comment="请求头信息")
    request_params = Column(JSON, nullable=True, comment="请求参数")
    
    # 响应信息
    response_data = Column(JSON, nullable=True, comment="响应数据")
    response_headers = Column(JSON, nullable=True, comment="响应头信息")
    
    # 业务数据
    business_context = Column(JSON, nullable=True, comment="业务上下文")
    operation_metadata = Column(JSON, nullable=True, comment="操作元数据")
    tags = Column(JSON, nullable=True, comment="标签")
    
    # 优先级和分类
    priority = Column(Enum(AIOperationPriority), default=AIOperationPriority.MEDIUM, comment="优先级")
    category = Column(String(50), nullable=True, comment="分类")
    subcategory = Column(String(50), nullable=True, comment="子分类")
    
    # 审计信息
    is_sensitive = Column(Boolean, default=False, comment="是否敏感操作")
    requires_approval = Column(Boolean, default=False, comment="是否需要审批")
    approved_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="审批人ID")
    approved_at = Column(String(50), nullable=True, comment="审批时间")
    
    # 关联信息
    parent_log_id = Column(BigInteger, ForeignKey("ai_operation_logs.id", ondelete="SET NULL"), nullable=True, comment="父日志ID")
    correlation_id = Column(String(100), nullable=True, comment="关联ID")
    trace_id = Column(String(100), nullable=True, comment="追踪ID")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    parent_log = relationship("AIOperationLog", remote_side="AIOperationLog.id")
    child_logs = relationship("AIOperationLog", back_populates="parent_log")

    def __repr__(self):
        return f"<AIOperationLog(id={self.id}, type={self.operation_type.value}, user_id={self.user_id}, result={self.result.value})>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "operation_type": self.operation_type.value if self.operation_type else None,
            "operation_name": self.operation_name,
            "operation_description": self.operation_description,
            "result": self.result.value if self.result else None,
            "result_message": self.result_message,
            "error_code": self.error_code,
            "error_details": self.error_details,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "tokens_used": self.tokens_used,
            "cost_amount": self.cost_amount,
            "processing_time": self.processing_time,
            "response_size": self.response_size,
            "confidence_score": self.confidence_score,
            "request_ip": self.request_ip,
            "user_agent": self.user_agent,
            "priority": self.priority.value if self.priority else None,
            "category": self.category,
            "subcategory": self.subcategory,
            "is_sensitive": self.is_sensitive,
            "requires_approval": self.requires_approval,
            "operation_metadata": self.operation_metadata,
            "business_context": self.business_context,
            "tags": self.tags,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create_log(cls, operation_type: AIOperationType, operation_name: str, 
                   result: AIOperationResult, user_id: Optional[int] = None,
                   **kwargs) -> "AIOperationLog":
        """创建操作日志的便捷方法"""
        return cls(
            operation_type=operation_type,
            operation_name=operation_name,
            result=result,
            user_id=user_id,
            **kwargs
        )


class AIOperationLogSummary(BaseModel):
    """AI操作日志汇总表"""
    __tablename__ = "ai_operation_log_summaries"
    
    # 汇总维度
    summary_date = Column(String(10), nullable=False, comment="汇总日期(YYYY-MM-DD)")
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="用户ID")
    operation_type = Column(Enum(AIOperationType), nullable=True, comment="操作类型")
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    
    # 统计数据
    total_operations = Column(Integer, default=0, comment="总操作数")
    successful_operations = Column(Integer, default=0, comment="成功操作数")
    failed_operations = Column(Integer, default=0, comment="失败操作数")
    
    # 性能统计
    total_processing_time = Column(Float, default=0.0, comment="总处理时间")
    avg_processing_time = Column(Float, default=0.0, comment="平均处理时间")
    max_processing_time = Column(Float, default=0.0, comment="最大处理时间")
    min_processing_time = Column(Float, default=0.0, comment="最小处理时间")
    
    # 资源统计
    total_tokens_used = Column(Integer, default=0, comment="总Token使用量")
    total_cost = Column(Float, default=0.0, comment="总成本")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<AIOperationLogSummary(date={self.summary_date}, user_id={self.user_id}, operations={self.total_operations})>"