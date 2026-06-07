"""
需求管理审计服务

本模块实现需求管理模块的审计功能，包括：
- 操作审计日志记录
- 审计日志查询和分析
- 合规性检查
- 审计报告生成
"""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload
from fastapi import Request

from ..models.user import User
from ..models.requirement import Requirement
from ..models.project import Project
from ..models.requirement_permission import (
    RequirementAuditLog, RequirementAuditAction, RequirementAuditResult
)


class RequirementAuditService:
    """需求审计服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_operation(
        self,
        user_id: Optional[int],
        action: RequirementAuditAction,
        result: RequirementAuditResult,
        resource_type: str,
        resource_id: Optional[int] = None,
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        operation_details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        request: Optional[Request] = None,
        operation_start_time: Optional[datetime] = None
    ) -> RequirementAuditLog:
        """记录操作审计日志"""
        # 计算操作耗时
        operation_duration = None
        if operation_start_time:
            duration = datetime.utcnow() - operation_start_time
            operation_duration = int(duration.total_seconds() * 1000)  # 毫秒
        
        # 提取请求信息
        ip_address = None
        user_agent = None
        session_id = None
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")
            session_id = request.headers.get("x-session-id") or request.headers.get("authorization", "")[:50]
        
        # 清理敏感数据
        cleaned_old_values = self._clean_sensitive_data(old_values) if old_values else None
        cleaned_new_values = self._clean_sensitive_data(new_values) if new_values else None
        
        audit_log = RequirementAuditLog(
            user_id=user_id,
            action=action,
            result=result,
            resource_type=resource_type,
            resource_id=resource_id,
            requirement_id=requirement_id,
            project_id=project_id,
            old_values=cleaned_old_values,
            new_values=cleaned_new_values,
            operation_details=operation_details,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            error_message=error_message,
            error_code=error_code,
            operation_duration=operation_duration,
            permission_checked=True
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    async def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[RequirementAuditAction] = None,
        result: Optional[RequirementAuditResult] = None,
        resource_type: Optional[str] = None,
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[RequirementAuditLog], int]:
        """查询审计日志"""
        # 构建查询条件
        conditions = []
        
        if user_id:
            conditions.append(RequirementAuditLog.user_id == user_id)
        
        if action:
            conditions.append(RequirementAuditLog.action == action)
        
        if result:
            conditions.append(RequirementAuditLog.result == result)
        
        if resource_type:
            conditions.append(RequirementAuditLog.resource_type == resource_type)
        
        if requirement_id:
            conditions.append(RequirementAuditLog.requirement_id == requirement_id)
        
        if project_id:
            conditions.append(RequirementAuditLog.project_id == project_id)
        
        if start_date:
            conditions.append(RequirementAuditLog.created_at >= start_date)
        
        if end_date:
            conditions.append(RequirementAuditLog.created_at <= end_date)
        
        if ip_address:
            conditions.append(RequirementAuditLog.ip_address == ip_address)
        
        # 构建基础查询
        base_query = select(RequirementAuditLog).options(
            selectinload(RequirementAuditLog.user),
            selectinload(RequirementAuditLog.requirement),
            selectinload(RequirementAuditLog.project)
        )
        
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # 获取总数
        count_query = select(func.count(RequirementAuditLog.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        # 排序
        if order_direction.lower() == "desc":
            order_func = desc
        else:
            order_func = asc
        
        if hasattr(RequirementAuditLog, order_by):
            base_query = base_query.order_by(order_func(getattr(RequirementAuditLog, order_by)))
        else:
            base_query = base_query.order_by(desc(RequirementAuditLog.created_at))
        
        # 分页
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)
        
        # 执行查询
        result = await self.db.execute(base_query)
        audit_logs = result.scalars().all()
        
        return audit_logs, total_count
    
    async def get_user_activity_summary(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取用户活动摘要"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        
        if not end_date:
            end_date = datetime.utcnow()
        
        # 基础条件
        conditions = [
            RequirementAuditLog.user_id == user_id,
            RequirementAuditLog.created_at >= start_date,
            RequirementAuditLog.created_at <= end_date
        ]
        
        # 总操作数
        total_query = select(func.count(RequirementAuditLog.id)).where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_operations = total_result.scalar()
        
        # 按操作类型统计
        action_query = select(
            RequirementAuditLog.action,
            func.count(RequirementAuditLog.id).label('count')
        ).where(and_(*conditions)).group_by(RequirementAuditLog.action)
        
        action_result = await self.db.execute(action_query)
        action_stats = {row.action.value: row.count for row in action_result}
        
        # 按结果统计
        result_query = select(
            RequirementAuditLog.result,
            func.count(RequirementAuditLog.id).label('count')
        ).where(and_(*conditions)).group_by(RequirementAuditLog.result)
        
        result_result = await self.db.execute(result_query)
        result_stats = {row.result.value: row.count for row in result_result}
        
        # 按日期统计
        daily_query = select(
            func.date(RequirementAuditLog.created_at).label('date'),
            func.count(RequirementAuditLog.id).label('count')
        ).where(and_(*conditions)).group_by(func.date(RequirementAuditLog.created_at))
        
        daily_result = await self.db.execute(daily_query)
        daily_stats = {str(row.date): row.count for row in daily_result}
        
        # 最近操作
        recent_query = select(RequirementAuditLog).options(
            selectinload(RequirementAuditLog.requirement),
            selectinload(RequirementAuditLog.project)
        ).where(and_(*conditions)).order_by(desc(RequirementAuditLog.created_at)).limit(10)
        
        recent_result = await self.db.execute(recent_query)
        recent_operations = recent_result.scalars().all()
        
        return {
            "user_id": user_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_operations": total_operations,
            "action_statistics": action_stats,
            "result_statistics": result_stats,
            "daily_statistics": daily_stats,
            "recent_operations": [log.to_dict() for log in recent_operations]
        }
    
    async def get_requirement_audit_trail(
        self,
        requirement_id: int,
        include_related: bool = True
    ) -> Dict[str, Any]:
        """获取需求的完整审计轨迹"""
        # 基础条件
        conditions = [RequirementAuditLog.requirement_id == requirement_id]
        
        if include_related:
            # 包含相关操作（如评审、变更等）
            related_conditions = [
                RequirementAuditLog.operation_details.contains(f'"requirement_id": {requirement_id}'),
                RequirementAuditLog.old_values.contains(f'"requirement_id": {requirement_id}'),
                RequirementAuditLog.new_values.contains(f'"requirement_id": {requirement_id}')
            ]
            conditions = [or_(RequirementAuditLog.requirement_id == requirement_id, *related_conditions)]
        
        # 获取审计日志
        query = select(RequirementAuditLog).options(
            selectinload(RequirementAuditLog.user),
            selectinload(RequirementAuditLog.requirement),
            selectinload(RequirementAuditLog.project)
        ).where(and_(*conditions)).order_by(RequirementAuditLog.created_at)
        
        result = await self.db.execute(query)
        audit_logs = result.scalars().all()
        
        # 按操作类型分组
        operations_by_type = {}
        for log in audit_logs:
            action = log.action.value
            if action not in operations_by_type:
                operations_by_type[action] = []
            operations_by_type[action].append(log.to_dict())
        
        # 获取需求基本信息
        req_query = select(Requirement).where(Requirement.id == requirement_id)
        req_result = await self.db.execute(req_query)
        requirement = req_result.scalar_one_or_none()
        
        return {
            "requirement_id": requirement_id,
            "requirement_info": requirement.to_dict() if requirement else None,
            "total_operations": len(audit_logs),
            "operations_by_type": operations_by_type,
            "chronological_operations": [log.to_dict() for log in audit_logs],
            "first_operation": audit_logs[0].created_at.isoformat() if audit_logs else None,
            "last_operation": audit_logs[-1].created_at.isoformat() if audit_logs else None
        }
    
    async def get_project_audit_summary(
        self,
        project_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取项目审计摘要"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        
        if not end_date:
            end_date = datetime.utcnow()
        
        # 基础条件
        conditions = [
            RequirementAuditLog.project_id == project_id,
            RequirementAuditLog.created_at >= start_date,
            RequirementAuditLog.created_at <= end_date
        ]
        
        # 总操作数
        total_query = select(func.count(RequirementAuditLog.id)).where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_operations = total_result.scalar()
        
        # 活跃用户统计
        user_query = select(
            RequirementAuditLog.user_id,
            func.count(RequirementAuditLog.id).label('count')
        ).where(and_(*conditions)).group_by(RequirementAuditLog.user_id)
        
        user_result = await self.db.execute(user_query)
        user_stats = {row.user_id: row.count for row in user_result if row.user_id}
        
        # 操作类型统计
        action_query = select(
            RequirementAuditLog.action,
            func.count(RequirementAuditLog.id).label('count')
        ).where(and_(*conditions)).group_by(RequirementAuditLog.action)
        
        action_result = await self.db.execute(action_query)
        action_stats = {row.action.value: row.count for row in action_result}
        
        # 失败操作统计
        failure_query = select(func.count(RequirementAuditLog.id)).where(
            and_(
                *conditions,
                RequirementAuditLog.result.in_([
                    RequirementAuditResult.FAILURE,
                    RequirementAuditResult.UNAUTHORIZED,
                    RequirementAuditResult.FORBIDDEN
                ])
            )
        )
        failure_result = await self.db.execute(failure_query)
        failure_count = failure_result.scalar()
        
        # 获取项目信息
        project_query = select(Project).where(Project.id == project_id)
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        return {
            "project_id": project_id,
            "project_info": {
                "name": project.name if project else None,
                "code": project.project_code if project else None
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_operations": total_operations,
            "active_users": len(user_stats),
            "user_activity": user_stats,
            "action_statistics": action_stats,
            "failure_count": failure_count,
            "success_rate": round((total_operations - failure_count) / total_operations * 100, 2) if total_operations > 0 else 0
        }
    
    async def detect_suspicious_activities(
        self,
        lookback_hours: int = 24,
        threshold_operations: int = 100,
        threshold_failures: int = 10
    ) -> List[Dict[str, Any]]:
        """检测可疑活动"""
        start_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        suspicious_activities = []
        
        # 检测异常高频操作
        high_frequency_query = select(
            RequirementAuditLog.user_id,
            RequirementAuditLog.ip_address,
            func.count(RequirementAuditLog.id).label('count')
        ).where(
            RequirementAuditLog.created_at >= start_time
        ).group_by(
            RequirementAuditLog.user_id,
            RequirementAuditLog.ip_address
        ).having(
            func.count(RequirementAuditLog.id) > threshold_operations
        )
        
        high_freq_result = await self.db.execute(high_frequency_query)
        for row in high_freq_result:
            suspicious_activities.append({
                "type": "HIGH_FREQUENCY_OPERATIONS",
                "user_id": row.user_id,
                "ip_address": row.ip_address,
                "operation_count": row.count,
                "severity": "HIGH" if row.count > threshold_operations * 2 else "MEDIUM"
            })
        
        # 检测高失败率
        high_failure_query = select(
            RequirementAuditLog.user_id,
            RequirementAuditLog.ip_address,
            func.count(RequirementAuditLog.id).label('total'),
            func.sum(
                func.case(
                    (RequirementAuditLog.result == RequirementAuditResult.FAILURE, 1),
                    else_=0
                )
            ).label('failures')
        ).where(
            RequirementAuditLog.created_at >= start_time
        ).group_by(
            RequirementAuditLog.user_id,
            RequirementAuditLog.ip_address
        ).having(
            func.sum(
                func.case(
                    (RequirementAuditLog.result == RequirementAuditResult.FAILURE, 1),
                    else_=0
                )
            ) > threshold_failures
        )
        
        high_failure_result = await self.db.execute(high_failure_query)
        for row in high_failure_result:
            failure_rate = (row.failures / row.total) * 100 if row.total > 0 else 0
            suspicious_activities.append({
                "type": "HIGH_FAILURE_RATE",
                "user_id": row.user_id,
                "ip_address": row.ip_address,
                "total_operations": row.total,
                "failure_count": row.failures,
                "failure_rate": round(failure_rate, 2),
                "severity": "HIGH" if failure_rate > 50 else "MEDIUM"
            })
        
        # 检测异常IP地址
        unusual_ip_query = select(
            RequirementAuditLog.user_id,
            RequirementAuditLog.ip_address,
            func.count(RequirementAuditLog.id).label('count')
        ).where(
            and_(
                RequirementAuditLog.created_at >= start_time,
                RequirementAuditLog.user_id.isnot(None)
            )
        ).group_by(
            RequirementAuditLog.user_id,
            RequirementAuditLog.ip_address
        )
        
        # 这里可以添加更复杂的异常IP检测逻辑
        
        return suspicious_activities
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """生成合规性报告"""
        conditions = [
            RequirementAuditLog.created_at >= start_date,
            RequirementAuditLog.created_at <= end_date
        ]
        
        if project_id:
            conditions.append(RequirementAuditLog.project_id == project_id)
        
        # 总操作统计
        total_query = select(func.count(RequirementAuditLog.id)).where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_operations = total_result.scalar()
        
        # 权限检查覆盖率
        permission_checked_query = select(
            func.count(RequirementAuditLog.id)
        ).where(
            and_(*conditions, RequirementAuditLog.permission_checked == True)
        )
        permission_checked_result = await self.db.execute(permission_checked_query)
        permission_checked_count = permission_checked_result.scalar()
        
        permission_coverage = (permission_checked_count / total_operations * 100) if total_operations > 0 else 0
        
        # 敏感操作统计
        sensitive_actions = [
            RequirementAuditAction.DELETE_REQUIREMENT,
            RequirementAuditAction.GRANT_PERMISSION,
            RequirementAuditAction.REVOKE_PERMISSION,
            RequirementAuditAction.BULK_UPDATE
        ]
        
        sensitive_query = select(
            RequirementAuditLog.action,
            func.count(RequirementAuditLog.id).label('count')
        ).where(
            and_(*conditions, RequirementAuditLog.action.in_(sensitive_actions))
        ).group_by(RequirementAuditLog.action)
        
        sensitive_result = await self.db.execute(sensitive_query)
        sensitive_operations = {row.action.value: row.count for row in sensitive_result}
        
        # 失败操作分析
        failure_query = select(
            RequirementAuditLog.action,
            RequirementAuditLog.error_code,
            func.count(RequirementAuditLog.id).label('count')
        ).where(
            and_(*conditions, RequirementAuditLog.result == RequirementAuditResult.FAILURE)
        ).group_by(RequirementAuditLog.action, RequirementAuditLog.error_code)
        
        failure_result = await self.db.execute(failure_query)
        failure_analysis = [
            {
                "action": row.action.value,
                "error_code": row.error_code,
                "count": row.count
            }
            for row in failure_result
        ]
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "project_id": project_id,
            "total_operations": total_operations,
            "permission_coverage": round(permission_coverage, 2),
            "sensitive_operations": sensitive_operations,
            "failure_analysis": failure_analysis,
            "compliance_score": self._calculate_compliance_score(
                permission_coverage, len(failure_analysis), total_operations
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 使用直接连接IP
        if request.client:
            return request.client.host
        
        return None
    
    def _clean_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理敏感数据"""
        if not data:
            return data
        
        sensitive_fields = ["password", "token", "secret", "key", "credential"]
        cleaned_data = data.copy()
        
        for key in list(cleaned_data.keys()):
            if any(sensitive_field in key.lower() for sensitive_field in sensitive_fields):
                cleaned_data[key] = "***REDACTED***"
        
        return cleaned_data
    
    def _calculate_compliance_score(
        self, 
        permission_coverage: float, 
        failure_count: int, 
        total_operations: int
    ) -> float:
        """计算合规性评分"""
        # 基础分数
        base_score = 100.0
        
        # 权限检查覆盖率扣分
        if permission_coverage < 100:
            base_score -= (100 - permission_coverage) * 0.5
        
        # 失败率扣分
        if total_operations > 0:
            failure_rate = (failure_count / total_operations) * 100
            base_score -= failure_rate * 0.3
        
        return max(0, round(base_score, 2))