"""
仪表板事件管理服务

实现事件订阅、推送和权限控制功能
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable, Union
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.websocket_connection import EventType
from ..models.dashboard_config import RoleType
from ..models.user import User
from ..models.project import Project
from ..core.database import get_db
from ..services.permission_service import PermissionService
from ..utils.redis_client import get_redis_client
from .dashboard_realtime_service import DashboardEventType, MessagePriority, RealtimeMessage

logger = logging.getLogger(__name__)


class EventCategory(Enum):
    """事件分类"""
    SYSTEM = "SYSTEM"  # 系统事件
    PROJECT = "PROJECT"  # 项目事件
    REQUIREMENT = "REQUIREMENT"  # 需求事件
    TEST = "TEST"  # 测试事件
    USER = "USER"  # 用户事件
    DASHBOARD = "DASHBOARD"  # 仪表板事件


class EventScope(Enum):
    """事件范围"""
    GLOBAL = "GLOBAL"  # 全局事件
    PROJECT = "PROJECT"  # 项目级事件
    TEAM = "TEAM"  # 团队级事件
    USER = "USER"  # 用户级事件


class EventFilter:
    """事件过滤器"""
    
    def __init__(
        self,
        event_types: Optional[List[DashboardEventType]] = None,
        categories: Optional[List[EventCategory]] = None,
        scopes: Optional[List[EventScope]] = None,
        roles: Optional[List[str]] = None,
        projects: Optional[List[int]] = None,
        users: Optional[List[int]] = None,
        priority_min: Optional[MessagePriority] = None,
        priority_max: Optional[MessagePriority] = None
    ):
        self.event_types = set(event_types) if event_types else set()
        self.categories = set(categories) if categories else set()
        self.scopes = set(scopes) if scopes else set()
        self.roles = set(roles) if roles else set()
        self.projects = set(projects) if projects else set()
        self.users = set(users) if users else set()
        self.priority_min = priority_min
        self.priority_max = priority_max
    
    def matches(self, event: 'DashboardEvent') -> bool:
        """检查事件是否匹配过滤器"""
        # 检查事件类型
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # 检查事件分类
        if self.categories and event.category not in self.categories:
            return False
        
        # 检查事件范围
        if self.scopes and event.scope not in self.scopes:
            return False
        
        # 检查角色
        if self.roles and not (set(event.target_roles) & self.roles):
            return False
        
        # 检查项目
        if self.projects and not (set(event.target_projects) & self.projects):
            return False
        
        # 检查用户
        if self.users and not (set(event.target_users) & self.users):
            return False
        
        # 检查优先级
        if self.priority_min and event.priority.value < self.priority_min.value:
            return False
        
        if self.priority_max and event.priority.value > self.priority_max.value:
            return False
        
        return True


class DashboardEvent:
    """仪表板事件类"""
    
    def __init__(
        self,
        event_type: DashboardEventType,
        category: EventCategory,
        scope: EventScope,
        data: Dict[str, Any],
        source_user_id: Optional[int] = None,
        target_users: Optional[List[int]] = None,
        target_roles: Optional[List[str]] = None,
        target_projects: Optional[List[int]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.event_id = f"{event_type.value}_{uuid.uuid4().hex[:12]}"
        self.event_type = event_type
        self.category = category
        self.scope = scope
        self.data = data
        self.source_user_id = source_user_id
        self.target_users = target_users or []
        self.target_roles = target_roles or []
        self.target_projects = target_projects or []
        self.priority = priority
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.processed = False
        self.retry_count = 0
        self.max_retries = 3
    
    def to_realtime_message(self) -> RealtimeMessage:
        """转换为实时消息"""
        return RealtimeMessage(
            event_type=self.event_type,
            data={
                'event_id': self.event_id,
                'category': self.category.value,
                'scope': self.scope.value,
                'source_user_id': self.source_user_id,
                'data': self.data,
                'metadata': self.metadata
            },
            target_user_ids=self.target_users,
            target_roles=self.target_roles,
            target_projects=self.target_projects,
            priority=self.priority
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'category': self.category.value,
            'scope': self.scope.value,
            'data': self.data,
            'source_user_id': self.source_user_id,
            'target_users': self.target_users,
            'target_roles': self.target_roles,
            'target_projects': self.target_projects,
            'priority': self.priority.value,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'processed': self.processed,
            'retry_count': self.retry_count
        }


class EventSubscription:
    """事件订阅类"""
    
    def __init__(
        self,
        user_id: int,
        role_type: str,
        event_filter: EventFilter,
        callback: Optional[Callable] = None,
        active: bool = True
    ):
        self.subscription_id = f"sub_{user_id}_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.role_type = role_type
        self.event_filter = event_filter
        self.callback = callback
        self.active = active
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.event_count = 0
    
    def matches_event(self, event: DashboardEvent) -> bool:
        """检查事件是否匹配订阅"""
        if not self.active:
            return False
        
        return self.event_filter.matches(event)
    
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = datetime.utcnow()
        self.event_count += 1


class DashboardEventService:
    """仪表板事件管理服务"""
    
    def __init__(self, permission_service: PermissionService):
        self.permission_service = permission_service
        
        # 事件订阅管理
        self.subscriptions: Dict[str, EventSubscription] = {}  # subscription_id -> subscription
        self.user_subscriptions: Dict[int, Set[str]] = {}  # user_id -> subscription_ids
        self.role_subscriptions: Dict[str, Set[str]] = {}  # role -> subscription_ids
        self.project_subscriptions: Dict[int, Set[str]] = {}  # project_id -> subscription_ids
        
        # 事件队列
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.priority_queues: Dict[MessagePriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in MessagePriority
        }
        
        # 事件处理器
        self.event_handlers: Dict[DashboardEventType, List[Callable]] = {}
        
        # 事件历史
        self.event_history: List[DashboardEvent] = []
        self.max_history_size = 1000
        
        # 统计信息
        self.stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'subscriptions_active': 0,
            'handlers_registered': 0
        }
        
        # Redis客户端
        self.redis_client = get_redis_client()
        
        # 后台任务
        self.background_tasks: Set[asyncio.Task] = set()
        
        # 启动事件处理器
        self._start_event_processor()
    
    def _start_event_processor(self):
        """启动事件处理器"""
        # 主事件处理任务
        processor_task = asyncio.create_task(self._event_processor())
        self.background_tasks.add(processor_task)
        processor_task.add_done_callback(self.background_tasks.discard)
        
        # 优先级事件处理任务
        for priority in MessagePriority:
            priority_task = asyncio.create_task(self._priority_event_processor(priority))
            self.background_tasks.add(priority_task)
            priority_task.add_done_callback(self.background_tasks.discard)
        
        # 事件清理任务
        cleanup_task = asyncio.create_task(self._event_cleanup())
        self.background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self.background_tasks.discard)
    
    async def subscribe(
        self,
        user_id: int,
        role_type: str,
        event_filter: EventFilter,
        callback: Optional[Callable] = None
    ) -> str:
        """
        创建事件订阅
        
        Args:
            user_id: 用户ID
            role_type: 用户角色
            event_filter: 事件过滤器
            callback: 回调函数
            
        Returns:
            str: 订阅ID
        """
        subscription = EventSubscription(
            user_id=user_id,
            role_type=role_type,
            event_filter=event_filter,
            callback=callback
        )
        
        # 存储订阅
        self.subscriptions[subscription.subscription_id] = subscription
        
        # 更新用户订阅映射
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(subscription.subscription_id)
        
        # 更新角色订阅映射
        if role_type not in self.role_subscriptions:
            self.role_subscriptions[role_type] = set()
        self.role_subscriptions[role_type].add(subscription.subscription_id)
        
        # 更新项目订阅映射
        for project_id in event_filter.projects:
            if project_id not in self.project_subscriptions:
                self.project_subscriptions[project_id] = set()
            self.project_subscriptions[project_id].add(subscription.subscription_id)
        
        # 更新统计
        self.stats['subscriptions_active'] = len(self.subscriptions)
        
        logger.info(f"Created event subscription: {subscription.subscription_id} for user {user_id}")
        return subscription.subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消事件订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            bool: 是否成功取消
        """
        if subscription_id not in self.subscriptions:
            return False
        
        subscription = self.subscriptions[subscription_id]
        user_id = subscription.user_id
        role_type = subscription.role_type
        
        # 从订阅映射中移除
        del self.subscriptions[subscription_id]
        
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(subscription_id)
            if not self.user_subscriptions[user_id]:
                del self.user_subscriptions[user_id]
        
        if role_type in self.role_subscriptions:
            self.role_subscriptions[role_type].discard(subscription_id)
            if not self.role_subscriptions[role_type]:
                del self.role_subscriptions[role_type]
        
        for project_connections in self.project_subscriptions.values():
            project_connections.discard(subscription_id)
        
        # 更新统计
        self.stats['subscriptions_active'] = len(self.subscriptions)
        
        logger.info(f"Removed event subscription: {subscription_id}")
        return True
    
    async def publish_event(self, event: DashboardEvent) -> bool:
        """
        发布事件
        
        Args:
            event: 仪表板事件
            
        Returns:
            bool: 是否成功发布
        """
        try:
            # 验证事件权限
            if not await self._validate_event_permissions(event):
                logger.warning(f"Event permission validation failed: {event.event_id}")
                return False
            
            # 添加到相应的队列
            if event.priority == MessagePriority.CRITICAL:
                await self.priority_queues[MessagePriority.CRITICAL].put(event)
            elif event.priority == MessagePriority.HIGH:
                await self.priority_queues[MessagePriority.HIGH].put(event)
            else:
                await self.event_queue.put(event)
            
            # 更新统计
            self.stats['events_published'] += 1
            
            # 添加到历史记录
            self._add_to_history(event)
            
            # 缓存到Redis
            await self._cache_event(event)
            
            logger.debug(f"Published event: {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            self.stats['events_failed'] += 1
            return False
    
    async def publish_project_update(
        self,
        project_id: int,
        update_type: str,
        data: Dict[str, Any],
        source_user_id: Optional[int] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """
        发布项目更新事件
        
        Args:
            project_id: 项目ID
            update_type: 更新类型
            data: 更新数据
            source_user_id: 源用户ID
            priority: 消息优先级
        """
        event = DashboardEvent(
            event_type=DashboardEventType.DASHBOARD_DATA_UPDATE,
            category=EventCategory.PROJECT,
            scope=EventScope.PROJECT,
            data={
                'update_type': update_type,
                'project_id': project_id,
                'data': data
            },
            source_user_id=source_user_id,
            target_projects=[project_id],
            target_roles=['PROJECT_MANAGER', 'ADMIN'],
            priority=priority
        )
        
        await self.publish_event(event)
    
    async def publish_requirement_update(
        self,
        requirement_id: int,
        project_id: int,
        update_type: str,
        data: Dict[str, Any],
        source_user_id: Optional[int] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """
        发布需求更新事件
        
        Args:
            requirement_id: 需求ID
            project_id: 项目ID
            update_type: 更新类型
            data: 更新数据
            source_user_id: 源用户ID
            priority: 消息优先级
        """
        event = DashboardEvent(
            event_type=DashboardEventType.WIDGET_DATA_UPDATE,
            category=EventCategory.REQUIREMENT,
            scope=EventScope.PROJECT,
            data={
                'update_type': update_type,
                'requirement_id': requirement_id,
                'project_id': project_id,
                'data': data
            },
            source_user_id=source_user_id,
            target_projects=[project_id],
            target_roles=['REQUIREMENT_MANAGER', 'PROJECT_MANAGER', 'ADMIN'],
            priority=priority
        )
        
        await self.publish_event(event)
    
    async def publish_test_update(
        self,
        test_case_id: int,
        project_id: int,
        update_type: str,
        data: Dict[str, Any],
        source_user_id: Optional[int] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ):
        """
        发布测试更新事件
        
        Args:
            test_case_id: 测试用例ID
            project_id: 项目ID
            update_type: 更新类型
            data: 更新数据
            source_user_id: 源用户ID
            priority: 消息优先级
        """
        event = DashboardEvent(
            event_type=DashboardEventType.WIDGET_DATA_UPDATE,
            category=EventCategory.TEST,
            scope=EventScope.PROJECT,
            data={
                'update_type': update_type,
                'test_case_id': test_case_id,
                'project_id': project_id,
                'data': data
            },
            source_user_id=source_user_id,
            target_projects=[project_id],
            target_roles=['TESTER', 'PROJECT_MANAGER', 'ADMIN'],
            priority=priority
        )
        
        await self.publish_event(event)
    
    async def publish_system_alert(
        self,
        alert_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        target_roles: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.HIGH
    ):
        """
        发布系统告警事件
        
        Args:
            alert_type: 告警类型
            message: 告警消息
            data: 告警数据
            target_roles: 目标角色
            priority: 消息优先级
        """
        event = DashboardEvent(
            event_type=DashboardEventType.SYSTEM_ALERT,
            category=EventCategory.SYSTEM,
            scope=EventScope.GLOBAL,
            data={
                'alert_type': alert_type,
                'message': message,
                'data': data or {}
            },
            target_roles=target_roles or ['ADMIN', 'DEVOPS'],
            priority=priority
        )
        
        await self.publish_event(event)
    
    async def publish_user_activity(
        self,
        user_id: int,
        activity_type: str,
        data: Dict[str, Any],
        target_users: Optional[List[int]] = None,
        target_projects: Optional[List[int]] = None
    ):
        """
        发布用户活动事件
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
            data: 活动数据
            target_users: 目标用户
            target_projects: 目标项目
        """
        event = DashboardEvent(
            event_type=DashboardEventType.USER_ACTIVITY,
            category=EventCategory.USER,
            scope=EventScope.USER if target_users else EventScope.PROJECT,
            data={
                'activity_type': activity_type,
                'user_id': user_id,
                'data': data
            },
            source_user_id=user_id,
            target_users=target_users,
            target_projects=target_projects,
            priority=MessagePriority.LOW
        )
        
        await self.publish_event(event)
    
    def register_event_handler(
        self,
        event_type: DashboardEventType,
        handler: Callable[[DashboardEvent], None]
    ):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        self.stats['handlers_registered'] = sum(len(handlers) for handlers in self.event_handlers.values())
        
        logger.info(f"Registered event handler for {event_type.value}")
    
    def unregister_event_handler(
        self,
        event_type: DashboardEventType,
        handler: Callable[[DashboardEvent], None]
    ):
        """
        取消注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理器函数
        """
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
                if not self.event_handlers[event_type]:
                    del self.event_handlers[event_type]
                
                self.stats['handlers_registered'] = sum(len(handlers) for handlers in self.event_handlers.values())
                logger.info(f"Unregistered event handler for {event_type.value}")
            except ValueError:
                pass
    
    async def get_user_subscriptions(self, user_id: int) -> List[EventSubscription]:
        """
        获取用户的事件订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[EventSubscription]: 订阅列表
        """
        if user_id not in self.user_subscriptions:
            return []
        
        subscriptions = []
        for subscription_id in self.user_subscriptions[user_id]:
            if subscription_id in self.subscriptions:
                subscriptions.append(self.subscriptions[subscription_id])
        
        return subscriptions
    
    async def get_event_history(
        self,
        user_id: int,
        limit: int = 50,
        event_types: Optional[List[DashboardEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[DashboardEvent]:
        """
        获取事件历史
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            event_types: 事件类型过滤
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[DashboardEvent]: 事件列表
        """
        # 获取用户权限相关的事件
        user_events = []
        
        for event in reversed(self.event_history):  # 最新的在前
            # 时间过滤
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            # 事件类型过滤
            if event_types and event.event_type not in event_types:
                continue
            
            # 权限检查
            if await self._user_can_access_event(user_id, event):
                user_events.append(event)
                
                if len(user_events) >= limit:
                    break
        
        return user_events
    
    async def _event_processor(self):
        """主事件处理器"""
        while True:
            try:
                # 处理普通优先级事件
                event = await self.event_queue.get()
                await self._process_event(event)
                
            except Exception as e:
                logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(1)
    
    async def _priority_event_processor(self, priority: MessagePriority):
        """优先级事件处理器"""
        while True:
            try:
                event = await self.priority_queues[priority].get()
                await self._process_event(event)
                
            except Exception as e:
                logger.error(f"Error in priority event processor ({priority.name}): {e}")
                await asyncio.sleep(0.1)
    
    async def _process_event(self, event: DashboardEvent):
        """
        处理单个事件
        
        Args:
            event: 仪表板事件
        """
        try:
            # 查找匹配的订阅
            matching_subscriptions = await self._find_matching_subscriptions(event)
            
            # 调用事件处理器
            if event.event_type in self.event_handlers:
                for handler in self.event_handlers[event.event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
            
            # 通知订阅者
            for subscription in matching_subscriptions:
                try:
                    subscription.update_activity()
                    
                    if subscription.callback:
                        if asyncio.iscoroutinefunction(subscription.callback):
                            await subscription.callback(event)
                        else:
                            subscription.callback(event)
                            
                except Exception as e:
                    logger.error(f"Error in subscription callback: {e}")
            
            # 标记事件为已处理
            event.processed = True
            self.stats['events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
            event.retry_count += 1
            
            if event.retry_count < event.max_retries:
                # 重新加入队列
                await asyncio.sleep(2 ** event.retry_count)  # 指数退避
                await self.event_queue.put(event)
            else:
                self.stats['events_failed'] += 1
    
    async def _find_matching_subscriptions(self, event: DashboardEvent) -> List[EventSubscription]:
        """
        查找匹配的订阅
        
        Args:
            event: 仪表板事件
            
        Returns:
            List[EventSubscription]: 匹配的订阅列表
        """
        matching_subscriptions = []
        
        # 检查所有活跃订阅
        for subscription in self.subscriptions.values():
            if subscription.matches_event(event):
                # 额外的权限检查
                if await self._subscription_can_access_event(subscription, event):
                    matching_subscriptions.append(subscription)
        
        return matching_subscriptions
    
    async def _validate_event_permissions(self, event: DashboardEvent) -> bool:
        """
        验证事件权限
        
        Args:
            event: 仪表板事件
            
        Returns:
            bool: 是否有权限
        """
        try:
            # 如果有源用户，检查用户权限
            if event.source_user_id:
                # 检查用户是否有发布此类事件的权限
                if not await self._user_can_publish_event(event.source_user_id, event):
                    return False
            
            # 检查目标项目权限
            if event.target_projects:
                for project_id in event.target_projects:
                    if not await self._validate_project_access(project_id, event):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating event permissions: {e}")
            return False
    
    async def _user_can_publish_event(self, user_id: int, event: DashboardEvent) -> bool:
        """
        检查用户是否可以发布事件
        
        Args:
            user_id: 用户ID
            event: 仪表板事件
            
        Returns:
            bool: 是否可以发布
        """
        try:
            # 获取用户信息
            db = next(get_db())
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user or not user.is_active:
                return False
            
            # 根据事件类型检查权限
            if event.category == EventCategory.SYSTEM:
                # 系统事件需要管理员权限
                return await self.permission_service.check_permission(user_id, "system:manage")
            
            elif event.category == EventCategory.PROJECT:
                # 项目事件需要项目权限
                if event.target_projects:
                    for project_id in event.target_projects:
                        if not await self.permission_service.check_project_permission(
                            user_id, project_id, "project:update"
                        ):
                            return False
                return True
            
            elif event.category in [EventCategory.REQUIREMENT, EventCategory.TEST]:
                # 需求和测试事件需要相应的权限
                permission_map = {
                    EventCategory.REQUIREMENT: "requirement:update",
                    EventCategory.TEST: "test:update"
                }
                
                permission = permission_map.get(event.category)
                if permission:
                    return await self.permission_service.check_permission(user_id, permission)
            
            # 用户事件默认允许
            return True
            
        except Exception as e:
            logger.error(f"Error checking user publish permission: {e}")
            return False
    
    async def _user_can_access_event(self, user_id: int, event: DashboardEvent) -> bool:
        """
        检查用户是否可以访问事件
        
        Args:
            user_id: 用户ID
            event: 仪表板事件
            
        Returns:
            bool: 是否可以访问
        """
        try:
            # 检查是否是目标用户
            if event.target_users and user_id in event.target_users:
                return True
            
            # 检查用户角色
            if event.target_roles:
                user_roles = await self.permission_service.get_user_roles(user_id)
                if any(role.name in event.target_roles for role in user_roles):
                    return True
            
            # 检查项目权限
            if event.target_projects:
                for project_id in event.target_projects:
                    if await self.permission_service.check_project_permission(
                        user_id, project_id, "project:read"
                    ):
                        return True
            
            # 检查是否是事件发布者
            if event.source_user_id == user_id:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking user event access: {e}")
            return False
    
    async def _subscription_can_access_event(
        self,
        subscription: EventSubscription,
        event: DashboardEvent
    ) -> bool:
        """
        检查订阅是否可以访问事件
        
        Args:
            subscription: 事件订阅
            event: 仪表板事件
            
        Returns:
            bool: 是否可以访问
        """
        return await self._user_can_access_event(subscription.user_id, event)
    
    async def _validate_project_access(self, project_id: int, event: DashboardEvent) -> bool:
        """
        验证项目访问权限
        
        Args:
            project_id: 项目ID
            event: 仪表板事件
            
        Returns:
            bool: 是否有权限
        """
        try:
            # 检查项目是否存在且活跃
            db = next(get_db())
            project = db.query(Project).filter(
                and_(Project.id == project_id, Project.is_active == True)
            ).first()
            
            return project is not None
            
        except Exception as e:
            logger.error(f"Error validating project access: {e}")
            return False
    
    def _add_to_history(self, event: DashboardEvent):
        """
        添加事件到历史记录
        
        Args:
            event: 仪表板事件
        """
        self.event_history.append(event)
        
        # 限制历史记录大小
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
    
    async def _cache_event(self, event: DashboardEvent):
        """
        缓存事件到Redis
        
        Args:
            event: 仪表板事件
        """
        try:
            if self.redis_client:
                key = f"dashboard:events:{event.event_id}"
                event_data = event.to_dict()
                
                await self.redis_client.setex(
                    key,
                    3600,  # 1小时过期
                    json.dumps(event_data, ensure_ascii=False)
                )
                
                # 添加到事件索引
                index_key = f"dashboard:event_index:{event.category.value}"
                await self.redis_client.zadd(
                    index_key,
                    {event.event_id: event.timestamp.timestamp()}
                )
                await self.redis_client.expire(index_key, 86400)  # 24小时过期
                
        except Exception as e:
            logger.error(f"Error caching event: {e}")
    
    async def _event_cleanup(self):
        """事件清理后台任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                
                # 清理过期的订阅
                current_time = datetime.utcnow()
                expired_subscriptions = []
                
                for subscription_id, subscription in self.subscriptions.items():
                    # 如果订阅超过24小时没有活动，标记为过期
                    if (current_time - subscription.last_activity).total_seconds() > 86400:
                        expired_subscriptions.append(subscription_id)
                
                for subscription_id in expired_subscriptions:
                    await self.unsubscribe(subscription_id)
                
                # 清理过期的事件历史
                cutoff_time = current_time - timedelta(hours=24)
                self.event_history = [
                    event for event in self.event_history
                    if event.timestamp > cutoff_time
                ]
                
                logger.debug(f"Event cleanup completed. Removed {len(expired_subscriptions)} expired subscriptions")
                
            except Exception as e:
                logger.error(f"Error in event cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            'subscriptions_by_role': {
                role: len(subscription_ids)
                for role, subscription_ids in self.role_subscriptions.items()
            },
            'subscriptions_by_project': {
                str(project_id): len(subscription_ids)
                for project_id, subscription_ids in self.project_subscriptions.items()
            },
            'event_queue_size': self.event_queue.qsize(),
            'priority_queue_sizes': {
                priority.name: queue.qsize()
                for priority, queue in self.priority_queues.items()
            },
            'event_history_size': len(self.event_history),
            'background_tasks': len(self.background_tasks)
        }
    
    async def shutdown(self):
        """关闭服务"""
        try:
            # 取消所有后台任务
            for task in self.background_tasks:
                task.cancel()
            
            # 等待任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 清理订阅
            self.subscriptions.clear()
            self.user_subscriptions.clear()
            self.role_subscriptions.clear()
            self.project_subscriptions.clear()
            
            logger.info("Dashboard event service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during event service shutdown: {e}")


# 全局实例
dashboard_event_service: Optional[DashboardEventService] = None


def get_dashboard_event_service() -> DashboardEventService:
    """获取仪表板事件服务实例"""
    global dashboard_event_service
    
    if dashboard_event_service is None:
        from .permission_service import get_permission_service
        
        dashboard_event_service = DashboardEventService(
            permission_service=get_permission_service()
        )
    
    return dashboard_event_service