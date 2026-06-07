"""
测试报告分发和订阅服务

本模块实现了测试报告的分发和订阅功能，包括：
- 报告的自动分发和邮件通知
- 报告订阅和个性化推送
- 报告的版本管理和历史对比
- 报告访问权限控制
"""
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..models.test_report import TestReportRecord
from ..models.test_report_subscription import (
    TestReportSubscription, TestReportDistribution, TestReportVersion, TestReportAccessLog,
    SubscriptionType, DeliveryChannel, SubscriptionStatus, DistributionStatus
)
from ..models.user import User
from ..schemas.test_report_subscription import (
    TestReportSubscriptionRequest, TestReportSubscriptionResponse, TestReportSubscriptionUpdate,
    TestReportDistributionRequest, TestReportDistributionResponse,
    TestReportVersionRequest, TestReportVersionResponse,
    DistributionStatistics, SubscriptionStatistics
)
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..utils.redis_client import RedisClient
from .email_service import EmailService
from .webhook_service import WebhookService

logger = logging.getLogger(__name__)

class TestReportDistributionService:
    """测试报告分发和订阅服务"""
    
    def __init__(self, db: Session, redis_client: RedisClient, 
                 email_service: EmailService, webhook_service: WebhookService):
        self.db = db
        self.redis = redis_client
        self.email_service = email_service
        self.webhook_service = webhook_service
        self.distribution_queue = []
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 这里可以启动定时任务处理分发队列
        pass
    
    # 订阅管理
    async def create_subscription(self, subscription_request: TestReportSubscriptionRequest, 
                                user_id: int) -> TestReportSubscriptionResponse:
        """创建报告订阅"""
        try:
            # 1. 验证订阅请求
            await self._validate_subscription_request(subscription_request)
            
            # 2. 创建订阅记录
            subscription = TestReportSubscription(
                name=subscription_request.name,
                description=subscription_request.description,
                subscription_type=subscription_request.subscription_type,
                delivery_channels=[channel.value for channel in subscription_request.delivery_channels],
                project_ids=subscription_request.project_ids,
                report_types=subscription_request.report_types,
                template_ids=subscription_request.template_ids,
                schedule_enabled=subscription_request.schedule_enabled,
                schedule_expression=subscription_request.schedule_expression,
                timezone=subscription_request.timezone,
                delivery_config=subscription_request.delivery_config,
                email_recipients=subscription_request.email_recipients,
                webhook_url=subscription_request.webhook_url,
                include_attachments=subscription_request.include_attachments,
                max_file_size=subscription_request.max_file_size,
                preferred_formats=subscription_request.preferred_formats,
                user_id=user_id,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            
            # 3. 计算下次分发时间
            if subscription.schedule_enabled:
                subscription.next_delivery_time = await self._calculate_next_delivery_time(
                    subscription.schedule_expression, subscription.timezone
                )
                self.db.commit()
            
            # 4. 清除相关缓存
            await self._clear_subscription_cache(user_id)
            
            logger.info(f"报告订阅创建成功: {subscription.name}")
            return TestReportSubscriptionResponse.from_orm(subscription)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建报告订阅失败: {str(e)}")
            raise ValidationError(f"创建报告订阅失败: {str(e)}")
    
    async def update_subscription(self, subscription_id: int, 
                                subscription_update: TestReportSubscriptionUpdate,
                                user_id: int) -> TestReportSubscriptionResponse:
        """更新报告订阅"""
        try:
            # 1. 获取订阅记录
            subscription = self.db.query(TestReportSubscription).filter(
                TestReportSubscription.id == subscription_id
            ).first()
            
            if not subscription:
                raise NotFoundError("订阅不存在")
            
            # 2. 验证权限
            if subscription.user_id != user_id and subscription.created_by != user_id:
                raise PermissionError("没有权限修改此订阅")
            
            # 3. 更新订阅信息
            update_data = subscription_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(subscription, field):
                    if field == 'delivery_channels' and value:
                        setattr(subscription, field, [channel.value for channel in value])
                    else:
                        setattr(subscription, field, value)
            
            subscription.updated_at = datetime.utcnow()
            
            # 4. 重新计算下次分发时间
            if subscription.schedule_enabled and subscription.schedule_expression:
                subscription.next_delivery_time = await self._calculate_next_delivery_time(
                    subscription.schedule_expression, subscription.timezone
                )
            
            self.db.commit()
            self.db.refresh(subscription)
            
            # 5. 清除相关缓存
            await self._clear_subscription_cache(user_id)
            
            logger.info(f"报告订阅更新成功: {subscription.name}")
            return TestReportSubscriptionResponse.from_orm(subscription)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新报告订阅失败: {str(e)}")
            raise
    
    async def delete_subscription(self, subscription_id: int, user_id: int):
        """删除报告订阅"""
        try:
            # 1. 获取订阅记录
            subscription = self.db.query(TestReportSubscription).filter(
                TestReportSubscription.id == subscription_id
            ).first()
            
            if not subscription:
                raise NotFoundError("订阅不存在")
            
            # 2. 验证权限
            if subscription.user_id != user_id and subscription.created_by != user_id:
                raise PermissionError("没有权限删除此订阅")
            
            # 3. 删除相关分发记录
            self.db.query(TestReportDistribution).filter(
                TestReportDistribution.subscription_id == subscription_id
            ).delete()
            
            # 4. 删除订阅记录
            self.db.delete(subscription)
            self.db.commit()
            
            # 5. 清除相关缓存
            await self._clear_subscription_cache(user_id)
            
            logger.info(f"报告订阅删除成功: {subscription.name}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除报告订阅失败: {str(e)}")
            raise
    
    async def get_user_subscriptions(self, user_id: int, 
                                   page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取用户订阅列表"""
        try:
            # 1. 构建查询
            query = self.db.query(TestReportSubscription).filter(
                TestReportSubscription.user_id == user_id
            )
            
            # 2. 分页查询
            total = query.count()
            subscriptions = query.offset((page - 1) * page_size).limit(page_size).all()
            
            # 3. 构建响应
            subscription_responses = [
                TestReportSubscriptionResponse.from_orm(sub) for sub in subscriptions
            ]
            
            return {
                'subscriptions': subscription_responses,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"获取用户订阅列表失败: {str(e)}")
            raise ValidationError(f"获取用户订阅列表失败: {str(e)}")
    
    # 报告分发
    async def distribute_report(self, distribution_request: TestReportDistributionRequest,
                              user_id: int) -> List[TestReportDistributionResponse]:
        """分发报告"""
        try:
            # 1. 验证报告存在
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == distribution_request.report_id
            ).first()
            
            if not report:
                raise NotFoundError("报告不存在")
            
            # 2. 验证权限
            if not await self._has_distribution_permission(user_id, report):
                raise PermissionError("没有分发权限")
            
            # 3. 创建分发记录
            distributions = []
            for recipient in distribution_request.recipients:
                distribution = TestReportDistribution(
                    subscription_id=distribution_request.subscription_id,
                    report_id=distribution_request.report_id,
                    delivery_channel=distribution_request.delivery_channel,
                    recipient=recipient,
                    subject=distribution_request.subject or f"测试报告: {report.name}",
                    content=distribution_request.content,
                    scheduled_at=distribution_request.scheduled_at or datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                
                self.db.add(distribution)
                distributions.append(distribution)
            
            self.db.commit()
            
            # 4. 处理分发
            distribution_responses = []
            for distribution in distributions:
                self.db.refresh(distribution)
                
                # 添加到分发队列
                self.distribution_queue.append(distribution.id)
                
                # 如果是立即分发，直接处理
                if not distribution_request.scheduled_at or distribution_request.scheduled_at <= datetime.utcnow():
                    await self._process_distribution(distribution.id)
                
                distribution_responses.append(TestReportDistributionResponse.from_orm(distribution))
            
            logger.info(f"报告分发任务创建成功: {len(distributions)}个分发任务")
            return distribution_responses
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"分发报告失败: {str(e)}")
            raise
    
    async def auto_distribute_report(self, report_id: int):
        """自动分发报告（基于订阅）"""
        try:
            # 1. 获取报告信息
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == report_id
            ).first()
            
            if not report:
                logger.warning(f"报告不存在: {report_id}")
                return
            
            # 2. 查找匹配的订阅
            matching_subscriptions = await self._find_matching_subscriptions(report)
            
            # 3. 为每个匹配的订阅创建分发任务
            for subscription in matching_subscriptions:
                try:
                    await self._create_subscription_distribution(subscription, report)
                except Exception as e:
                    logger.error(f"为订阅{subscription.id}创建分发任务失败: {str(e)}")
            
            logger.info(f"报告自动分发完成: {report.name}, 匹配订阅数: {len(matching_subscriptions)}")
            
        except Exception as e:
            logger.error(f"自动分发报告失败: {str(e)}")
    
    async def process_scheduled_distributions(self):
        """处理定时分发任务"""
        try:
            # 1. 获取需要处理的分发任务
            now = datetime.utcnow()
            pending_distributions = self.db.query(TestReportDistribution).filter(
                TestReportDistribution.status == "pending",
                TestReportDistribution.scheduled_at <= now
            ).all()
            
            # 2. 处理每个分发任务
            for distribution in pending_distributions:
                try:
                    await self._process_distribution(distribution.id)
                except Exception as e:
                    logger.error(f"处理分发任务{distribution.id}失败: {str(e)}")
            
            logger.info(f"定时分发任务处理完成: {len(pending_distributions)}个任务")
            
        except Exception as e:
            logger.error(f"处理定时分发任务失败: {str(e)}")
    
    # 版本管理
    async def create_report_version(self, version_request: TestReportVersionRequest,
                                  user_id: int) -> TestReportVersionResponse:
        """创建报告版本"""
        try:
            # 1. 验证报告存在
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == version_request.report_id
            ).first()
            
            if not report:
                raise NotFoundError("报告不存在")
            
            # 2. 验证权限
            if not await self._has_version_management_permission(user_id, report):
                raise PermissionError("没有版本管理权限")
            
            # 3. 检查版本号是否已存在
            existing_version = self.db.query(TestReportVersion).filter(
                TestReportVersion.report_id == version_request.report_id,
                TestReportVersion.version_number == version_request.version_number
            ).first()
            
            if existing_version:
                raise ValidationError("版本号已存在")
            
            # 4. 创建版本记录
            version = TestReportVersion(
                report_id=version_request.report_id,
                version_number=version_request.version_number,
                version_name=version_request.version_name,
                description=version_request.description,
                change_log=version_request.change_log,
                file_paths=report.file_paths,
                file_size=report.file_size,
                access_level=version_request.access_level,
                allowed_users=version_request.allowed_users,
                allowed_roles=version_request.allowed_roles,
                is_published=version_request.is_published,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            # 5. 计算文件哈希
            if report.file_paths:
                version.file_hash = await self._calculate_file_hash(report.file_paths)
            
            self.db.add(version)
            
            # 6. 如果是发布版本，更新当前版本标记
            if version_request.is_published:
                # 取消其他版本的当前标记
                self.db.query(TestReportVersion).filter(
                    TestReportVersion.report_id == version_request.report_id,
                    TestReportVersion.is_current == True
                ).update({'is_current': False})
                
                version.is_current = True
            
            self.db.commit()
            self.db.refresh(version)
            
            logger.info(f"报告版本创建成功: {report.name} v{version.version_number}")
            return TestReportVersionResponse.from_orm(version)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建报告版本失败: {str(e)}")
            raise
    
    async def get_report_versions(self, report_id: int, user_id: int) -> List[TestReportVersionResponse]:
        """获取报告版本列表"""
        try:
            # 1. 验证报告存在
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == report_id
            ).first()
            
            if not report:
                raise NotFoundError("报告不存在")
            
            # 2. 获取版本列表
            versions = self.db.query(TestReportVersion).filter(
                TestReportVersion.report_id == report_id
            ).order_by(desc(TestReportVersion.created_at)).all()
            
            # 3. 过滤用户有权限访问的版本
            accessible_versions = []
            for version in versions:
                if await self._has_version_access_permission(user_id, version):
                    accessible_versions.append(TestReportVersionResponse.from_orm(version))
            
            return accessible_versions
            
        except Exception as e:
            logger.error(f"获取报告版本列表失败: {str(e)}")
            raise
    
    async def compare_report_versions(self, version1_id: int, version2_id: int, 
                                    user_id: int) -> Dict[str, Any]:
        """比较报告版本"""
        try:
            # 1. 获取版本信息
            version1 = self.db.query(TestReportVersion).filter(
                TestReportVersion.id == version1_id
            ).first()
            version2 = self.db.query(TestReportVersion).filter(
                TestReportVersion.id == version2_id
            ).first()
            
            if not version1 or not version2:
                raise NotFoundError("版本不存在")
            
            # 2. 验证权限
            if not await self._has_version_access_permission(user_id, version1) or \
               not await self._has_version_access_permission(user_id, version2):
                raise PermissionError("没有访问权限")
            
            # 3. 比较版本
            comparison = {
                'version1': TestReportVersionResponse.from_orm(version1),
                'version2': TestReportVersionResponse.from_orm(version2),
                'differences': {
                    'file_size_diff': (version2.file_size or 0) - (version1.file_size or 0),
                    'file_hash_changed': version1.file_hash != version2.file_hash,
                    'access_level_changed': version1.access_level != version2.access_level,
                    'time_diff': (version2.created_at - version1.created_at).total_seconds()
                },
                'change_summary': {
                    'version1_date': version1.created_at,
                    'version2_date': version2.created_at,
                    'version1_creator': await self._get_user_name(version1.created_by),
                    'version2_creator': await self._get_user_name(version2.created_by)
                }
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"比较报告版本失败: {str(e)}")
            raise
    
    # 访问控制
    async def log_report_access(self, report_id: int, version_id: Optional[int],
                              user_id: Optional[int], access_type: str,
                              access_method: Optional[str] = None,
                              ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None) -> bool:
        """记录报告访问日志"""
        try:
            # 1. 创建访问日志
            access_log = TestReportAccessLog(
                report_id=report_id,
                version_id=version_id,
                user_id=user_id,
                access_type=access_type,
                access_method=access_method,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                accessed_at=datetime.utcnow()
            )
            
            self.db.add(access_log)
            self.db.commit()
            
            # 2. 更新报告访问统计
            if access_type == "view":
                await self._update_report_view_count(report_id)
            elif access_type == "download":
                await self._update_report_download_count(report_id)
            
            return True
            
        except Exception as e:
            logger.error(f"记录报告访问日志失败: {str(e)}")
            return False
    
    async def check_report_access_permission(self, report_id: int, version_id: Optional[int],
                                           user_id: Optional[int]) -> bool:
        """检查报告访问权限"""
        try:
            # 1. 获取报告信息
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == report_id
            ).first()
            
            if not report:
                return False
            
            # 2. 如果指定了版本，检查版本权限
            if version_id:
                version = self.db.query(TestReportVersion).filter(
                    TestReportVersion.id == version_id
                ).first()
                
                if not version:
                    return False
                
                return await self._has_version_access_permission(user_id, version)
            
            # 3. 检查报告基本权限
            return await self._has_report_access_permission(user_id, report)
            
        except Exception as e:
            logger.error(f"检查报告访问权限失败: {str(e)}")
            return False
    
    # 统计分析
    async def get_distribution_statistics(self, project_id: Optional[int] = None,
                                        time_range: str = "30d") -> DistributionStatistics:
        """获取分发统计"""
        try:
            # 1. 解析时间范围
            start_date, end_date = self._parse_time_range(time_range)
            
            # 2. 构建查询
            query = self.db.query(TestReportDistribution).filter(
                TestReportDistribution.created_at >= start_date,
                TestReportDistribution.created_at <= end_date
            )
            
            if project_id:
                query = query.join(TestReportRecord).filter(
                    TestReportRecord.project_id == project_id
                )
            
            distributions = query.all()
            
            # 3. 计算统计指标
            stats = DistributionStatistics()
            stats.total_distributions = len(distributions)
            stats.successful_distributions = len([d for d in distributions if d.status == "delivered"])
            stats.failed_distributions = len([d for d in distributions if d.status == "failed"])
            
            if stats.total_distributions > 0:
                stats.success_rate = stats.successful_distributions / stats.total_distributions
            
            # 4. 按渠道统计
            from collections import defaultdict
            channel_stats = defaultdict(lambda: {'total': 0, 'successful': 0})
            
            for distribution in distributions:
                channel = distribution.delivery_channel
                channel_stats[channel]['total'] += 1
                if distribution.status == "delivered":
                    channel_stats[channel]['successful'] += 1
            
            for channel, data in channel_stats.items():
                stats.distributions_by_channel[channel] = data['total']
                if data['total'] > 0:
                    stats.success_rate_by_channel[channel] = data['successful'] / data['total']
            
            # 5. 按日期统计
            daily_stats = defaultdict(lambda: {'total': 0, 'successful': 0})
            for distribution in distributions:
                date_key = distribution.created_at.date().isoformat()
                daily_stats[date_key]['total'] += 1
                if distribution.status == "delivered":
                    daily_stats[date_key]['successful'] += 1
            
            stats.daily_distributions = [
                {
                    'date': date,
                    'total': data['total'],
                    'successful': data['successful'],
                    'success_rate': data['successful'] / data['total'] if data['total'] > 0 else 0
                }
                for date, data in sorted(daily_stats.items())
            ]
            
            stats.start_date = start_date
            stats.end_date = end_date
            
            return stats
            
        except Exception as e:
            logger.error(f"获取分发统计失败: {str(e)}")
            raise ValidationError(f"获取分发统计失败: {str(e)}")
    
    async def get_subscription_statistics(self, user_id: Optional[int] = None) -> SubscriptionStatistics:
        """获取订阅统计"""
        try:
            # 1. 构建查询
            query = self.db.query(TestReportSubscription)
            if user_id:
                query = query.filter(TestReportSubscription.user_id == user_id)
            
            subscriptions = query.all()
            
            # 2. 计算统计指标
            stats = SubscriptionStatistics()
            stats.total_subscriptions = len(subscriptions)
            stats.active_subscriptions = len([s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE])
            stats.paused_subscriptions = len([s for s in subscriptions if s.status == SubscriptionStatus.PAUSED])
            stats.cancelled_subscriptions = len([s for s in subscriptions if s.status == SubscriptionStatus.CANCELLED])
            
            # 3. 按类型统计
            from collections import defaultdict
            type_stats = defaultdict(int)
            channel_stats = defaultdict(int)
            
            for subscription in subscriptions:
                type_stats[subscription.subscription_type.value] += 1
                for channel in subscription.delivery_channels:
                    channel_stats[channel] += 1
            
            stats.subscriptions_by_type = dict(type_stats)
            stats.subscriptions_by_channel = dict(channel_stats)
            
            # 4. 最活跃订阅
            active_subscriptions = sorted(
                [s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE],
                key=lambda x: x.delivery_count,
                reverse=True
            )[:10]
            
            stats.most_active_subscriptions = [
                {
                    'id': s.id,
                    'name': s.name,
                    'delivery_count': s.delivery_count,
                    'last_delivery_time': s.last_delivery_time.isoformat() if s.last_delivery_time else None
                }
                for s in active_subscriptions
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"获取订阅统计失败: {str(e)}")
            raise ValidationError(f"获取订阅统计失败: {str(e)}")
    
    # 私有方法实现
    async def _validate_subscription_request(self, request: TestReportSubscriptionRequest):
        """验证订阅请求"""
        if DeliveryChannel.EMAIL in request.delivery_channels and not request.email_recipients:
            raise ValidationError("邮件分发渠道需要指定接收人")
        
        if DeliveryChannel.WEBHOOK in request.delivery_channels and not request.webhook_url:
            raise ValidationError("Webhook分发渠道需要指定URL")
        
        if request.schedule_enabled and not request.schedule_expression:
            raise ValidationError("启用定期发送需要指定调度表达式")
    
    async def _calculate_next_delivery_time(self, schedule_expression: str, timezone: str) -> datetime:
        """计算下次分发时间"""
        # 简化实现，实际应该使用cron表达式解析
        # 这里假设schedule_expression是简单的格式，如"daily", "weekly", "monthly"
        now = datetime.utcnow()
        
        if schedule_expression == "daily":
            return now + timedelta(days=1)
        elif schedule_expression == "weekly":
            return now + timedelta(weeks=1)
        elif schedule_expression == "monthly":
            return now + timedelta(days=30)
        else:
            # 默认每天
            return now + timedelta(days=1)
    
    async def _find_matching_subscriptions(self, report: TestReportRecord) -> List[TestReportSubscription]:
        """查找匹配的订阅"""
        # 1. 获取所有活跃订阅
        subscriptions = self.db.query(TestReportSubscription).filter(
            TestReportSubscription.status == SubscriptionStatus.ACTIVE,
            TestReportSubscription.subscription_type == SubscriptionType.REPORT_GENERATED
        ).all()
        
        # 2. 过滤匹配的订阅
        matching_subscriptions = []
        for subscription in subscriptions:
            # 检查项目匹配
            if subscription.project_ids and report.project_id not in subscription.project_ids:
                continue
            
            # 检查报告类型匹配
            if subscription.report_types and report.report_type not in subscription.report_types:
                continue
            
            # 检查模板匹配
            if subscription.template_ids and report.template_id not in subscription.template_ids:
                continue
            
            matching_subscriptions.append(subscription)
        
        return matching_subscriptions
    
    async def _create_subscription_distribution(self, subscription: TestReportSubscription, 
                                              report: TestReportRecord):
        """为订阅创建分发任务"""
        try:
            # 1. 为每个分发渠道创建分发任务
            for channel in subscription.delivery_channels:
                if channel == DeliveryChannel.EMAIL.value and subscription.email_recipients:
                    for recipient in subscription.email_recipients:
                        distribution = TestReportDistribution(
                            subscription_id=subscription.id,
                            report_id=report.id,
                            delivery_channel=channel,
                            recipient=recipient,
                            subject=f"测试报告: {report.name}",
                            content=f"新的测试报告已生成: {report.name}",
                            scheduled_at=datetime.utcnow(),
                            created_at=datetime.utcnow()
                        )
                        
                        self.db.add(distribution)
                
                elif channel == DeliveryChannel.WEBHOOK.value and subscription.webhook_url:
                    distribution = TestReportDistribution(
                        subscription_id=subscription.id,
                        report_id=report.id,
                        delivery_channel=channel,
                        recipient=subscription.webhook_url,
                        subject=f"测试报告: {report.name}",
                        content=f"新的测试报告已生成: {report.name}",
                        scheduled_at=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    )
                    
                    self.db.add(distribution)
            
            self.db.commit()
            
            # 2. 更新订阅统计
            subscription.delivery_count += 1
            subscription.last_delivery_time = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"为订阅{subscription.id}创建分发任务失败: {str(e)}")
            raise
    
    async def _process_distribution(self, distribution_id: int):
        """处理分发任务"""
        try:
            # 1. 获取分发任务
            distribution = self.db.query(TestReportDistribution).filter(
                TestReportDistribution.id == distribution_id
            ).first()
            
            if not distribution or distribution.status != "pending":
                return
            
            # 2. 更新状态为发送中
            distribution.status = "sending"
            distribution.sent_at = datetime.utcnow()
            self.db.commit()
            
            # 3. 根据渠道处理分发
            success = False
            error_message = None
            
            try:
                if distribution.delivery_channel == DeliveryChannel.EMAIL.value:
                    success = await self._send_email_distribution(distribution)
                elif distribution.delivery_channel == DeliveryChannel.WEBHOOK.value:
                    success = await self._send_webhook_distribution(distribution)
                elif distribution.delivery_channel == DeliveryChannel.IN_APP.value:
                    success = await self._send_in_app_distribution(distribution)
                else:
                    error_message = f"不支持的分发渠道: {distribution.delivery_channel}"
            
            except Exception as e:
                error_message = str(e)
            
            # 4. 更新分发状态
            if success:
                distribution.status = "delivered"
                distribution.delivered_at = datetime.utcnow()
            else:
                distribution.status = "failed"
                distribution.error_message = error_message
                distribution.retry_count += 1
            
            self.db.commit()
            
            logger.info(f"分发任务处理完成: {distribution_id}, 状态: {distribution.status}")
            
        except Exception as e:
            logger.error(f"处理分发任务{distribution_id}失败: {str(e)}")
            # 更新为失败状态
            try:
                distribution = self.db.query(TestReportDistribution).filter(
                    TestReportDistribution.id == distribution_id
                ).first()
                if distribution:
                    distribution.status = "failed"
                    distribution.error_message = str(e)
                    distribution.retry_count += 1
                    self.db.commit()
            except:
                pass
    
    async def _send_email_distribution(self, distribution: TestReportDistribution) -> bool:
        """发送邮件分发"""
        try:
            # 1. 获取报告信息
            report = distribution.report
            if not report:
                return False
            
            # 2. 构建邮件内容
            subject = distribution.subject or f"测试报告: {report.name}"
            
            # 3. 构建邮件正文
            body = f"""
            <h3>测试报告通知</h3>
            <p><strong>报告名称:</strong> {report.name}</p>
            <p><strong>报告类型:</strong> {report.report_type}</p>
            <p><strong>生成时间:</strong> {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>报告描述:</strong> {report.description or '无'}</p>
            
            <p>请点击以下链接查看报告详情:</p>
            <p><a href="/reports/{report.id}">查看报告</a></p>
            """
            
            if distribution.content:
                body += f"<p><strong>附加说明:</strong></p><p>{distribution.content}</p>"
            
            # 4. 添加附件（如果启用）
            attachments = []
            subscription = distribution.subscription
            if subscription and subscription.include_attachments and report.file_paths:
                for format_type, file_path in report.file_paths.items():
                    if Path(file_path).exists():
                        # 检查文件大小限制
                        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
                        if not subscription.max_file_size or file_size_mb <= subscription.max_file_size:
                            # 检查格式偏好
                            if not subscription.preferred_formats or format_type in subscription.preferred_formats:
                                attachments.append(file_path)
            
            # 5. 发送邮件
            await self.email_service.send_email(
                to=[distribution.recipient],
                subject=subject,
                body=body,
                is_html=True,
                attachments=attachments
            )
            
            return True
            
        except Exception as e:
            logger.error(f"发送邮件分发失败: {str(e)}")
            return False
    
    async def _send_webhook_distribution(self, distribution: TestReportDistribution) -> bool:
        """发送Webhook分发"""
        try:
            # 1. 构建Webhook数据
            report = distribution.report
            webhook_data = {
                'event': 'report_generated',
                'report': {
                    'id': report.id,
                    'name': report.name,
                    'type': report.report_type,
                    'created_at': report.created_at.isoformat(),
                    'file_paths': report.file_paths,
                    'view_url': f"/reports/{report.id}"
                },
                'distribution': {
                    'id': distribution.id,
                    'subscription_id': distribution.subscription_id,
                    'created_at': distribution.created_at.isoformat()
                }
            }
            
            # 2. 发送Webhook
            success = await self.webhook_service.send_webhook(
                url=distribution.recipient,
                data=webhook_data,
                headers={'Content-Type': 'application/json'}
            )
            
            return success
            
        except Exception as e:
            logger.error(f"发送Webhook分发失败: {str(e)}")
            return False
    
    async def _send_in_app_distribution(self, distribution: TestReportDistribution) -> bool:
        """发送应用内分发"""
        try:
            # 简化实现，实际应该发送到消息队列或WebSocket
            logger.info(f"应用内通知: {distribution.subject}")
            return True
            
        except Exception as e:
            logger.error(f"发送应用内分发失败: {str(e)}")
            return False
    
    async def _calculate_file_hash(self, file_paths: Dict[str, str]) -> str:
        """计算文件哈希"""
        try:
            hash_md5 = hashlib.md5()
            for file_path in file_paths.values():
                if Path(file_path).exists():
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"计算文件哈希失败: {str(e)}")
            return ""
    
    async def _has_distribution_permission(self, user_id: int, report: TestReportRecord) -> bool:
        """检查分发权限"""
        # 简化实现，实际应该检查用户角色和权限
        return report.created_by == user_id
    
    async def _has_version_management_permission(self, user_id: int, report: TestReportRecord) -> bool:
        """检查版本管理权限"""
        # 简化实现，实际应该检查用户角色和权限
        return report.created_by == user_id
    
    async def _has_version_access_permission(self, user_id: Optional[int], version: TestReportVersion) -> bool:
        """检查版本访问权限"""
        if version.access_level == "public":
            return True
        
        if not user_id:
            return False
        
        if version.access_level == "private":
            return version.created_by == user_id or (
                version.allowed_users and user_id in version.allowed_users
            )
        
        # internal级别的权限检查
        return True  # 简化实现
    
    async def _has_report_access_permission(self, user_id: Optional[int], report: TestReportRecord) -> bool:
        """检查报告访问权限"""
        # 简化实现，实际应该检查项目权限
        return True
    
    async def _update_report_view_count(self, report_id: int):
        """更新报告查看次数"""
        try:
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == report_id
            ).first()
            if report:
                report.view_count = (report.view_count or 0) + 1
                self.db.commit()
        except Exception as e:
            logger.warning(f"更新报告查看次数失败: {str(e)}")
    
    async def _update_report_download_count(self, report_id: int):
        """更新报告下载次数"""
        try:
            report = self.db.query(TestReportRecord).filter(
                TestReportRecord.id == report_id
            ).first()
            if report:
                report.download_count = (report.download_count or 0) + 1
                self.db.commit()
        except Exception as e:
            logger.warning(f"更新报告下载次数失败: {str(e)}")
    
    async def _get_user_name(self, user_id: int) -> str:
        """获取用户名"""
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.username if user else "未知用户"
    
    async def _clear_subscription_cache(self, user_id: int):
        """清除订阅缓存"""
        try:
            cache_key = f"user_subscriptions:{user_id}"
            await self.redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"清除订阅缓存失败: {str(e)}")
    
    def _parse_time_range(self, time_range: str) -> tuple[datetime, datetime]:
        """解析时间范围"""
        end_date = datetime.utcnow()
        
        if time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        return start_date, end_date