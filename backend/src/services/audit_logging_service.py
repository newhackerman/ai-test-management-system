"""
操作审计日志服务
提供用户操作的详细审计记录和分析功能
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from ..models.audit import AuditLog, AuditAction, AuditResult
from ..models.user import User
from ..core.redis import redis_service
from ..utils.security_utils import SecurityUtils
from ..utils.ip import IPUtils

logger = logging.getLogger(__name__)


class AuditLoggingService:
    """操作审计日志服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_prefix = "audit_logging"
        self.cache_ttl = 1800  # 30分钟缓存
    
    async def log_user_operation(
        self,
        user_id: Optional[int],
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        result: AuditResult = AuditResult.SUCCESS,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        记录用户操作审计日志
        
        Args:
            user_id: 用户ID
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            result: 操作结果
            old_values: 操作前的值
            new_values: 操作后的值
            error_message: 错误信息
            ip_address: IP地址
            user_agent: 用户代理
            session_id: 会话ID
            extra_data: 额外数据
            
        Returns:
            AuditLog: 审计日志记录
        """
        try:
            # 创建审计日志记录
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=result,
                old_values=old_values,
                new_values=new_values,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                extra_data=extra_data,
                created_at=datetime.utcnow()
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            await self.db.refresh(audit_log)
            
            # 异步处理审计日志分析
            await self._analyze_audit_log(audit_log)
            
            logger.info(f"审计日志记录成功: {action.value} - {resource_type}:{resource_id}")
            return audit_log
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"记录审计日志失败: {e}")
            raise
    
    async def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        result: Optional[AuditResult] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[AuditLog], int]:
        """
        获取审计日志列表
        
        Args:
            user_id: 用户ID
            action: 操作类型
            resource_type: 资源类型
            result: 操作结果
            start_time: 开始时间
            end_time: 结束时间
            ip_address: IP地址
            page: 页码
            size: 每页数量
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            Tuple[List[AuditLog], int]: 审计日志列表和总数
        """
        try:
            # 构建查询条件
            conditions = []
            
            if user_id:
                conditions.append(AuditLog.user_id == user_id)
            
            if action:
                conditions.append(AuditLog.action == action)
            
            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type)
            
            if result:
                conditions.append(AuditLog.result == result)
            
            if start_time:
                conditions.append(AuditLog.created_at >= start_time)
            
            if end_time:
                conditions.append(AuditLog.created_at <= end_time)
            
            if ip_address:
                conditions.append(AuditLog.ip_address == ip_address)
            
            # 查询总数
            count_query = select(func.count(AuditLog.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # 查询审计日志列表
            offset = (page - 1) * size
            query = select(AuditLog).options(selectinload(AuditLog.user))
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # 排序
            order_column = getattr(AuditLog, order_by, AuditLog.created_at)
            if order_desc:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
            
            query = query.offset(offset).limit(size)
            
            result = await self.db.execute(query)
            audit_logs = list(result.scalars().all())
            
            return audit_logs, total
            
        except Exception as e:
            logger.error(f"获取审计日志失败: {e}")
            return [], 0
    
    async def get_user_operation_summary(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取用户操作摘要
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            Dict[str, Any]: 用户操作摘要
        """
        try:
            # 计算时间范围
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # 查询用户操作统计
            query = (
                select(
                    AuditLog.action,
                    AuditLog.result,
                    func.count(AuditLog.id).label('count')
                )
                .where(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time
                    )
                )
                .group_by(AuditLog.action, AuditLog.result)
            )
            
            result = await self.db.execute(query)
            operation_stats = result.all()
            
            # 统计数据处理
            summary = {
                "user_id": user_id,
                "period_days": days,
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "action_distribution": {},
                "result_distribution": {
                    "SUCCESS": 0,
                    "FAILURE": 0,
                    "PARTIAL": 0
                },
                "daily_activity": []
            }
            
            for action, result_type, count in operation_stats:
                summary["total_operations"] += count
                
                if result_type == AuditResult.SUCCESS:
                    summary["successful_operations"] += count
                else:
                    summary["failed_operations"] += count
                
                # 操作类型分布
                action_key = action.value
                if action_key not in summary["action_distribution"]:
                    summary["action_distribution"][action_key] = 0
                summary["action_distribution"][action_key] += count
                
                # 结果分布
                result_key = result_type.value
                summary["result_distribution"][result_key] += count
            
            # 获取每日活动统计
            daily_query = (
                select(
                    func.date(AuditLog.created_at).label('date'),
                    func.count(AuditLog.id).label('count')
                )
                .where(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time
                    )
                )
                .group_by(func.date(AuditLog.created_at))
                .order_by(func.date(AuditLog.created_at))
            )
            
            daily_result = await self.db.execute(daily_query)
            daily_stats = daily_result.all()
            
            summary["daily_activity"] = [
                {
                    "date": date.isoformat(),
                    "count": count
                }
                for date, count in daily_stats
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"获取用户操作摘要失败: {e}")
            return {}
    
    async def get_system_audit_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取系统审计统计
        
        Args:
            days: 统计天数
            
        Returns:
            Dict[str, Any]: 系统审计统计
        """
        try:
            # 计算时间范围
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # 总体统计
            total_query = (
                select(func.count(AuditLog.id))
                .where(
                    and_(
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time
                    )
                )
            )
            
            total_result = await self.db.execute(total_query)
            total_operations = total_result.scalar() or 0
            
            # 按操作类型统计
            action_query = (
                select(
                    AuditLog.action,
                    func.count(AuditLog.id).label('count')
                )
                .where(
                    and_(
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time
                    )
                )
                .group_by(AuditLog.action)
                .order_by(desc(func.count(AuditLog.id)))
            )
            
            action_result = await self.db.execute(action_query)
            action_stats = action_result.all()
            
            # 按资源类型统计
            resource_query = (
                select(
                    AuditLog.resource_type,
                    func.count(AuditLog.id).label('count')
                )
                .where(
                    and_(
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time
                    )
                )
                .group_by(AuditLog.resource_type)
                .order_by(desc(func.count(AuditLog.id)))
            )
            
            resource_result = await self.db.execute(resource_query)
            resource_stats = resource_result.all()
            
            # 按结果统计
            result_query = (
                select(
                    AuditLog.result,
                    func.count(AuditLog.id).label('count')
                )
                .where(
                    and_(
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time
                    )
                )
                .group_by(AuditLog.result)
            )
            
            result_result = await self.db.execute(result_query)
            result_stats = result_result.all()
            
            # 活跃用户统计
            user_query = (
                select(
                    func.count(func.distinct(AuditLog.user_id))
                )
                .where(
                    and_(
                        AuditLog.created_at >= start_time,
                        AuditLog.created_at <= end_time,
                        AuditLog.user_id.isnot(None)
                    )
                )
            )
            
            user_result = await self.db.execute(user_query)
            active_users = user_result.scalar() or 0
            
            # 构建统计结果
            statistics = {
                "period_days": days,
                "total_operations": total_operations,
                "active_users": active_users,
                "action_distribution": {
                    action.value: count for action, count in action_stats
                },
                "resource_distribution": {
                    resource_type: count for resource_type, count in resource_stats
                },
                "result_distribution": {
                    result.value: count for result, count in result_stats
                },
                "success_rate": 0.0
            }
            
            # 计算成功率
            success_count = statistics["result_distribution"].get("SUCCESS", 0)
            if total_operations > 0:
                statistics["success_rate"] = (success_count / total_operations) * 100
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取系统审计统计失败: {e}")
            return {}
    
    async def get_security_events(
        self,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取安全事件
        
        Args:
            days: 查询天数
            severity: 严重程度
            
        Returns:
            List[Dict[str, Any]]: 安全事件列表
        """
        try:
            # 计算时间范围
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # 定义安全相关的操作
            security_actions = [
                AuditAction.LOGIN,
                AuditAction.LOGOUT,
                AuditAction.ASSIGN,
                AuditAction.REVOKE,
                AuditAction.DELETE
            ]
            
            # 查询安全事件
            conditions = [
                AuditLog.created_at >= start_time,
                AuditLog.created_at <= end_time,
                or_(
                    AuditLog.action.in_(security_actions),
                    AuditLog.result == AuditResult.FAILURE
                )
            ]
            
            query = (
                select(AuditLog)
                .options(selectinload(AuditLog.user))
                .where(and_(*conditions))
                .order_by(desc(AuditLog.created_at))
                .limit(100)
            )
            
            result = await self.db.execute(query)
            audit_logs = result.scalars().all()
            
            # 转换为安全事件格式
            security_events = []
            for log in audit_logs:
                event = {
                    "id": log.id,
                    "timestamp": log.created_at.isoformat(),
                    "user_id": log.user_id,
                    "username": log.user.username if log.user else "Unknown",
                    "action": log.action.value,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "result": log.result.value,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "severity": self._calculate_event_severity(log),
                    "description": self._generate_event_description(log)
                }
                
                # 根据严重程度过滤
                if severity and event["severity"] != severity:
                    continue
                
                security_events.append(event)
            
            return security_events
            
        except Exception as e:
            logger.error(f"获取安全事件失败: {e}")
            return []
    
    async def export_audit_logs(
        self,
        format_type: str = "csv",
        filters: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        导出审计日志
        
        Args:
            format_type: 导出格式 (csv, excel, json)
            filters: 过滤条件
            
        Returns:
            bytes: 导出的文件内容
        """
        try:
            # 获取审计日志数据
            filters = filters or {}
            audit_logs, _ = await self.get_audit_logs(
                user_id=filters.get("user_id"),
                action=filters.get("action"),
                resource_type=filters.get("resource_type"),
                result=filters.get("result"),
                start_time=filters.get("start_time"),
                end_time=filters.get("end_time"),
                size=10000  # 导出限制
            )
            
            if format_type == "csv":
                return await self._export_to_csv(audit_logs)
            elif format_type == "excel":
                return await self._export_to_excel(audit_logs)
            elif format_type == "json":
                return await self._export_to_json(audit_logs)
            else:
                raise ValueError(f"不支持的导出格式: {format_type}")
                
        except Exception as e:
            logger.error(f"导出审计日志失败: {e}")
            raise
    
    # 私有方法
    async def _analyze_audit_log(self, audit_log: AuditLog) -> None:
        """分析审计日志，检测异常行为"""
        try:
            # 检测可疑活动
            if await self._is_suspicious_activity(audit_log):
                await self._handle_suspicious_activity(audit_log)
            
            # 更新用户活动统计
            await self._update_user_activity_stats(audit_log)
            
        except Exception as e:
            logger.error(f"分析审计日志失败: {e}")
    
    async def _is_suspicious_activity(self, audit_log: AuditLog) -> bool:
        """检测是否为可疑活动"""
        try:
            # 检测频繁失败操作
            if audit_log.result == AuditResult.FAILURE:
                recent_failures = await self._count_recent_failures(
                    audit_log.user_id,
                    audit_log.action,
                    minutes=10
                )
                if recent_failures >= 5:
                    return True
            
            # 检测异常IP地址
            if audit_log.ip_address:
                if await self._is_suspicious_ip(audit_log.ip_address):
                    return True
            
            # 检测权限提升操作
            if audit_log.action in [AuditAction.ASSIGN, AuditAction.CREATE]:
                if audit_log.resource_type in ["role", "permission"]:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检测可疑活动失败: {e}")
            return False
    
    async def _count_recent_failures(
        self,
        user_id: Optional[int],
        action: AuditAction,
        minutes: int = 10
    ) -> int:
        """统计最近的失败次数"""
        try:
            start_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            query = (
                select(func.count(AuditLog.id))
                .where(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.action == action,
                        AuditLog.result == AuditResult.FAILURE,
                        AuditLog.created_at >= start_time
                    )
                )
            )
            
            result = await self.db.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"统计失败次数失败: {e}")
            return 0
    
    async def _is_suspicious_ip(self, ip_address: str) -> bool:
        """检测是否为可疑IP地址"""
        try:
            # 检查IP地址是否在黑名单中
            cache_key = f"{self.cache_prefix}:suspicious_ip:{ip_address}"
            cached_result = await redis_service.get(cache_key)
            
            if cached_result is not None:
                return cached_result == "true"
            
            # 这里可以集成第三方威胁情报API
            # 简化实现：检查是否为内网IP
            is_suspicious = not IPUtils.is_private_ip(ip_address)
            
            # 缓存结果
            await redis_service.set(
                cache_key,
                "true" if is_suspicious else "false",
                expire=3600
            )
            
            return is_suspicious
            
        except Exception as e:
            logger.error(f"检测可疑IP失败: {e}")
            return False
    
    async def _handle_suspicious_activity(self, audit_log: AuditLog) -> None:
        """处理可疑活动"""
        try:
            # 记录安全事件
            logger.warning(f"检测到可疑活动: {audit_log.action.value} - {audit_log.resource_type}")
            
            # 这里可以触发安全告警
            # await self.security_alert_service.send_alert(audit_log)
            
        except Exception as e:
            logger.error(f"处理可疑活动失败: {e}")
    
    async def _update_user_activity_stats(self, audit_log: AuditLog) -> None:
        """更新用户活动统计"""
        try:
            if not audit_log.user_id:
                return
            
            # 更新Redis中的用户活动统计
            cache_key = f"{self.cache_prefix}:user_activity:{audit_log.user_id}"
            
            # 增加操作计数
            await redis_service.incr(cache_key)
            await redis_service.expire(cache_key, 86400)  # 24小时过期
            
        except Exception as e:
            logger.error(f"更新用户活动统计失败: {e}")
    
    def _calculate_event_severity(self, audit_log: AuditLog) -> str:
        """计算事件严重程度"""
        if audit_log.result == AuditResult.FAILURE:
            if audit_log.action in [AuditAction.LOGIN, AuditAction.DELETE]:
                return "HIGH"
            else:
                return "MEDIUM"
        elif audit_log.action in [AuditAction.ASSIGN, AuditAction.REVOKE]:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_event_description(self, audit_log: AuditLog) -> str:
        """生成事件描述"""
        action_desc = {
            AuditAction.LOGIN: "用户登录",
            AuditAction.LOGOUT: "用户登出",
            AuditAction.CREATE: "创建资源",
            AuditAction.UPDATE: "更新资源",
            AuditAction.DELETE: "删除资源",
            AuditAction.ASSIGN: "分配权限",
            AuditAction.REVOKE: "撤销权限"
        }
        
        action_text = action_desc.get(audit_log.action, audit_log.action.value)
        result_text = "成功" if audit_log.result == AuditResult.SUCCESS else "失败"
        
        return f"{action_text} {audit_log.resource_type} {result_text}"
    
    async def _export_to_csv(self, audit_logs: List[AuditLog]) -> bytes:
        """导出为CSV格式"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        writer.writerow([
            "ID", "用户ID", "用户名", "操作", "资源类型", "资源ID",
            "结果", "IP地址", "创建时间", "错误信息"
        ])
        
        # 写入数据行
        for log in audit_logs:
            writer.writerow([
                log.id,
                log.user_id,
                log.user.username if log.user else "",
                log.action.value,
                log.resource_type,
                log.resource_id,
                log.result.value,
                log.ip_address or "",
                log.created_at.isoformat(),
                log.error_message or ""
            ])
        
        return output.getvalue().encode('utf-8-sig')
    
    async def _export_to_excel(self, audit_logs: List[AuditLog]) -> bytes:
        """导出为Excel格式"""
        import pandas as pd
        import io
        
        # 准备数据
        data = []
        for log in audit_logs:
            data.append({
                "ID": log.id,
                "用户ID": log.user_id,
                "用户名": log.user.username if log.user else "",
                "操作": log.action.value,
                "资源类型": log.resource_type,
                "资源ID": log.resource_id,
                "结果": log.result.value,
                "IP地址": log.ip_address or "",
                "创建时间": log.created_at.isoformat(),
                "错误信息": log.error_message or ""
            })
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 导出为Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='审计日志', index=False)
        
        return output.getvalue()
    
    async def _export_to_json(self, audit_logs: List[AuditLog]) -> bytes:
        """导出为JSON格式"""
        import json
        
        data = []
        for log in audit_logs:
            data.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else None,
                "action": log.action.value,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "result": log.result.value,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "error_message": log.error_message,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "session_id": log.session_id,
                "extra_data": log.extra_data,
                "created_at": log.created_at.isoformat()
            })
        
        return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')