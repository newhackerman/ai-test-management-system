"""
自定义异常类
"""


class BaseCustomException(Exception):
    """基础自定义异常"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """验证错误"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


class NotFoundError(BaseCustomException):
    """资源不存在错误"""
    def __init__(self, message: str, resource_type: str = None):
        self.resource_type = resource_type
        super().__init__(message, "NOT_FOUND")


class PermissionError(BaseCustomException):
    """权限错误"""
    def __init__(self, message: str, required_permission: str = None):
        self.required_permission = required_permission
        super().__init__(message, "PERMISSION_DENIED")


class ConfigurationError(BaseCustomException):
    """配置错误"""
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        super().__init__(message, "CONFIGURATION_ERROR")


class ServiceError(BaseCustomException):
    """服务错误"""
    def __init__(self, message: str, service_name: str = None):
        self.service_name = service_name
        super().__init__(message, "SERVICE_ERROR")


class DatabaseError(BaseCustomException):
    """数据库错误"""
    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        super().__init__(message, "DATABASE_ERROR")


class AIServiceError(BaseCustomException):
    """AI服务错误"""
    def __init__(self, message: str, provider: str = None, model: str = None):
        self.provider = provider
        self.model = model
        super().__init__(message, "AI_SERVICE_ERROR")


class ConversationError(BaseCustomException):
    """对话相关错误"""
    def __init__(self, message: str, conversation_id: int = None):
        self.conversation_id = conversation_id
        super().__init__(message, "CONVERSATION_ERROR")


class MessageError(BaseCustomException):
    """消息相关错误"""
    def __init__(self, message: str, message_id: int = None):
        self.message_id = message_id
        super().__init__(message, "MESSAGE_ERROR")


class QuotaExceededException(BaseCustomException):
    """配额超限异常"""
    def __init__(self, message: str, quota_type: str = None, current_usage: int = None, limit: int = None):
        self.quota_type = quota_type
        self.current_usage = current_usage
        self.limit = limit
        super().__init__(message, "QUOTA_EXCEEDED")


class BudgetExceededException(BaseCustomException):
    """预算超限异常"""
    def __init__(self, message: str, budget_type: str = None, current_cost: float = None, limit: float = None):
        self.budget_type = budget_type
        self.current_cost = current_cost
        self.limit = limit
        super().__init__(message, "BUDGET_EXCEEDED")


class BusinessLogicError(BaseCustomException):
    """业务逻辑错误"""
    def __init__(self, message: str, business_rule: str = None):
        self.business_rule = business_rule
        super().__init__(message, "BUSINESS_LOGIC_ERROR")


class ExecutionError(BaseCustomException):
    """执行错误"""
    def __init__(self, message: str, execution_type: str = None, error_code: str = None):
        self.execution_type = execution_type
        self.error_code = error_code
        super().__init__(message, "EXECUTION_ERROR")


class TestExecutionError(ExecutionError):
    """测试执行错误"""
    def __init__(self, message: str, test_id: int = None, step: str = None):
        self.test_id = test_id
        self.step = step
        super().__init__(message, "test_execution", "TEST_EXECUTION_ERROR")


class AutomationError(ExecutionError):
    """自动化执行错误"""
    def __init__(self, message: str, automation_type: str = None, script_path: str = None):
        self.automation_type = automation_type
        self.script_path = script_path
        super().__init__(message, "automation", "AUTOMATION_ERROR")


class ConflictError(BaseCustomException):
    """冲突错误"""
    def __init__(self, message: str, resource_type: str = None, conflict_field: str = None):
        self.resource_type = resource_type
        self.conflict_field = conflict_field
        super().__init__(message, "CONFLICT_ERROR")


class TimeoutError(BaseCustomException):
    """超时错误"""
    def __init__(self, message: str, timeout_seconds: int = None, operation: str = None):
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        super().__init__(message, "TIMEOUT_ERROR")


class RateLimitError(BaseCustomException):
    """频率限制错误"""
    def __init__(self, message: str, limit_type: str = None, retry_after: int = None):
        self.limit_type = limit_type
        self.retry_after = retry_after
        super().__init__(message, "RATE_LIMIT_ERROR")