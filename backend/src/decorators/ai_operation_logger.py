"""
AI操作日志装饰器

提供便捷的装饰器来自动记录AI助手模块的操作日志，包括：
1. 方法调用日志记录
2. 异常处理和错误日志
3. 性能监控和统计
4. 上下文信息提取
5. 异步和同步方法支持
"""
import asyncio
import functools
import inspect
import logging
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from ..models.ai_operation_log import AIOperationType, AIOperationResult, AIOperationPriority
from ..services.ai_operation_log_service import get_ai_operation_log_service

logger = logging.getLogger(__name__)


def ai_operation_log(
    operation_type: AIOperationType,
    operation_name: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    priority: AIOperationPriority = AIOperationPriority.MEDIUM,
    is_sensitive: bool = False,
    log_args: bool = False,
    log_result: bool = False,
    extract_user_id: Optional[str] = None,
    extract_session_id: Optional[str] = None,
    custom_extractor: Optional[Callable] = None
):
    """
    AI操作日志装饰器
    
    Args:
        operation_type: 操作类型
        operation_name: 操作名称，默认使用函数名
        category: 分类
        subcategory: 子分类
        priority: 优先级
        is_sensitive: 是否敏感操作
        log_args: 是否记录参数
        log_result: 是否记录结果
        extract_user_id: 从参数中提取用户ID的字段名
        extract_session_id: 从参数中提取会话ID的字段名
        custom_extractor: 自定义信息提取函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _execute_with_logging(
                func, args, kwargs, operation_type, operation_name, category, 
                subcategory, priority, is_sensitive, log_args, log_result,
                extract_user_id, extract_session_id, custom_extractor, is_async=True
            )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(_execute_with_logging(
                func, args, kwargs, operation_type, operation_name, category,
                subcategory, priority, is_sensitive, log_args, log_result,
                extract_user_id, extract_session_id, custom_extractor, is_async=False
            ))
        
        # 根据函数类型返回相应的包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def _execute_with_logging(
    func: Callable,
    args: tuple,
    kwargs: dict,
    operation_type: AIOperationType,
    operation_name: Optional[str],
    category: Optional[str],
    subcategory: Optional[str],
    priority: AIOperationPriority,
    is_sensitive: bool,
    log_args: bool,
    log_result: bool,
    extract_user_id: Optional[str],
    extract_session_id: Optional[str],
    custom_extractor: Optional[Callable],
    is_async: bool
) -> Any:
    """执行函数并记录日志"""
    start_time = time.time()
    result = None
    error = None
    
    # 提取基本信息
    func_name = operation_name or func.__name__
    user_id = _extract_user_id(args, kwargs, extract_user_id)
    session_id = _extract_session_id(args, kwargs, extract_session_id)
    
    # 自定义信息提取
    custom_info = {}
    if custom_extractor:
        try:
            custom_info = custom_extractor(args, kwargs) or {}
        except Exception as e:
            logger.warning(f"自定义信息提取失败: {e}")
    
    try:
        # 执行函数
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        # 记录成功日志
        processing_time = time.time() - start_time
        
        await _log_operation_result(
            operation_type=operation_type,
            operation_name=func_name,
            result=AIOperationResult.SUCCESS,
            user_id=user_id,
            session_id=session_id,
            processing_time=processing_time,
            category=category,
            subcategory=subcategory,
            priority=priority,
            is_sensitive=is_sensitive,
            args=args if log_args else None,
            kwargs=kwargs if log_args else None,
            function_result=result if log_result else None,
            custom_info=custom_info
        )
        
        return result
        
    except Exception as e:
        error = e
        processing_time = time.time() - start_time
        
        # 记录失败日志
        await _log_operation_result(
            operation_type=operation_type,
            operation_name=func_name,
            result=AIOperationResult.FAILURE,
            user_id=user_id,
            session_id=session_id,
            processing_time=processing_time,
            category=category,
            subcategory=subcategory,
            priority=AIOperationPriority.HIGH,  # 错误日志提升优先级
            is_sensitive=is_sensitive,
            args=args if log_args else None,
            kwargs=kwargs if log_args else None,
            error=error,
            custom_info=custom_info
        )
        
        # 重新抛出异常
        raise


def _extract_user_id(args: tuple, kwargs: dict, extract_field: Optional[str]) -> Optional[int]:
    """提取用户ID"""
    if not extract_field:
        # 尝试常见的用户ID字段
        for field in ['user_id', 'current_user_id', 'uid']:
            if field in kwargs:
                return kwargs[field]
        
        # 尝试从第一个参数提取（通常是self）
        if args and hasattr(args[0], 'user_id'):
            return getattr(args[0], 'user_id')
        
        return None
    
    # 从指定字段提取
    if extract_field in kwargs:
        return kwargs[extract_field]
    
    return None


def _extract_session_id(args: tuple, kwargs: dict, extract_field: Optional[str]) -> Optional[str]:
    """提取会话ID"""
    if not extract_field:
        # 尝试常见的会话ID字段
        for field in ['session_id', 'conversation_id', 'chat_id']:
            if field in kwargs:
                return str(kwargs[field])
        
        return None
    
    # 从指定字段提取
    if extract_field in kwargs:
        return str(kwargs[extract_field])
    
    return None


async def _log_operation_result(
    operation_type: AIOperationType,
    operation_name: str,
    result: AIOperationResult,
    user_id: Optional[int],
    session_id: Optional[str],
    processing_time: float,
    category: Optional[str],
    subcategory: Optional[str],
    priority: AIOperationPriority,
    is_sensitive: bool,
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
    function_result: Any = None,
    error: Optional[Exception] = None,
    custom_info: Optional[Dict[str, Any]] = None
):
    """记录操作结果日志"""
    try:
        log_service = await get_ai_operation_log_service()
        
        # 构建日志数据
        log_data = {
            'processing_time': processing_time,
            'category': category,
            'subcategory': subcategory,
            'priority': priority,
            'is_sensitive': is_sensitive
        }
        
        # 添加自定义信息
        if custom_info:
            log_data.update(custom_info)
        
        # 处理参数信息
        if args or kwargs:
            request_params = {}
            if args:
                request_params['args'] = _serialize_args(args)
            if kwargs:
                request_params['kwargs'] = _serialize_kwargs(kwargs)
            log_data['request_params'] = request_params
        
        # 处理结果信息
        if function_result is not None:
            log_data['response_data'] = _serialize_result(function_result)
        
        # 处理错误信息
        if error:
            log_data['error_code'] = type(error).__name__
            log_data['error_details'] = str(error)
            log_data['result_message'] = f"函数执行失败: {str(error)}"
            
            # 添加堆栈跟踪（仅用于调试）
            if logger.isEnabledFor(logging.DEBUG):
                log_data['metadata'] = {
                    'traceback': traceback.format_exc()
                }
        else:
            log_data['result_message'] = "函数执行成功"
        
        # 记录日志
        await log_service.log_operation(
            operation_type=operation_type,
            operation_name=operation_name,
            result=result,
            user_id=user_id,
            session_id=session_id,
            **log_data
        )
        
    except Exception as log_error:
        # 日志记录失败不应该影响主业务
        logger.error(f"记录操作日志失败: {log_error}")


def _serialize_args(args: tuple) -> list:
    """序列化函数参数"""
    serialized = []
    for arg in args:
        try:
            # 跳过self参数
            if hasattr(arg, '__class__') and hasattr(arg.__class__, '__name__'):
                if arg.__class__.__name__ in ['AIAssistantService', 'AIOperationLogService']:
                    serialized.append(f"<{arg.__class__.__name__} instance>")
                    continue
            
            # 序列化其他参数
            serialized.append(_safe_serialize(arg))
        except Exception:
            serialized.append("<不可序列化的参数>")
    
    return serialized


def _serialize_kwargs(kwargs: dict) -> dict:
    """序列化关键字参数"""
    serialized = {}
    for key, value in kwargs.items():
        try:
            # 过滤敏感信息
            if key.lower() in ['password', 'token', 'api_key', 'secret']:
                serialized[key] = "***"
            else:
                serialized[key] = _safe_serialize(value)
        except Exception:
            serialized[key] = "<不可序列化的值>"
    
    return serialized


def _serialize_result(result: Any) -> Any:
    """序列化函数结果"""
    try:
        return _safe_serialize(result)
    except Exception:
        return "<不可序列化的结果>"


def _safe_serialize(obj: Any, max_length: int = 1000) -> Any:
    """安全序列化对象"""
    try:
        # 基本类型直接返回
        if obj is None or isinstance(obj, (bool, int, float, str)):
            if isinstance(obj, str) and len(obj) > max_length:
                return obj[:max_length] + "..."
            return obj
        
        # 列表和元组
        if isinstance(obj, (list, tuple)):
            return [_safe_serialize(item, max_length) for item in obj[:10]]  # 限制长度
        
        # 字典
        if isinstance(obj, dict):
            return {k: _safe_serialize(v, max_length) for k, v in list(obj.items())[:10]}
        
        # 对象有to_dict方法
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
        
        # 对象有__dict__属性
        if hasattr(obj, '__dict__'):
            return {k: _safe_serialize(v, max_length) for k, v in obj.__dict__.items()}
        
        # 其他情况转换为字符串
        str_repr = str(obj)
        if len(str_repr) > max_length:
            str_repr = str_repr[:max_length] + "..."
        return str_repr
        
    except Exception:
        return f"<{type(obj).__name__} 对象>"


# 便捷装饰器定义
def log_ai_model_call(operation_name: Optional[str] = None, **kwargs):
    """AI模型调用日志装饰器"""
    return ai_operation_log(
        operation_type=AIOperationType.AI_MODEL_CALL,
        operation_name=operation_name,
        category="ai_service",
        subcategory="model_call",
        **kwargs
    )


def log_conversation_activity(activity_type: str, operation_name: Optional[str] = None, **kwargs):
    """对话活动日志装饰器"""
    operation_type_map = {
        "create": AIOperationType.CONVERSATION_CREATE,
        "delete": AIOperationType.CONVERSATION_DELETE,
        "send_message": AIOperationType.MESSAGE_SEND,
        "receive_message": AIOperationType.MESSAGE_RECEIVE
    }
    
    return ai_operation_log(
        operation_type=operation_type_map.get(activity_type, AIOperationType.MESSAGE_SEND),
        operation_name=operation_name or f"conversation_{activity_type}",
        category="conversation",
        subcategory=activity_type,
        **kwargs
    )


def log_suggestion_activity(activity_type: str, operation_name: Optional[str] = None, **kwargs):
    """建议活动日志装饰器"""
    operation_type_map = {
        "generate": AIOperationType.SUGGESTION_GENERATE,
        "accept": AIOperationType.SUGGESTION_ACCEPT,
        "reject": AIOperationType.SUGGESTION_REJECT,
        "implement": AIOperationType.SUGGESTION_IMPLEMENT
    }
    
    return ai_operation_log(
        operation_type=operation_type_map.get(activity_type, AIOperationType.SUGGESTION_GENERATE),
        operation_name=operation_name or f"suggestion_{activity_type}",
        category="suggestion",
        subcategory=activity_type,
        **kwargs
    )


def log_security_event(event_type: str, operation_name: Optional[str] = None, **kwargs):
    """安全事件日志装饰器"""
    operation_type_map = {
        "unauthorized_access": AIOperationType.UNAUTHORIZED_ACCESS,
        "rate_limit_exceeded": AIOperationType.RATE_LIMIT_EXCEEDED,
        "suspicious_activity": AIOperationType.SUSPICIOUS_ACTIVITY
    }
    
    return ai_operation_log(
        operation_type=operation_type_map.get(event_type, AIOperationType.SUSPICIOUS_ACTIVITY),
        operation_name=operation_name or f"security_{event_type}",
        category="security",
        subcategory=event_type,
        priority=AIOperationPriority.HIGH,
        is_sensitive=True,
        **kwargs
    )