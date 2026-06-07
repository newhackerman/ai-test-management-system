"""
缺陷通知和协作服务

本模块实现了缺陷管理的通知和协作功能，包括：
- 缺陷状态变更的实时通知
- 缺陷讨论和协作功能
- 缺陷处理的SLA监控
- 缺陷处理效率统计和分析
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..models.test_case import Defect, DefectStatus
from ..models.user import User
from ..schemas.defect import DefectComment, DefectCommentRequest
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..utils.redis_client import RedisClient
from .notification_service import NotificationService
from .email_service import EmailService

logger = logging.getLogger(__name__)

class DefectNotificationService:
    """缺陷通知和协作服务"""
    
    def __init__(self, db: Session, redis_client: RedisClient, 
                 notification_service: NotificationService, email_service: EmailService):
        self.db = db
        self.redis = redis_client
        self.notification_service = notification_service
        self.email_service = email_service
    
    async def send_defect_created_notification(self, defect: Defect):
        """发送缺陷创建通知"""
        try:
            # 1. 获取通知接收人
            recipients = await self._get_defect_notification_recipients(defect, 'created')
            
            # 2. 构建通知内容
            notification_data = {
                'type': 'defect_created',
                'defect_id': defect.id,
                'defect_code': defect.defect_code,
                'title': defect.title,
                'severity': defect.severity.value,
                'reporter': await self._get_user_name(defect.reporter_id),
                'assignee': await self._get_user_name(defect.assignee_id) if defect.assignee_id else '未分配',
                'created_at': defect.created_at.isoformat()
            }
            
            # 3. 发送实时通知
            for recipient_id in recipients:
                await self.notification_service.send_notification(
                    user_id=recipient_id,
                    title=f"新缺陷: {defect.defect_code}",
                    message=f"缺陷 '{defect.title}' 已创建，严重程度: {defect.severity.value}",
                    notification_type="defect_created",
                    data=notification_data
                )
            
            # 4. 发送邮件通知（如果启用）
            if await self._is_email_notification_enabled(defect, 'created'):
                await self._send_defect_email_notification(defect, recipients, 'created')
            
            # 5. 记录通知日志
            await self._log_notification(defect.id, 'created', recipients)
            
            logger.info(f"缺陷创建通知发送成功: {defect.defect_code}")
            
        except Exception as e:
            logger.error(f"发送缺陷创建通知失败: {str(e)}")
    
    async def send_defect_status_change_notification(self, defect: Defect, old_status: DefectStatus, 
                                                   new_status: DefectStatus, changed_by: int):
        """发送缺陷状态变更通知"""
        try:
            # 1. 获取通知接收人
            recipients = await self._get_defect_notification_recipients(defect, 'status_changed')
            
            # 2. 构建通知内容
            notification_data = {
                'type': 'defect_status_changed',
                'defect_id': defect.id,
                'defect_code': defect.defect_code,
                'title': defect.title,
                'old_status': old_status.value,
                'new_status': new_status.value,
                'changed_by': await self._get_user_name(changed_by),
                'changed_at': datetime.utcnow().isoformat()
            }
            
            # 3. 发送实时通知
            for recipient_id in recipients:
                if recipient_id != changed_by:  # 不给操作者发通知
                    await self.notification_service.send_notification(
                        user_id=recipient_id,
                        title=f"缺陷状态变更: {defect.defect_code}",
                        message=f"缺陷 '{defect.title}' 状态从 {old_status.value} 变更为 {new_status.value}",
                        notification_type="defect_status_changed",
                        data=notification_data
                    )
            
            # 4. 发送邮件通知
            if await self._is_email_notification_enabled(defect, 'status_changed'):
                await self._send_defect_email_notification(defect, recipients, 'status_changed', {
                    'old_status': old_status.value,
                    'new_status': new_status.value,
                    'changed_by': await self._get_user_name(changed_by)
                })
            
            # 5. 记录通知日志
            await self._log_notification(defect.id, 'status_changed', recipients)
            
            logger.info(f"缺陷状态变更通知发送成功: {defect.defect_code} {old_status.value} -> {new_status.value}")
            
        except Exception as e:
            logger.error(f"发送缺陷状态变更通知失败: {str(e)}")
    
    async def send_defect_assigned_notification(self, defect: Defect, assignee_id: int, assigned_by: int):
        """发送缺陷分配通知"""
        try:
            # 1. 构建通知内容
            notification_data = {
                'type': 'defect_assigned',
                'defect_id': defect.id,
                'defect_code': defect.defect_code,
                'title': defect.title,
                'severity': defect.severity.value,
                'assigned_by': await self._get_user_name(assigned_by),
                'assigned_at': datetime.utcnow().isoformat()
            }
            
            # 2. 发送给被分配人
            await self.notification_service.send_notification(
                user_id=assignee_id,
                title=f"缺陷分配: {defect.defect_code}",
                message=f"缺陷 '{defect.title}' 已分配给您处理",
                notification_type="defect_assigned",
                data=notification_data
            )
            
            # 3. 发送邮件通知
            if await self._is_email_notification_enabled(defect, 'assigned'):
                await self._send_defect_email_notification(defect, [assignee_id], 'assigned', {
                    'assigned_by': await self._get_user_name(assigned_by)
                })
            
            # 4. 记录通知日志
            await self._log_notification(defect.id, 'assigned', [assignee_id])
            
            logger.info(f"缺陷分配通知发送成功: {defect.defect_code} -> {await self._get_user_name(assignee_id)}")
            
        except Exception as e:
            logger.error(f"发送缺陷分配通知失败: {str(e)}")
    
    async def send_defect_comment_notification(self, defect: Defect, comment: DefectComment, commenter_id: int):
        """发送缺陷评论通知"""
        try:
            # 1. 获取通知接收人（排除评论者）
            recipients = await self._get_defect_notification_recipients(defect, 'commented')
            recipients = [r for r in recipients if r != commenter_id]
            
            # 2. 构建通知内容
            notification_data = {
                'type': 'defect_commented',
                'defect_id': defect.id,
                'defect_code': defect.defect_code,
                'title': defect.title,
                'comment_id': comment.id,
                'commenter': await self._get_user_name(commenter_id),
                'comment_preview': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                'commented_at': comment.created_at.isoformat()
            }
            
            # 3. 发送实时通知
            for recipient_id in recipients:
                await self.notification_service.send_notification(
                    user_id=recipient_id,
                    title=f"缺陷新评论: {defect.defect_code}",
                    message=f"{await self._get_user_name(commenter_id)} 在缺陷 '{defect.title}' 中添加了评论",
                    notification_type="defect_commented",
                    data=notification_data
                )
            
            # 4. 发送邮件通知
            if await self._is_email_notification_enabled(defect, 'commented'):
                await self._send_defect_email_notification(defect, recipients, 'commented', {
                    'commenter': await self._get_user_name(commenter_id),
                    'comment': comment.content
                })
            
            # 5. 记录通知日志
            await self._log_notification(defect.id, 'commented', recipients)
            
            logger.info(f"缺陷评论通知发送成功: {defect.defect_code}")
            
        except Exception as e:
            logger.error(f"发送缺陷评论通知失败: {str(e)}")
    
    async def send_defect_sla_warning(self, defect: Defect, warning_type: str):
        """发送缺陷SLA预警通知"""
        try:
            # 1. 获取通知接收人
            recipients = await self._get_defect_notification_recipients(defect, 'sla_warning')
            
            # 2. 构建通知内容
            warning_messages = {
                'approaching_deadline': '即将超时',
                'overdue': '已超时',
                'critical_overdue': '严重超时'
            }
            
            warning_message = warning_messages.get(warning_type, '时间预警')
            
            notification_data = {
                'type': 'defect_sla_warning',
                'defect_id': defect.id,
                'defect_code': defect.defect_code,
                'title': defect.title,
                'severity': defect.severity.value,
                'warning_type': warning_type,
                'assignee': await self._get_user_name(defect.assignee_id) if defect.assignee_id else '未分配',
                'created_at': defect.created_at.isoformat()
            }
            
            # 3. 发送实时通知
            for recipient_id in recipients:
                await self.notification_service.send_notification(
                    user_id=recipient_id,
                    title=f"缺陷SLA预警: {defect.defect_code}",
                    message=f"缺陷 '{defect.title}' {warning_message}，请及时处理",
                    notification_type="defect_sla_warning",
                    data=notification_data,
                    priority="high" if warning_type in ['overdue', 'critical_overdue'] else "normal"
                )
            
            # 4. 发送邮件通知
            if await self._is_email_notification_enabled(defect, 'sla_warning'):
                await self._send_defect_email_notification(defect, recipients, 'sla_warning', {
                    'warning_type': warning_type,
                    'warning_message': warning_message
                })
            
            # 5. 记录通知日志
            await self._log_notification(defect.id, f'sla_warning_{warning_type}', recipients)
            
            logger.info(f"缺陷SLA预警通知发送成功: {defect.defect_code} - {warning_type}")
            
        except Exception as e:
            logger.error(f"发送缺陷SLA预警通知失败: {str(e)}")
    
    async def add_defect_comment(self, defect_id: int, comment_request: DefectCommentRequest, 
                               user_id: int) -> DefectComment:
        """添加缺陷评论"""
        try:
            # 1. 验证缺陷存在
            defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
            if not defect:
                raise NotFoundError("缺陷不存在")
            
            # 2. 验证评论权限
            if not await self._has_comment_permission(user_id, defect):
                raise PermissionError("没有评论权限")
            
            # 3. 创建评论
            from ..models.defect_comment import DefectComment as DefectCommentModel
            comment = DefectCommentModel(
                defect_id=defect_id,
                user_id=user_id,
                content=comment_request.content,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(comment)
            self.db.commit()
            self.db.refresh(comment)
            
            # 4. 构建响应对象
            user = self.db.query(User).filter(User.id == user_id).first()
            comment_response = DefectComment(
                id=comment.id,
                defect_id=comment.defect_id,
                user_id=comment.user_id,
                user_name=user.username if user else "未知用户",
                content=comment.content,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            )
            
            # 5. 发送评论通知
            await self.send_defect_comment_notification(defect, comment_response, user_id)
            
            # 6. 更新缺陷活动时间
            defect.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"缺陷评论添加成功: {defect.defect_code}")
            return comment_response
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"添加缺陷评论失败: {str(e)}")
            raise
    
    async def get_defect_comments(self, defect_id: int, user_id: int) -> List[DefectComment]:
        """获取缺陷评论列表"""
        try:
            # 1. 验证缺陷存在
            defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
            if not defect:
                raise NotFoundError("缺陷不存在")
            
            # 2. 验证查看权限
            if not await self._has_view_permission(user_id, defect):
                raise PermissionError("没有查看权限")
            
            # 3. 获取评论列表
            from ..models.defect_comment import DefectComment as DefectCommentModel
            comments = self.db.query(DefectCommentModel).filter(
                DefectCommentModel.defect_id == defect_id
            ).order_by(DefectCommentModel.created_at).all()
            
            # 4. 构建响应列表
            comment_responses = []
            for comment in comments:
                user = self.db.query(User).filter(User.id == comment.user_id).first()
                comment_responses.append(DefectComment(
                    id=comment.id,
                    defect_id=comment.defect_id,
                    user_id=comment.user_id,
                    user_name=user.username if user else "未知用户",
                    content=comment.content,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at
                ))
            
            return comment_responses
            
        except Exception as e:
            logger.error(f"获取缺陷评论失败: {str(e)}")
            raise
    
    async def monitor_defect_sla(self):
        """监控缺陷SLA"""
        try:
            # 1. 获取需要监控的缺陷
            active_defects = self.db.query(Defect).filter(
                Defect.status.in_([DefectStatus.NEW, DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS])
            ).all()
            
            now = datetime.utcnow()
            
            for defect in active_defects:
                # 2. 计算缺陷年龄
                defect_age = now - defect.created_at
                
                # 3. 根据严重程度确定SLA时间
                sla_hours = self._get_sla_hours(defect.severity)
                sla_deadline = defect.created_at + timedelta(hours=sla_hours)
                
                # 4. 检查SLA状态
                if now > sla_deadline:
                    # 已超时
                    hours_overdue = (now - sla_deadline).total_seconds() / 3600
                    if hours_overdue > 24:  # 超时超过24小时
                        await self.send_defect_sla_warning(defect, 'critical_overdue')
                    else:
                        await self.send_defect_sla_warning(defect, 'overdue')
                elif (sla_deadline - now).total_seconds() / 3600 <= 2:  # 2小时内到期
                    await self.send_defect_sla_warning(defect, 'approaching_deadline')
            
            logger.info(f"缺陷SLA监控完成，检查了{len(active_defects)}个活跃缺陷")
            
        except Exception as e:
            logger.error(f"缺陷SLA监控失败: {str(e)}")
    
    async def get_defect_processing_efficiency_stats(self, project_id: Optional[int] = None,
                                                   time_range: str = "30d") -> Dict[str, Any]:
        """获取缺陷处理效率统计"""
        try:
            # 1. 解析时间范围
            end_date = datetime.utcnow()
            if time_range == "7d":
                start_date = end_date - timedelta(days=7)
            elif time_range == "30d":
                start_date = end_date - timedelta(days=30)
            elif time_range == "90d":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # 2. 获取缺陷数据
            query = self.db.query(Defect).filter(
                Defect.created_at >= start_date,
                Defect.created_at <= end_date
            )
            
            if project_id:
                from ..models.test_case import TestCase
                query = query.join(TestCase, Defect.test_case_id == TestCase.id).filter(
                    TestCase.project_id == project_id
                )
            
            defects = query.all()
            
            # 3. 计算效率指标
            stats = {
                'total_defects': len(defects),
                'resolved_defects': 0,
                'avg_resolution_time': 0,
                'sla_compliance_rate': 0,
                'first_response_time': 0,
                'resolution_rate_by_severity': {},
                'processing_efficiency_by_assignee': {},
                'sla_violations': 0
            }
            
            resolution_times = []
            first_response_times = []
            sla_violations = 0
            
            for defect in defects:
                # 解决时间统计
                if defect.resolved_at and defect.created_at:
                    resolution_time = (defect.resolved_at - defect.created_at).total_seconds() / 3600
                    resolution_times.append(resolution_time)
                    stats['resolved_defects'] += 1
                    
                    # SLA合规性检查
                    sla_hours = self._get_sla_hours(defect.severity)
                    if resolution_time > sla_hours:
                        sla_violations += 1
                
                # 首次响应时间（分配时间）
                if defect.assigned_at and defect.created_at:
                    first_response_time = (defect.assigned_at - defect.created_at).total_seconds() / 3600
                    first_response_times.append(first_response_time)
            
            # 4. 计算平均值
            if resolution_times:
                stats['avg_resolution_time'] = sum(resolution_times) / len(resolution_times)
            
            if first_response_times:
                stats['first_response_time'] = sum(first_response_times) / len(first_response_times)
            
            if stats['resolved_defects'] > 0:
                stats['sla_compliance_rate'] = (stats['resolved_defects'] - sla_violations) / stats['resolved_defects']
            
            stats['sla_violations'] = sla_violations
            
            # 5. 按严重程度统计解决率
            from collections import defaultdict
            severity_stats = defaultdict(lambda: {'total': 0, 'resolved': 0})
            
            for defect in defects:
                severity_stats[defect.severity.value]['total'] += 1
                if defect.status in [DefectStatus.RESOLVED, DefectStatus.CLOSED]:
                    severity_stats[defect.severity.value]['resolved'] += 1
            
            for severity, data in severity_stats.items():
                if data['total'] > 0:
                    stats['resolution_rate_by_severity'][severity] = data['resolved'] / data['total']
            
            # 6. 按分配人统计处理效率
            assignee_stats = defaultdict(lambda: {'total': 0, 'resolved': 0, 'avg_time': 0})
            
            for defect in defects:
                if defect.assignee_id:
                    assignee_id = str(defect.assignee_id)
                    assignee_stats[assignee_id]['total'] += 1
                    
                    if defect.status in [DefectStatus.RESOLVED, DefectStatus.CLOSED]:
                        assignee_stats[assignee_id]['resolved'] += 1
                        
                        if defect.resolved_at and defect.assigned_at:
                            resolution_time = (defect.resolved_at - defect.assigned_at).total_seconds() / 3600
                            assignee_stats[assignee_id]['avg_time'] += resolution_time
            
            for assignee_id, data in assignee_stats.items():
                if data['total'] > 0:
                    efficiency = data['resolved'] / data['total']
                    avg_time = data['avg_time'] / data['resolved'] if data['resolved'] > 0 else 0
                    stats['processing_efficiency_by_assignee'][assignee_id] = {
                        'efficiency': efficiency,
                        'avg_resolution_time': avg_time,
                        'total_handled': data['total']
                    }
            
            logger.info(f"缺陷处理效率统计完成: 项目{project_id}, 时间范围{time_range}")
            return stats
            
        except Exception as e:
            logger.error(f"获取缺陷处理效率统计失败: {str(e)}")
            raise ValidationError(f"获取缺陷处理效率统计失败: {str(e)}")
    
    # 私有方法实现
    async def _get_defect_notification_recipients(self, defect: Defect, event_type: str) -> List[int]:
        """获取缺陷通知接收人"""
        recipients = set()
        
        # 报告人
        if defect.reporter_id:
            recipients.add(defect.reporter_id)
        
        # 分配人
        if defect.assignee_id:
            recipients.add(defect.assignee_id)
        
        # 项目相关人员（通过测试用例获取项目信息）
        if defect.test_case and defect.test_case.project_id:
            project_members = await self._get_project_members(defect.test_case.project_id)
            recipients.update(project_members)
        
        # 根据事件类型添加特定接收人
        if event_type == 'sla_warning':
            # SLA预警需要通知项目经理
            project_managers = await self._get_project_managers(defect.test_case.project_id if defect.test_case else None)
            recipients.update(project_managers)
        
        return list(recipients)
    
    async def _get_user_name(self, user_id: Optional[int]) -> str:
        """获取用户名"""
        if not user_id:
            return "未知用户"
        
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.username if user else "未知用户"
    
    async def _is_email_notification_enabled(self, defect: Defect, event_type: str) -> bool:
        """检查是否启用邮件通知"""
        # 简化实现，实际应该从配置中读取
        return True
    
    async def _send_defect_email_notification(self, defect: Defect, recipients: List[int], 
                                            event_type: str, extra_data: Optional[Dict] = None):
        """发送缺陷邮件通知"""
        try:
            # 获取收件人邮箱
            recipient_emails = []
            for recipient_id in recipients:
                user = self.db.query(User).filter(User.id == recipient_id).first()
                if user and user.email:
                    recipient_emails.append(user.email)
            
            if not recipient_emails:
                return
            
            # 构建邮件内容
            subject, body = self._build_email_content(defect, event_type, extra_data)
            
            # 发送邮件
            await self.email_service.send_email(
                to=recipient_emails,
                subject=subject,
                body=body,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"发送缺陷邮件通知失败: {str(e)}")
    
    def _build_email_content(self, defect: Defect, event_type: str, 
                           extra_data: Optional[Dict] = None) -> tuple[str, str]:
        """构建邮件内容"""
        extra_data = extra_data or {}
        
        if event_type == 'created':
            subject = f"新缺陷通知: {defect.defect_code}"
            body = f"""
            <h3>新缺陷通知</h3>
            <p><strong>缺陷编号:</strong> {defect.defect_code}</p>
            <p><strong>标题:</strong> {defect.title}</p>
            <p><strong>严重程度:</strong> {defect.severity.value}</p>
            <p><strong>类型:</strong> {defect.defect_type.value}</p>
            <p><strong>报告人:</strong> {extra_data.get('reporter', '未知')}</p>
            <p><strong>分配人:</strong> {extra_data.get('assignee', '未分配')}</p>
            <p><strong>创建时间:</strong> {defect.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>描述:</strong></p>
            <p>{defect.description}</p>
            """
        elif event_type == 'status_changed':
            subject = f"缺陷状态变更: {defect.defect_code}"
            body = f"""
            <h3>缺陷状态变更通知</h3>
            <p><strong>缺陷编号:</strong> {defect.defect_code}</p>
            <p><strong>标题:</strong> {defect.title}</p>
            <p><strong>状态变更:</strong> {extra_data.get('old_status')} → {extra_data.get('new_status')}</p>
            <p><strong>操作人:</strong> {extra_data.get('changed_by', '未知')}</p>
            <p><strong>变更时间:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
            """
        elif event_type == 'assigned':
            subject = f"缺陷分配通知: {defect.defect_code}"
            body = f"""
            <h3>缺陷分配通知</h3>
            <p><strong>缺陷编号:</strong> {defect.defect_code}</p>
            <p><strong>标题:</strong> {defect.title}</p>
            <p><strong>严重程度:</strong> {defect.severity.value}</p>
            <p><strong>分配人:</strong> {extra_data.get('assigned_by', '未知')}</p>
            <p><strong>分配时间:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>描述:</strong></p>
            <p>{defect.description}</p>
            """
        elif event_type == 'commented':
            subject = f"缺陷新评论: {defect.defect_code}"
            body = f"""
            <h3>缺陷新评论通知</h3>
            <p><strong>缺陷编号:</strong> {defect.defect_code}</p>
            <p><strong>标题:</strong> {defect.title}</p>
            <p><strong>评论人:</strong> {extra_data.get('commenter', '未知')}</p>
            <p><strong>评论时间:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>评论内容:</strong></p>
            <p>{extra_data.get('comment', '')}</p>
            """
        elif event_type == 'sla_warning':
            subject = f"缺陷SLA预警: {defect.defect_code}"
            body = f"""
            <h3>缺陷SLA预警通知</h3>
            <p><strong>缺陷编号:</strong> {defect.defect_code}</p>
            <p><strong>标题:</strong> {defect.title}</p>
            <p><strong>严重程度:</strong> {defect.severity.value}</p>
            <p><strong>预警类型:</strong> {extra_data.get('warning_message', '时间预警')}</p>
            <p><strong>创建时间:</strong> {defect.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>当前分配人:</strong> {extra_data.get('assignee', '未分配')}</p>
            <p style="color: red;"><strong>请及时处理！</strong></p>
            """
        else:
            subject = f"缺陷通知: {defect.defect_code}"
            body = f"缺陷 {defect.defect_code} 有新的更新"
        
        return subject, body
    
    async def _log_notification(self, defect_id: int, event_type: str, recipients: List[int]):
        """记录通知日志"""
        try:
            log_data = {
                'defect_id': defect_id,
                'event_type': event_type,
                'recipients': recipients,
                'sent_at': datetime.utcnow().isoformat()
            }
            
            # 存储到Redis（可选）
            cache_key = f"defect_notification_log:{defect_id}:{event_type}:{datetime.utcnow().timestamp()}"
            await self.redis.setex(cache_key, 86400, str(log_data))  # 保存24小时
            
        except Exception as e:
            logger.warning(f"记录通知日志失败: {str(e)}")
    
    async def _has_comment_permission(self, user_id: int, defect: Defect) -> bool:
        """检查是否有评论权限"""
        # 报告人、分配人、项目成员可以评论
        if user_id in [defect.reporter_id, defect.assignee_id]:
            return True
        
        # 检查是否是项目成员
        if defect.test_case and defect.test_case.project_id:
            project_members = await self._get_project_members(defect.test_case.project_id)
            if user_id in project_members:
                return True
        
        return False
    
    async def _has_view_permission(self, user_id: int, defect: Defect) -> bool:
        """检查是否有查看权限"""
        # 简化实现，所有用户都可以查看
        return True
    
    async def _get_project_members(self, project_id: Optional[int]) -> List[int]:
        """获取项目成员"""
        if not project_id:
            return []
        
        # 简化实现，实际应该从项目成员表中获取
        # 这里返回空列表，实际应用中需要实现项目成员管理
        return []
    
    async def _get_project_managers(self, project_id: Optional[int]) -> List[int]:
        """获取项目经理"""
        if not project_id:
            return []
        
        # 简化实现，实际应该从项目管理表中获取
        return []
    
    def _get_sla_hours(self, severity) -> int:
        """根据严重程度获取SLA时间（小时）"""
        sla_mapping = {
            'CRITICAL': 4,   # 4小时
            'HIGH': 24,      # 24小时
            'MEDIUM': 72,    # 72小时
            'LOW': 168       # 168小时（7天）
        }
        return sla_mapping.get(severity.value, 72)