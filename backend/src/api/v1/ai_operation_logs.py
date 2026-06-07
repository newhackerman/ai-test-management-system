"""
AI助手操作日志API接口

提供AI助手操作日志的查询、统计、导出等功能，包括：
1. 日志查询和过滤
2. 统计分析和报告
3. 日志导出和下载
4. 实时监控和告警
5. 日志管理和维护
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import io
import json

from ...core.security import get_current_user
from ...models.user import User
from ...models.ai_operation_log import AIOperationType, AIOperationResult, AIOperationPriority
from ...services.ai_operation_log_service import get_ai_operation_log_service
from ...services.ai_permission_service import AIPermissionService
from ...schemas.base import ApiResponse, PaginatedResponse
from ...decorators.ai_operation_logger import ai_operation_log

router = APIRouter(prefix="/ai/operation-logs", tags=["AI操作日志"])


@router.get("", response_model=ApiResponse[PaginatedResponse])
@ai_operation_log(
    operation_type=AIOperationType.DATA_EXPORT,
    operation_name="query_operation_logs",
    category="log_management",
    subcategory="query",
    extract_user_id="current_user.id"
)
async def get_operation_logs(
    user_id: Optional[int] = Query(None, description="用户ID"),
    operation_type: Optional[str] = Query(None, description="操作类型"),
    result: Optional[str] = Query(None, description="操作结果"),
    ai_provider: Optional[str] = Query(None, description="AI服务提供商"),
    category: Optional[str] = Query(None, description="分类"),
    priority: Optional[str] = Query(None, description="优先级"),
    is_sensitive: Optional[bool] = Query(None, description="是否敏感操作"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    search_keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="页大小"),
    order_by: str = Query("created_at", description="排序字段"),
    order_desc: bool = Query(True, description="是否降序"),
    current_user: User = Depends(get_current_user)
):
    """
    查询AI操作日志
    
    支持多维度过滤和搜索：
    - 按用户、操作类型、结果等过滤
    - 按时间范围查询
    - 关键词搜索
    - 分页和排序
    """
    try:
        # 权限检查
        permission_service = AIPermissionService()
        
        # 检查是否有查看日志的权限
        has_permission, message = await permission_service.check_ai_operation_permission(
            current_user.id, "log_view"
        )
        
        if not has_permission:
            # 如果没有查看所有日志的权限，只能查看自己的日志
            if user_id and user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限查看其他用户的操作日志"
                )
            user_id = current_user.id
        
        # 解析日期参数
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="开始日期格式错误，请使用 YYYY-MM-DD 格式"
                )
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="结束日期格式错误，请使用 YYYY-MM-DD 格式"
                )
        
        # 解析枚举参数
        operation_type_enum = None
        if operation_type:
            try:
                operation_type_enum = AIOperationType(operation_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的操作类型: {operation_type}"
                )
        
        result_enum = None
        if result:
            try:
                result_enum = AIOperationResult(result)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的操作结果: {result}"
                )
        
        # 获取日志服务
        log_service = await get_ai_operation_log_service()
        
        # 查询日志
        logs, total = await log_service.get_operation_logs(
            user_id=user_id,
            operation_type=operation_type_enum,
            result=result_enum,
            start_date=start_datetime,
            end_date=end_datetime,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc
        )
        
        # 如果有搜索关键词，进行客户端过滤
        if search_keyword:
            filtered_logs = []
            keyword_lower = search_keyword.lower()
            for log in logs:
                if (keyword_lower in log.get('operation_name', '').lower() or
                    keyword_lower in log.get('operation_description', '').lower() or
                    keyword_lower in log.get('result_message', '').lower() or
                    keyword_lower in log.get('error_details', '').lower()):
                    filtered_logs.append(log)
            logs = filtered_logs
            total = len(logs)
        
        # 构建分页响应
        paginated_response = PaginatedResponse(
            items=logs,
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size
        )
        
        return ApiResponse(
            success=True,
            data=paginated_response,
            message="查询操作日志成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询操作日志失败: {str(e)}"
        )


@router.get("/statistics", response_model=ApiResponse[Dict[str, Any]])
@ai_operation_log(
    operation_type=AIOperationType.DATA_EXPORT,
    operation_name="get_operation_statistics",
    category="log_management",
    subcategory="statistics",
    extract_user_id="current_user.id"
)
async def get_operation_statistics(
    user_id: Optional[int] = Query(None, description="用户ID"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    group_by: str = Query("operation_type", description="分组字段"),
    current_user: User = Depends(get_current_user)
):
    """
    获取AI操作统计信息
    
    支持多维度统计分析：
    - 按操作类型、结果、AI提供商等分组
    - 按时间范围统计
    - 性能指标分析
    - 成本统计
    """
    try:
        # 权限检查
        permission_service = AIPermissionService()
        
        has_permission, _ = await permission_service.check_ai_operation_permission(
            current_user.id, "log_view"
        )
        
        if not has_permission:
            if user_id and user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限查看其他用户的统计信息"
                )
            user_id = current_user.id
        
        # 解析日期参数
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="开始日期格式错误"
                )
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="结束日期格式错误"
                )
        
        # 验证分组字段
        valid_group_by = ["operation_type", "result", "ai_provider", "date", "overall"]
        if group_by not in valid_group_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的分组字段，支持的字段: {', '.join(valid_group_by)}"
            )
        
        # 获取统计信息
        log_service = await get_ai_operation_log_service()
        statistics = await log_service.get_operation_statistics(
            user_id=user_id,
            start_date=start_datetime,
            end_date=end_datetime,
            group_by=group_by
        )
        
        return ApiResponse(
            success=True,
            data=statistics,
            message="获取统计信息成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/export")
@ai_operation_log(
    operation_type=AIOperationType.DATA_EXPORT,
    operation_name="export_operation_logs",
    category="log_management",
    subcategory="export",
    extract_user_id="current_user.id"
)
async def export_operation_logs(
    format_type: str = Query("json", description="导出格式 (json, csv)"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    operation_type: Optional[str] = Query(None, description="操作类型"),
    current_user: User = Depends(get_current_user)
):
    """
    导出AI操作日志
    
    支持多种导出格式：
    - JSON格式：完整的结构化数据
    - CSV格式：表格数据，便于Excel处理
    """
    try:
        # 权限检查
        permission_service = AIPermissionService()
        
        has_permission, _ = await permission_service.check_ai_operation_permission(
            current_user.id, "log_export"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限导出操作日志"
            )
        
        # 验证导出格式
        if format_type not in ["json", "csv"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的导出格式，支持: json, csv"
            )
        
        # 解析日期参数
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="开始日期格式错误"
                )
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="结束日期格式错误"
                )
        
        # 导出日志
        log_service = await get_ai_operation_log_service()
        export_data = await log_service.export_logs(
            user_id=user_id,
            start_date=start_datetime,
            end_date=end_datetime,
            format_type=format_type
        )
        
        if not export_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到符合条件的日志数据"
            )
        
        # 设置响应头
        filename = f"ai_operation_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format_type == "json":
            media_type = "application/json"
            filename += ".json"
        else:  # csv
            media_type = "text/csv"
            filename += ".csv"
        
        # 创建流式响应
        def generate():
            yield export_data.encode('utf-8')
        
        return StreamingResponse(
            generate(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": f"{media_type}; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出日志失败: {str(e)}"
        )


@router.get("/types", response_model=ApiResponse[List[Dict[str, str]]])
async def get_operation_types():
    """
    获取所有操作类型
    
    返回系统支持的所有AI操作类型，用于前端下拉选择等场景
    """
    try:
        operation_types = []
        
        for op_type in AIOperationType:
            operation_types.append({
                "value": op_type.value,
                "label": _get_operation_type_label(op_type),
                "category": _get_operation_type_category(op_type)
            })
        
        return ApiResponse(
            success=True,
            data=operation_types,
            message="获取操作类型成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取操作类型失败: {str(e)}"
        )


@router.delete("/cleanup")
@ai_operation_log(
    operation_type=AIOperationType.DATA_BACKUP,
    operation_name="cleanup_old_logs",
    category="log_management",
    subcategory="cleanup",
    priority=AIOperationPriority.HIGH,
    extract_user_id="current_user.id"
)
async def cleanup_old_logs(
    days_to_keep: int = Query(90, ge=7, le=365, description="保留天数"),
    current_user: User = Depends(get_current_user)
):
    """
    清理旧的操作日志
    
    删除指定天数之前的非敏感日志记录，释放存储空间
    """
    try:
        # 权限检查 - 只有管理员可以清理日志
        permission_service = AIPermissionService()
        
        has_permission, _ = await permission_service.check_ai_operation_permission(
            current_user.id, "log_admin"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限执行日志清理操作"
            )
        
        # 执行清理
        log_service = await get_ai_operation_log_service()
        cleaned_count = await log_service.cleanup_old_logs(days_to_keep)
        
        return ApiResponse(
            success=True,
            data={"cleaned_count": cleaned_count, "days_to_keep": days_to_keep},
            message=f"成功清理了 {cleaned_count} 条旧日志记录"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理日志失败: {str(e)}"
        )


@router.post("/summary/generate")
@ai_operation_log(
    operation_type=AIOperationType.DATA_BACKUP,
    operation_name="generate_log_summary",
    category="log_management",
    subcategory="summary",
    priority=AIOperationPriority.MEDIUM,
    extract_user_id="current_user.id"
)
async def generate_log_summary(
    target_date: Optional[str] = Query(None, description="目标日期 (YYYY-MM-DD)，默认为昨天"),
    current_user: User = Depends(get_current_user)
):
    """
    生成日志汇总
    
    为指定日期生成操作日志的汇总统计，用于报告和分析
    """
    try:
        # 权限检查
        permission_service = AIPermissionService()
        
        has_permission, _ = await permission_service.check_ai_operation_permission(
            current_user.id, "log_admin"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限执行日志汇总操作"
            )
        
        # 解析目标日期
        target_datetime = None
        if target_date:
            try:
                target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="目标日期格式错误，请使用 YYYY-MM-DD 格式"
                )
        
        # 生成汇总
        log_service = await get_ai_operation_log_service()
        success = await log_service.generate_daily_summary(target_datetime)
        
        if success:
            return ApiResponse(
                success=True,
                data={"target_date": target_date or "昨天"},
                message="日志汇总生成成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="日志汇总生成失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成日志汇总失败: {str(e)}"
        )


def _get_operation_type_label(op_type: AIOperationType) -> str:
    """获取操作类型的中文标签"""
    labels = {
        AIOperationType.CONVERSATION_CREATE: "创建对话",
        AIOperationType.CONVERSATION_DELETE: "删除对话",
        AIOperationType.MESSAGE_SEND: "发送消息",
        AIOperationType.MESSAGE_RECEIVE: "接收消息",
        AIOperationType.AI_MODEL_CALL: "AI模型调用",
        AIOperationType.AI_STREAMING_START: "开始流式响应",
        AIOperationType.AI_STREAMING_COMPLETE: "完成流式响应",
        AIOperationType.SUGGESTION_GENERATE: "生成建议",
        AIOperationType.SUGGESTION_ACCEPT: "接受建议",
        AIOperationType.SUGGESTION_REJECT: "拒绝建议",
        AIOperationType.SUGGESTION_IMPLEMENT: "实施建议",
        AIOperationType.TEMPLATE_CREATE: "创建模板",
        AIOperationType.TEMPLATE_UPDATE: "更新模板",
        AIOperationType.TEMPLATE_DELETE: "删除模板",
        AIOperationType.TEMPLATE_USE: "使用模板",
        AIOperationType.TEMPLATE_SHARE: "分享模板",
        AIOperationType.AI_CONFIG_UPDATE: "更新AI配置",
        AIOperationType.MODEL_CONFIG_CHANGE: "模型配置变更",
        AIOperationType.PERMISSION_GRANT: "授予权限",
        AIOperationType.PERMISSION_REVOKE: "撤销权限",
        AIOperationType.SERVICE_START: "服务启动",
        AIOperationType.SERVICE_STOP: "服务停止",
        AIOperationType.HEALTH_CHECK: "健康检查",
        AIOperationType.ERROR_OCCURRED: "错误发生",
        AIOperationType.DATA_EXPORT: "数据导出",
        AIOperationType.DATA_IMPORT: "数据导入",
        AIOperationType.DATA_BACKUP: "数据备份",
        AIOperationType.DATA_RESTORE: "数据恢复",
        AIOperationType.UNAUTHORIZED_ACCESS: "未授权访问",
        AIOperationType.RATE_LIMIT_EXCEEDED: "超出速率限制",
        AIOperationType.SUSPICIOUS_ACTIVITY: "可疑活动"
    }
    return labels.get(op_type, op_type.value)


def _get_operation_type_category(op_type: AIOperationType) -> str:
    """获取操作类型的分类"""
    categories = {
        AIOperationType.CONVERSATION_CREATE: "对话管理",
        AIOperationType.CONVERSATION_DELETE: "对话管理",
        AIOperationType.MESSAGE_SEND: "对话管理",
        AIOperationType.MESSAGE_RECEIVE: "对话管理",
        AIOperationType.AI_MODEL_CALL: "AI服务",
        AIOperationType.AI_STREAMING_START: "AI服务",
        AIOperationType.AI_STREAMING_COMPLETE: "AI服务",
        AIOperationType.SUGGESTION_GENERATE: "建议系统",
        AIOperationType.SUGGESTION_ACCEPT: "建议系统",
        AIOperationType.SUGGESTION_REJECT: "建议系统",
        AIOperationType.SUGGESTION_IMPLEMENT: "建议系统",
        AIOperationType.TEMPLATE_CREATE: "模板管理",
        AIOperationType.TEMPLATE_UPDATE: "模板管理",
        AIOperationType.TEMPLATE_DELETE: "模板管理",
        AIOperationType.TEMPLATE_USE: "模板管理",
        AIOperationType.TEMPLATE_SHARE: "模板管理",
        AIOperationType.AI_CONFIG_UPDATE: "配置管理",
        AIOperationType.MODEL_CONFIG_CHANGE: "配置管理",
        AIOperationType.PERMISSION_GRANT: "权限管理",
        AIOperationType.PERMISSION_REVOKE: "权限管理",
        AIOperationType.SERVICE_START: "系统管理",
        AIOperationType.SERVICE_STOP: "系统管理",
        AIOperationType.HEALTH_CHECK: "系统管理",
        AIOperationType.ERROR_OCCURRED: "系统管理",
        AIOperationType.DATA_EXPORT: "数据管理",
        AIOperationType.DATA_IMPORT: "数据管理",
        AIOperationType.DATA_BACKUP: "数据管理",
        AIOperationType.DATA_RESTORE: "数据管理",
        AIOperationType.UNAUTHORIZED_ACCESS: "安全管理",
        AIOperationType.RATE_LIMIT_EXCEEDED: "安全管理",
        AIOperationType.SUSPICIOUS_ACTIVITY: "安全管理"
    }
    return categories.get(op_type, "其他")