"""
任务依赖关系管理服务

本模块实现任务依赖关系的核心业务逻辑，包括：
- 依赖关系验证和循环检测
- 关键路径分析
- 任务自动激活
- 依赖关系图构建
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
from collections import defaultdict, deque

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from fastapi import Depends

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError
from ..models.project import Task
from ..schemas.task import TaskStatus, TaskType

logger = logging.getLogger(__name__)


class TaskDependencyService:
    """任务依赖关系管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_dependencies(
        self, 
        task_id: int, 
        dependency_task_ids: List[int], 
        project_id: int
    ) -> bool:
        """
        验证任务依赖关系
        
        Args:
            task_id: 任务ID
            dependency_task_ids: 依赖任务ID列表
            project_id: 项目ID
            
        Returns:
            验证是否通过
            
        Raises:
            ValidationError: 验证失败
        """
        if not dependency_task_ids:
            return True
        
        # 1. 验证依赖任务是否存在且属于同一项目
        await self._validate_dependency_tasks_exist(dependency_task_ids, project_id)
        
        # 2. 验证不能依赖自己
        if task_id in dependency_task_ids:
            raise ValidationError("任务不能依赖自己")
        
        # 3. 验证不会形成循环依赖
        await self._validate_no_circular_dependency(task_id, dependency_task_ids, project_id)
        
        return True
    
    async def detect_circular_dependency(
        self, 
        task_id: int, 
        new_dependencies: List[int], 
        project_id: int
    ) -> bool:
        """
        检测循环依赖
        
        Args:
            task_id: 任务ID
            new_dependencies: 新的依赖任务ID列表
            project_id: 项目ID
            
        Returns:
            是否存在循环依赖
        """
        try:
            await self._validate_no_circular_dependency(task_id, new_dependencies, project_id)
            return False
        except ValidationError:
            return True
    
    async def calculate_critical_path(self, project_id: int) -> Dict[str, Any]:
        """
        计算关键路径
        
        Args:
            project_id: 项目ID
            
        Returns:
            关键路径分析结果
        """
        # 1. 获取项目所有任务
        tasks = await self._get_project_tasks(project_id)
        
        if not tasks:
            return {
                "critical_path": [],
                "total_duration": 0,
                "critical_tasks": [],
                "task_schedules": {}
            }
        
        # 2. 构建任务依赖图
        dependency_graph = await self._build_dependency_graph(tasks)
        
        # 3. 计算最早开始时间和最早结束时间
        early_times = await self._calculate_early_times(tasks, dependency_graph)
        
        # 4. 计算最晚开始时间和最晚结束时间
        late_times = await self._calculate_late_times(tasks, dependency_graph, early_times)
        
        # 5. 识别关键任务（浮动时间为0的任务）
        critical_tasks = []
        task_schedules = {}
        
        for task in tasks:
            early_start = early_times[task.id]['early_start']
            early_finish = early_times[task.id]['early_finish']
            late_start = late_times[task.id]['late_start']
            late_finish = late_times[task.id]['late_finish']
            
            # 计算浮动时间
            float_time = late_start - early_start
            
            task_schedules[task.id] = {
                "task_id": task.id,
                "task_name": task.task_name,
                "duration": self._get_task_duration(task),
                "early_start": early_start,
                "early_finish": early_finish,
                "late_start": late_start,
                "late_finish": late_finish,
                "float_time": float_time,
                "is_critical": float_time == 0
            }
            
            if float_time == 0:
                critical_tasks.append(task.id)
        
        # 6. 构建关键路径
        critical_path = await self._build_critical_path(critical_tasks, dependency_graph, task_schedules)
        
        # 7. 计算项目总工期
        total_duration = max(early_times[task_id]['early_finish'] for task_id in early_times.keys()) if early_times else 0
        
        return {
            "critical_path": critical_path,
            "total_duration": total_duration,
            "critical_tasks": critical_tasks,
            "task_schedules": task_schedules,
            "project_id": project_id,
            "calculated_at": datetime.utcnow()
        }
    
    async def get_task_dependencies(self, task_id: int) -> Dict[str, Any]:
        """
        获取任务依赖关系信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            依赖关系信息
        """
        # 获取任务
        task = await self._get_task_by_id(task_id)
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")
        
        # 获取直接依赖
        direct_dependencies = task.dependency_tasks or []
        
        # 获取被依赖的任务
        dependents = await self._get_task_dependents(task_id, task.project_id)
        
        # 获取依赖链
        dependency_chain = await self._get_dependency_chain(task_id, task.project_id)
        
        return {
            "task_id": task_id,
            "task_name": task.task_name,
            "direct_dependencies": direct_dependencies,
            "dependents": dependents,
            "dependency_chain": dependency_chain,
            "can_start": await self._can_task_start(task_id),
            "blocking_dependencies": await self._get_blocking_dependencies(task_id)
        }
    
    async def activate_ready_tasks(self, project_id: int) -> List[int]:
        """
        激活准备就绪的任务
        
        Args:
            project_id: 项目ID
            
        Returns:
            被激活的任务ID列表
        """
        activated_tasks = []
        
        # 获取所有待激活的任务（状态为TODO且依赖已满足）
        tasks = await self._get_project_tasks(project_id)
        
        for task in tasks:
            if task.status == TaskStatus.TODO and await self._can_task_start(task.id):
                # 激活任务
                task.status = TaskStatus.ASSIGNED if task.assignee_id else TaskStatus.TODO
                activated_tasks.append(task.id)
                
                logger.info(f"任务 {task.task_code} 依赖条件满足，已激活")
        
        if activated_tasks:
            await self.db.commit()
        
        return activated_tasks
    
    async def update_task_dependencies(
        self, 
        task_id: int, 
        new_dependencies: List[int], 
        project_id: int
    ) -> bool:
        """
        更新任务依赖关系
        
        Args:
            task_id: 任务ID
            new_dependencies: 新的依赖任务ID列表
            project_id: 项目ID
            
        Returns:
            更新是否成功
        """
        # 验证依赖关系
        await self.validate_dependencies(task_id, new_dependencies, project_id)
        
        # 获取任务
        task = await self._get_task_by_id(task_id)
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")
        
        # 更新依赖关系
        task.dependency_tasks = new_dependencies
        await self.db.commit()
        
        # 检查是否可以激活任务
        if await self._can_task_start(task_id):
            await self.activate_ready_tasks(project_id)
        
        return True
    
    # 私有方法
    async def _validate_dependency_tasks_exist(self, dependency_task_ids: List[int], project_id: int):
        """验证依赖任务是否存在且属于同一项目"""
        result = await self.db.execute(
            select(Task.id).where(
                and_(
                    Task.id.in_(dependency_task_ids),
                    Task.project_id == project_id
                )
            )
        )
        existing_task_ids = [row[0] for row in result.fetchall()]
        
        missing_task_ids = set(dependency_task_ids) - set(existing_task_ids)
        if missing_task_ids:
            raise ValidationError(f"依赖任务 {missing_task_ids} 不存在或不属于同一项目")
    
    async def _validate_no_circular_dependency(
        self, 
        task_id: int, 
        new_dependencies: List[int], 
        project_id: int
    ):
        """验证不会形成循环依赖"""
        # 使用深度优先搜索检测循环
        visited = set()
        rec_stack = set()
        
        # 构建依赖图（包含新的依赖关系）
        dependency_graph = await self._build_dependency_graph_with_new_deps(
            project_id, task_id, new_dependencies
        )
        
        def dfs(node_id: int) -> bool:
            """深度优先搜索检测循环"""
            if node_id in rec_stack:
                return True  # 发现循环
            
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # 检查所有依赖的任务
            for dep_id in dependency_graph.get(node_id, []):
                if dfs(dep_id):
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        # 从当前任务开始检测循环
        if dfs(task_id):
            raise ValidationError("设置依赖关系会形成循环依赖")
    
    async def _build_dependency_graph_with_new_deps(
        self, 
        project_id: int, 
        task_id: int, 
        new_dependencies: List[int]
    ) -> Dict[int, List[int]]:
        """构建包含新依赖关系的依赖图"""
        # 获取项目所有任务的依赖关系
        result = await self.db.execute(
            select(Task.id, Task.dependency_tasks).where(Task.project_id == project_id)
        )
        
        dependency_graph = {}
        for row in result.fetchall():
            tid, deps = row
            if tid == task_id:
                # 使用新的依赖关系
                dependency_graph[tid] = new_dependencies
            else:
                # 使用现有的依赖关系
                dependency_graph[tid] = deps or []
        
        return dependency_graph
    
    async def _get_project_tasks(self, project_id: int) -> List[Task]:
        """获取项目所有任务"""
        result = await self.db.execute(
            select(Task).where(Task.project_id == project_id)
        )
        return result.scalars().all()
    
    async def _get_task_by_id(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def _build_dependency_graph(self, tasks: List[Task]) -> Dict[int, List[int]]:
        """构建任务依赖图"""
        dependency_graph = {}
        for task in tasks:
            dependency_graph[task.id] = task.dependency_tasks or []
        return dependency_graph
    
    def _get_task_duration(self, task: Task) -> int:
        """获取任务工期（天数）"""
        if task.planned_start_date and task.planned_end_date:
            return (task.planned_end_date - task.planned_start_date).days + 1
        elif task.estimated_hours:
            # 假设每天工作8小时
            return max(1, int(float(task.estimated_hours) / 8))
        else:
            return 1  # 默认1天
    
    async def _calculate_early_times(
        self, 
        tasks: List[Task], 
        dependency_graph: Dict[int, List[int]]
    ) -> Dict[int, Dict[str, int]]:
        """计算最早开始时间和最早结束时间"""
        early_times = {}
        task_dict = {task.id: task for task in tasks}
        
        # 拓扑排序
        in_degree = defaultdict(int)
        for task_id, deps in dependency_graph.items():
            for dep_id in deps:
                in_degree[task_id] += 1
        
        # 初始化没有依赖的任务
        queue = deque()
        for task in tasks:
            if in_degree[task.id] == 0:
                early_times[task.id] = {
                    'early_start': 0,
                    'early_finish': self._get_task_duration(task) - 1
                }
                queue.append(task.id)
        
        # 计算其他任务的最早时间
        while queue:
            current_id = queue.popleft()
            current_finish = early_times[current_id]['early_finish']
            
            # 更新依赖当前任务的任务
            for task in tasks:
                if current_id in (task.dependency_tasks or []):
                    # 计算最早开始时间
                    early_start = current_finish + 1
                    if task.id in early_times:
                        early_start = max(early_start, early_times[task.id]['early_start'])
                    
                    duration = self._get_task_duration(task)
                    early_times[task.id] = {
                        'early_start': early_start,
                        'early_finish': early_start + duration - 1
                    }
                    
                    # 减少入度
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)
        
        return early_times
    
    async def _calculate_late_times(
        self, 
        tasks: List[Task], 
        dependency_graph: Dict[int, List[int]], 
        early_times: Dict[int, Dict[str, int]]
    ) -> Dict[int, Dict[str, int]]:
        """计算最晚开始时间和最晚结束时间"""
        late_times = {}
        task_dict = {task.id: task for task in tasks}
        
        # 项目最晚结束时间
        project_finish = max(early_times[task_id]['early_finish'] for task_id in early_times.keys())
        
        # 反向拓扑排序
        out_degree = defaultdict(int)
        reverse_graph = defaultdict(list)
        
        for task_id, deps in dependency_graph.items():
            for dep_id in deps:
                reverse_graph[dep_id].append(task_id)
                out_degree[dep_id] += 1
        
        # 初始化没有后续任务的任务
        queue = deque()
        for task in tasks:
            if out_degree[task.id] == 0:
                duration = self._get_task_duration(task)
                late_times[task.id] = {
                    'late_finish': project_finish,
                    'late_start': project_finish - duration + 1
                }
                queue.append(task.id)
        
        # 计算其他任务的最晚时间
        while queue:
            current_id = queue.popleft()
            current_start = late_times[current_id]['late_start']
            
            # 更新当前任务依赖的任务
            for dep_id in dependency_graph.get(current_id, []):
                # 计算最晚结束时间
                late_finish = current_start - 1
                if dep_id in late_times:
                    late_finish = min(late_finish, late_times[dep_id]['late_finish'])
                
                duration = self._get_task_duration(task_dict[dep_id])
                late_times[dep_id] = {
                    'late_finish': late_finish,
                    'late_start': late_finish - duration + 1
                }
                
                # 减少出度
                out_degree[dep_id] -= 1
                if out_degree[dep_id] == 0:
                    queue.append(dep_id)
        
        return late_times
    
    async def _build_critical_path(
        self, 
        critical_tasks: List[int], 
        dependency_graph: Dict[int, List[int]], 
        task_schedules: Dict[int, Dict[str, Any]]
    ) -> List[int]:
        """构建关键路径"""
        if not critical_tasks:
            return []
        
        # 找到关键路径的起点（没有关键前驱的关键任务）
        critical_set = set(critical_tasks)
        start_tasks = []
        
        for task_id in critical_tasks:
            has_critical_predecessor = False
            for dep_id in dependency_graph.get(task_id, []):
                if dep_id in critical_set:
                    has_critical_predecessor = True
                    break
            
            if not has_critical_predecessor:
                start_tasks.append(task_id)
        
        # 从起点构建关键路径
        if not start_tasks:
            return critical_tasks  # 如果没有明确的起点，返回所有关键任务
        
        # 选择最早开始的起点
        start_task = min(start_tasks, key=lambda x: task_schedules[x]['early_start'])
        
        # 构建路径
        path = []
        current = start_task
        visited = set()
        
        while current and current not in visited:
            path.append(current)
            visited.add(current)
            
            # 找到下一个关键任务
            next_task = None
            for task_id in critical_tasks:
                if (current in dependency_graph.get(task_id, []) and 
                    task_id not in visited):
                    if (next_task is None or 
                        task_schedules[task_id]['early_start'] < task_schedules[next_task]['early_start']):
                        next_task = task_id
            
            current = next_task
        
        return path
    
    async def _get_task_dependents(self, task_id: int, project_id: int) -> List[int]:
        """获取依赖当前任务的任务列表"""
        result = await self.db.execute(
            select(Task.id).where(
                and_(
                    Task.project_id == project_id,
                    Task.dependency_tasks.contains([task_id])
                )
            )
        )
        return [row[0] for row in result.fetchall()]
    
    async def _get_dependency_chain(self, task_id: int, project_id: int) -> List[List[int]]:
        """获取依赖链"""
        chains = []
        visited = set()
        
        def dfs(current_id: int, path: List[int]):
            if current_id in visited:
                return
            
            visited.add(current_id)
            path.append(current_id)
            
            # 获取当前任务的依赖
            task = next((t for t in self.tasks_cache if t.id == current_id), None)
            if task and task.dependency_tasks:
                for dep_id in task.dependency_tasks:
                    dfs(dep_id, path.copy())
            else:
                # 到达叶子节点，记录路径
                chains.append(path)
        
        # 缓存任务数据
        self.tasks_cache = await self._get_project_tasks(project_id)
        
        dfs(task_id, [])
        return chains
    
    async def _can_task_start(self, task_id: int) -> bool:
        """检查任务是否可以开始"""
        task = await self._get_task_by_id(task_id)
        if not task or not task.dependency_tasks:
            return True
        
        # 检查所有依赖任务是否已完成
        result = await self.db.execute(
            select(Task.status).where(Task.id.in_(task.dependency_tasks))
        )
        
        for status in result.scalars():
            if status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    async def _get_blocking_dependencies(self, task_id: int) -> List[int]:
        """获取阻塞当前任务的依赖任务"""
        task = await self._get_task_by_id(task_id)
        if not task or not task.dependency_tasks:
            return []
        
        blocking_deps = []
        result = await self.db.execute(
            select(Task.id, Task.status).where(Task.id.in_(task.dependency_tasks))
        )
        
        for tid, status in result.fetchall():
            if status != TaskStatus.COMPLETED:
                blocking_deps.append(tid)
        
        return blocking_deps


# 依赖注入函数
async def get_task_dependency_service(db: AsyncSession = Depends(get_async_session)):
    """获取任务依赖服务实例"""
    return TaskDependencyService(db)