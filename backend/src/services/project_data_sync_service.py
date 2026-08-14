"""
项目数据自动同步服务

本模块实现项目数据的自动同步功能，为AI助手提供实时的项目上下文信息。
包括项目基本信息、需求、测试用例、缺陷、质量指标等数据的同步和缓存。

主要功能：
1. 项目数据实时同步
2. 数据变更监听和通知
3. 缓存管理和更新
4. 数据一致性保证
5. 性能优化和批量处理
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload, joinedload

from ..core.config import get_settings
from ..core.database import get_async_session, get_async_session_ctx
from ..models.project import Project, ProjectMetrics
from ..models.test_case import TestCase, Defect
from ..models.requirement import Requirement
from ..models.ai_suggestion import AISuggestion
from ..services.ai_cache_service import AICacheService
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)
settings = get_settings()


class SyncEventType(Enum):
    """同步事件类型"""
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    REQUIREMENT_CREATED = "requirement_created"
    REQUIREMENT_UPDATED = "requirement_updated"
    REQUIREMENT_DELETED = "requirement_deleted"
    TEST_CASE_CREATED = "test_case_created"
    TEST_CASE_UPDATED = "test_case_updated"
    TEST_CASE_DELETED = "test_case_deleted"
    DEFECT_CREATED = "defect_created"
    DEFECT_UPDATED = "defect_updated"
    DEFECT_DELETED = "defect_deleted"
    METRICS_UPDATED = "metrics_updated"


@dataclass
class SyncEvent:
    """同步事件"""
    event_type: SyncEventType
    entity_id: int
    project_id: int
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[int] = None


@dataclass
class ProjectContext:
    """项目上下文数据"""
    project: Dict[str, Any]
    requirements: List[Dict[str, Any]]
    test_cases: List[Dict[str, Any]]
    defects: List[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    last_updated: datetime


class ProjectDataSyncService:
    """项目数据同步服务"""
    
    def __init__(self):
        self.cache_service = AICacheService()
        self.redis_client = None
        self.sync_queue = asyncio.Queue()
        self.sync_running = False
        self.sync_task = None
        
        # 缓存配置
        self.cache_ttl = 3600  # 1小时
        self.batch_size = 100
        self.sync_interval = 300  # 5分钟
        
        # 监听的事件类型
        self.monitored_events = {
            SyncEventType.PROJECT_CREATED,
            SyncEventType.PROJECT_UPDATED,
            SyncEventType.TASK_CREATED,
            SyncEventType.TASK_UPDATED,
            SyncEventType.REQUIREMENT_CREATED,
            SyncEventType.REQUIREMENT_UPDATED,
            SyncEventType.TEST_CASE_CREATED,
            SyncEventType.TEST_CASE_UPDATED,
            SyncEventType.DEFECT_CREATED,
            SyncEventType.DEFECT_UPDATED,
            SyncEventType.METRICS_UPDATED
        }
    
    async def initialize(self):
        """初始化同步服务"""
        try:
            self.redis_client = await get_redis_client()
            logger.info("项目数据同步服务初始化成功")
        except Exception as e:
            logger.error(f"项目数据同步服务初始化失败: {e}")
            raise
    
    async def start_sync_worker(self):
        """启动同步工作进程"""
        if self.sync_running:
            logger.warning("同步工作进程已在运行")
            return
        
        self.sync_running = True
        self.sync_task = asyncio.create_task(self._sync_worker())
        logger.info("项目数据同步工作进程已启动")
    
    async def stop_sync_worker(self):
        """停止同步工作进程"""
        if not self.sync_running:
            return
        
        self.sync_running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("项目数据同步工作进程已停止")
    
    async def _sync_worker(self):
        """同步工作进程"""
        while self.sync_running:
            try:
                # 处理同步队列中的事件
                await self._process_sync_queue()
                
                # 定期全量同步检查
                await self._periodic_sync_check()
                
                # 等待下一个同步周期
                await asyncio.sleep(self.sync_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"同步工作进程异常: {e}")
                await asyncio.sleep(60)  # 异常后等待1分钟再重试
    
    async def _process_sync_queue(self):
        """处理同步队列"""
        events_to_process = []
        
        # 批量获取队列中的事件
        try:
            while len(events_to_process) < self.batch_size:
                event = await asyncio.wait_for(self.sync_queue.get(), timeout=1.0)
                events_to_process.append(event)
        except asyncio.TimeoutError:
            pass  # 队列为空或超时，继续处理已获取的事件
        
        if not events_to_process:
            return
        
        # 按项目ID分组处理事件
        events_by_project = {}
        for event in events_to_process:
            project_id = event.project_id
            if project_id not in events_by_project:
                events_by_project[project_id] = []
            events_by_project[project_id].append(event)
        
        # 并发处理各项目的同步事件
        tasks = []
        for project_id, project_events in events_by_project.items():
            task = asyncio.create_task(self._sync_project_data(project_id, project_events))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _periodic_sync_check(self):
        """定期同步检查"""
        try:
            async with get_async_session_ctx() as session:
                # 获取所有活跃项目
                result = await session.execute(
                    select(Project.id).where(Project.status.in_(['PLANNING', 'ACTIVE']))
                )
                project_ids = [row[0] for row in result.fetchall()]
                
                # 检查缓存过期的项目
                expired_projects = []
                for project_id in project_ids:
                    cache_key = f"project_context:{project_id}"
                    if not await self.redis_client.exists(cache_key):
                        expired_projects.append(project_id)
                
                # 重新同步过期的项目
                if expired_projects:
                    logger.info(f"发现{len(expired_projects)}个项目缓存过期，开始重新同步")
                    tasks = []
                    for project_id in expired_projects:
                        task = asyncio.create_task(self._sync_project_data(project_id))
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"定期同步检查异常: {e}")
    
    async def notify_data_change(self, event: SyncEvent):
        """通知数据变更"""
        if event.event_type in self.monitored_events:
            await self.sync_queue.put(event)
            logger.debug(f"数据变更事件已加入同步队列: {event.event_type} - 项目{event.project_id}")
    
    async def get_project_context(self, project_id: int, force_refresh: bool = False) -> Optional[ProjectContext]:
        """获取项目上下文数据"""
        cache_key = f"project_context:{project_id}"
        
        # 尝试从缓存获取
        if not force_refresh:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                try:
                    data = json.loads(cached_data)
                    return ProjectContext(
                        project=data['project'],
                        requirements=data['requirements'],
                        test_cases=data['test_cases'],
                        defects=data['defects'],
                        metrics=data.get('metrics'),
                        last_updated=datetime.fromisoformat(data['last_updated'])
                    )
                except Exception as e:
                    logger.warning(f"解析缓存数据失败: {e}")
        
        # 从数据库重新加载
        return await self._load_project_context(project_id)
    
    async def _load_project_context(self, project_id: int) -> Optional[ProjectContext]:
        """从数据库加载项目上下文"""
        try:
            async with get_async_session_ctx() as session:
                # 加载项目基本信息
                project_result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = project_result.scalar_one_or_none()
                
                if not project:
                    logger.warning(f"项目{project_id}不存在")
                    return None
                
                # 加载需求
                requirements_result = await session.execute(
                    select(Requirement).where(Requirement.project_id == project_id)
                )
                requirements = requirements_result.scalars().all()
                
                # 加载测试用例
                test_cases_result = await session.execute(
                    select(TestCase).where(TestCase.project_id == project_id)
                )
                test_cases = test_cases_result.scalars().all()
                
                # 加载缺陷
                defects_result = await session.execute(
                    select(Defect).where(Defect.project_id == project_id)
                )
                defects = defects_result.scalars().all()
                
                # 加载最新指标
                metrics_result = await session.execute(
                    select(ProjectMetrics)
                    .where(ProjectMetrics.project_id == project_id)
                    .order_by(ProjectMetrics.metric_date.desc())
                    .limit(1)
                )
                metrics = metrics_result.scalar_one_or_none()
                
                # 构建上下文对象
                context = ProjectContext(
                    project=project.to_dict(),
                    requirements=[req.to_dict() for req in requirements],
                    test_cases=[tc.to_dict() for tc in test_cases],
                    defects=[defect.to_dict() for defect in defects],
                    metrics=metrics.to_dict() if metrics else None,
                    last_updated=datetime.utcnow()
                )
                
                # 缓存数据
                await self._cache_project_context(project_id, context)
                
                return context
                
        except Exception as e:
            logger.error(f"加载项目{project_id}上下文失败: {e}")
            return None
    
    async def _cache_project_context(self, project_id: int, context: ProjectContext):
        """缓存项目上下文数据"""
        try:
            cache_key = f"project_context:{project_id}"
            cache_data = {
                'project': context.project,
                'requirements': context.requirements,
                'test_cases': context.test_cases,
                'defects': context.defects,
                'metrics': context.metrics,
                'last_updated': context.last_updated.isoformat()
            }
            
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_data, ensure_ascii=False)
            )
            
            logger.debug(f"项目{project_id}上下文数据已缓存")
            
        except Exception as e:
            logger.error(f"缓存项目{project_id}上下文失败: {e}")
    
    async def _sync_project_data(self, project_id: int, events: Optional[List[SyncEvent]] = None):
        """同步项目数据"""
        try:
            # 重新加载项目上下文
            context = await self._load_project_context(project_id)
            
            if not context:
                logger.warning(f"无法加载项目{project_id}的上下文数据")
                return
            
            # 更新相关的AI建议缓存
            await self._invalidate_ai_suggestions_cache(project_id)
            
            # 通知AI助手服务数据更新
            await self._notify_ai_assistant_update(project_id, events)
            
            logger.info(f"项目{project_id}数据同步完成")
            
        except Exception as e:
            logger.error(f"同步项目{project_id}数据失败: {e}")
    
    async def _invalidate_ai_suggestions_cache(self, project_id: int):
        """失效AI建议缓存"""
        try:
            # 清除项目相关的建议缓存
            cache_patterns = [
                f"ai_suggestions:project:{project_id}:*",
                f"requirements_analysis:project:{project_id}:*",
                f"project_analysis:project:{project_id}:*"
            ]
            
            for pattern in cache_patterns:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            logger.debug(f"项目{project_id}的AI建议缓存已清除")
            
        except Exception as e:
            logger.error(f"清除项目{project_id}AI建议缓存失败: {e}")
    
    async def _notify_ai_assistant_update(self, project_id: int, events: Optional[List[SyncEvent]] = None):
        """通知AI助手服务数据更新"""
        try:
            # 发布数据更新事件到Redis
            event_data = {
                'project_id': project_id,
                'timestamp': datetime.utcnow().isoformat(),
                'events': [
                    {
                        'type': event.event_type.value,
                        'entity_id': event.entity_id,
                        'data': event.data
                    } for event in (events or [])
                ]
            }
            
            await self.redis_client.publish(
                'project_data_update',
                json.dumps(event_data, ensure_ascii=False)
            )
            
            logger.debug(f"项目{project_id}数据更新通知已发送")
            
        except Exception as e:
            logger.error(f"发送项目{project_id}数据更新通知失败: {e}")
    
    async def get_project_summary(self, project_id: int) -> Optional[Dict[str, Any]]:
        """获取项目摘要信息"""
        context = await self.get_project_context(project_id)
        
        if not context:
            return None
        
        # 计算统计信息
        total_requirements = len(context.requirements)
        completed_requirements = len([req for req in context.requirements if req['status'] == 'IMPLEMENTED'])
        
        total_test_cases = len(context.test_cases)
        passed_test_cases = len([tc for tc in context.test_cases if tc['pass_count'] > 0])
        
        total_defects = len(context.defects)
        open_defects = len([defect for defect in context.defects if defect['status'] not in ['RESOLVED', 'CLOSED']])
        
        return {
            'project_id': project_id,
            'project_name': context.project['name'],
            'project_status': context.project['status'],
            'requirements': {
                'total': total_requirements,
                'completed': completed_requirements,
                'completion_rate': completed_requirements / total_requirements if total_requirements > 0 else 0
            },
            'test_cases': {
                'total': total_test_cases,
                'passed': passed_test_cases,
                'pass_rate': passed_test_cases / total_test_cases if total_test_cases > 0 else 0
            },
            'defects': {
                'total': total_defects,
                'open': open_defects,
                'resolution_rate': (total_defects - open_defects) / total_defects if total_defects > 0 else 1
            },
            'metrics': context.metrics,
            'last_updated': context.last_updated.isoformat()
        }
    
    async def get_projects_list(self, user_id: Optional[int] = None, status_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取项目列表"""
        try:
            async with get_async_session_ctx() as session:
                query = select(Project)
                
                # 状态过滤
                if status_filter:
                    query = query.where(Project.status.in_(status_filter))
                
                # 用户权限过滤（如果需要）
                if user_id:
                    # 这里可以添加用户权限检查逻辑
                    pass
                
                result = await session.execute(query.order_by(Project.updated_at.desc()))
                projects = result.scalars().all()
                
                return [project.to_dict() for project in projects]
                
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            return []
    
    async def update_project_metrics(self, project_id: int):
        """更新项目指标"""
        try:
            context = await self.get_project_context(project_id, force_refresh=True)
            
            if not context:
                return
            
            # 计算各种指标
            requirements = context.requirements
            test_cases = context.test_cases
            defects = context.defects
            
            # 需求指标
            requirements_total = len(requirements)
            requirements_completed = len([req for req in requirements if req['status'] == 'IMPLEMENTED'])
            requirements_coverage = requirements_completed / requirements_total if requirements_total > 0 else 0
            
            # 计算需求质量评分
            quality_scores = [req.get('completeness_score', 0) for req in requirements if req.get('completeness_score')]
            requirements_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            # 测试指标
            test_cases_total = len(test_cases)
            test_cases_executed = len([tc for tc in test_cases if tc['execution_count'] > 0])
            test_cases_passed = len([tc for tc in test_cases if tc['pass_count'] > 0])
            test_coverage = test_cases_executed / test_cases_total if test_cases_total > 0 else 0
            automation_rate = len([tc for tc in test_cases if tc['is_automated']]) / test_cases_total if test_cases_total > 0 else 0
            
            # 质量指标
            defects_total = len(defects)
            defects_open = len([defect for defect in defects if defect['status'] not in ['RESOLVED', 'CLOSED']])
            defects_critical = len([defect for defect in defects if defect['severity'] == 'CRITICAL'])
            defect_density = defects_total / requirements_total if requirements_total > 0 else 0
            
            # 保存指标到数据库
            async with get_async_session_ctx() as session:
                metrics = ProjectMetrics(
                    project_id=project_id,
                    metric_date=datetime.utcnow(),
                    requirements_total=requirements_total,
                    requirements_completed=requirements_completed,
                    requirements_coverage=requirements_coverage,
                    requirements_quality_score=requirements_quality_score,
                    test_cases_total=test_cases_total,
                    test_cases_executed=test_cases_executed,
                    test_cases_passed=test_cases_passed,
                    test_coverage=test_coverage,
                    automation_rate=automation_rate,
                    defects_total=defects_total,
                    defects_open=defects_open,
                    defects_critical=defects_critical,
                    defect_density=defect_density
                )
                
                session.add(metrics)
                await session.commit()
                
                # 通知指标更新
                await self.notify_data_change(SyncEvent(
                    event_type=SyncEventType.METRICS_UPDATED,
                    entity_id=metrics.id,
                    project_id=project_id,
                    data=metrics.to_dict(),
                    timestamp=datetime.utcnow()
                ))
                
                logger.info(f"项目{project_id}指标更新完成")
                
        except Exception as e:
            logger.error(f"更新项目{project_id}指标失败: {e}")


# 全局同步服务实例
_sync_service = None

async def get_project_sync_service() -> ProjectDataSyncService:
    """获取项目数据同步服务实例"""
    global _sync_service
    
    if _sync_service is None:
        _sync_service = ProjectDataSyncService()
        await _sync_service.initialize()
    
    return _sync_service


# 便捷函数
async def sync_project_data(project_id: int):
    """同步指定项目数据"""
    service = await get_project_sync_service()
    await service._sync_project_data(project_id)


async def get_project_context(project_id: int, force_refresh: bool = False) -> Optional[ProjectContext]:
    """获取项目上下文"""
    service = await get_project_sync_service()
    return await service.get_project_context(project_id, force_refresh)


async def notify_project_change(event_type: SyncEventType, entity_id: int, project_id: int, 
                               data: Dict[str, Any], user_id: Optional[int] = None):
    """通知项目数据变更"""
    service = await get_project_sync_service()
    event = SyncEvent(
        event_type=event_type,
        entity_id=entity_id,
        project_id=project_id,
        data=data,
        timestamp=datetime.utcnow(),
        user_id=user_id
    )
    await service.notify_data_change(event)