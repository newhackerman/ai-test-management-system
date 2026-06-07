"""
测试管理模块Redis缓存工具

本模块定义了测试管理相关的缓存键命名规范、TTL策略和缓存操作工具。
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class TestCacheKeys:
    """测试管理模块缓存键命名规范"""
    
    # 测试计划缓存
    TEST_PLAN_INFO = "test_plan:info:{plan_id}"
    TEST_PLAN_CASES = "test_plan:cases:{plan_id}"
    TEST_PLAN_PROGRESS = "test_plan:progress:{plan_id}"
    TEST_PLAN_STATISTICS = "test_plan:stats:{plan_id}"
    
    # 测试用例缓存
    TEST_CASE_INFO = "test_case:info:{case_id}"
    TEST_CASE_EXECUTIONS = "test_case:executions:{case_id}"
    TEST_CASE_HISTORY = "test_case:history:{case_id}"
    
    # 测试执行缓存
    TEST_EXECUTION_ACTIVE = "test_execution:active:{user_id}"
    TEST_EXECUTION_RESULTS = "test_execution:results:{execution_id}"
    TEST_EXECUTION_LOGS = "test_execution:logs:{execution_id}"
    
    # 缺陷缓存
    DEFECT_INFO = "defect:info:{defect_id}"
    DEFECT_LIST_USER = "defect:list:{assignee_id}"
    DEFECT_LIST_PROJECT = "defect:list:project:{project_id}"
    
    # 项目测试缓存
    PROJECT_TEST_STATS = "project:test_stats:{project_id}"
    PROJECT_TEST_PLANS = "project:test_plans:{project_id}"
    PROJECT_TEST_COVERAGE = "project:test_coverage:{project_id}"
    
    # 统计缓存
    STATS_TEST_DAILY = "stats:test:daily:{date}"
    STATS_TEST_WEEKLY = "stats:test:weekly:{week}"
    STATS_TEST_MONTHLY = "stats:test:monthly:{month}"
    STATS_DEFECT_TRENDS = "stats:defect:trends:{project_id}"
    
    # 报告缓存
    TEST_REPORT_INFO = "test_report:info:{report_id}"
    TEST_REPORT_DATA = "test_report:data:{report_id}"
    
    # 用户相关缓存
    USER_TEST_DASHBOARD = "user:test_dashboard:{user_id}"
    USER_TEST_ASSIGNMENTS = "user:test_assignments:{user_id}"


class TestCacheTTL:
    """测试管理模块缓存TTL策略（秒）"""
    
    # 测试计划相关
    TEST_PLAN_INFO = 7200  # 2小时
    TEST_PLAN_PROGRESS = 1800  # 30分钟
    TEST_PLAN_STATISTICS = 3600  # 1小时
    
    # 测试用例相关
    TEST_CASE_INFO = 3600  # 1小时
    TEST_CASE_EXECUTIONS = 1800  # 30分钟
    
    # 测试执行相关
    TEST_EXECUTION_ACTIVE = 1800  # 30分钟
    TEST_EXECUTION_RESULTS = 3600  # 1小时
    
    # 缺陷相关
    DEFECT_INFO = 3600  # 1小时
    DEFECT_LIST = 1800  # 30分钟
    
    # 项目统计
    PROJECT_STATS = 3600  # 1小时
    
    # 统计数据
    STATS_DAILY = 86400  # 24小时
    STATS_WEEKLY = 604800  # 7天
    STATS_MONTHLY = 2592000  # 30天
    
    # 报告相关
    TEST_REPORT = 7200  # 2小时
    
    # 用户相关
    USER_DASHBOARD = 1800  # 30分钟


class TestCacheManager:
    """测试管理模块缓存管理器"""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self.prefix = "testmgr:"
    
    def _get_key(self, key_template: str, **kwargs) -> str:
        """生成完整的缓存键"""
        key = key_template.format(**kwargs)
        return f"{self.prefix}{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """序列化值"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value)
    
    def _deserialize_value(self, value: str) -> Any:
        """反序列化值"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def set(self, key_template: str, value: Any, ttl: int = None, **kwargs) -> bool:
        """设置缓存"""
        if self.redis is None:
            return False
        try:
            key = self._get_key(key_template, **kwargs)
            serialized_value = self._serialize_value(value)
            
            if ttl:
                return self.redis.setex(key, ttl, serialized_value)
            else:
                return self.redis.set(key, serialized_value)
        except RedisError as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def get(self, key_template: str, **kwargs) -> Any:
        """获取缓存"""
        if self.redis is None:
            return None
        try:
            key = self._get_key(key_template, **kwargs)
            value = self.redis.get(key)
            if value:
                return self._deserialize_value(value.decode('utf-8'))
            return None
        except RedisError as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def delete(self, key_template: str, **kwargs) -> bool:
        """删除缓存"""
        if self.redis is None:
            return False
        try:
            key = self._get_key(key_template, **kwargs)
            return bool(self.redis.delete(key))
        except RedisError as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def exists(self, key_template: str, **kwargs) -> bool:
        """检查缓存是否存在"""
        if self.redis is None:
            return False
        try:
            key = self._get_key(key_template, **kwargs)
            return bool(self.redis.exists(key))
        except RedisError as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    def expire(self, key_template: str, ttl: int, **kwargs) -> bool:
        """设置缓存过期时间"""
        if self.redis is None:
            return False
        try:
            key = self._get_key(key_template, **kwargs)
            return bool(self.redis.expire(key, ttl))
        except RedisError as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    def increment(self, key_template: str, amount: int = 1, **kwargs) -> Optional[int]:
        """递增缓存值"""
        if self.redis is None:
            return None
        try:
            key = self._get_key(key_template, **kwargs)
            return self.redis.incr(key, amount)
        except RedisError as e:
            logger.error(f"Redis incr error: {e}")
            return None
    
    def hash_set(self, key_template: str, field: str, value: Any, **kwargs) -> bool:
        """设置哈希字段"""
        try:
            key = self._get_key(key_template, **kwargs)
            serialized_value = self._serialize_value(value)
            return bool(self.redis.hset(key, field, serialized_value))
        except RedisError as e:
            logger.error(f"Redis hset error: {e}")
            return False
    
    def hash_get(self, key_template: str, field: str, **kwargs) -> Any:
        """获取哈希字段"""
        try:
            key = self._get_key(key_template, **kwargs)
            value = self.redis.hget(key, field)
            if value:
                return self._deserialize_value(value.decode('utf-8'))
            return None
        except RedisError as e:
            logger.error(f"Redis hget error: {e}")
            return None
    
    def hash_get_all(self, key_template: str, **kwargs) -> Dict[str, Any]:
        """获取所有哈希字段"""
        try:
            key = self._get_key(key_template, **kwargs)
            hash_data = self.redis.hgetall(key)
            result = {}
            for field, value in hash_data.items():
                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                result[field_str] = self._deserialize_value(value_str)
            return result
        except RedisError as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}
    
    def list_push(self, key_template: str, value: Any, **kwargs) -> Optional[int]:
        """向列表推入值"""
        try:
            key = self._get_key(key_template, **kwargs)
            serialized_value = self._serialize_value(value)
            return self.redis.lpush(key, serialized_value)
        except RedisError as e:
            logger.error(f"Redis lpush error: {e}")
            return None
    
    def list_pop(self, key_template: str, **kwargs) -> Any:
        """从列表弹出值"""
        try:
            key = self._get_key(key_template, **kwargs)
            value = self.redis.rpop(key)
            if value:
                return self._deserialize_value(value.decode('utf-8'))
            return None
        except RedisError as e:
            logger.error(f"Redis rpop error: {e}")
            return None
    
    def list_range(self, key_template: str, start: int = 0, end: int = -1, **kwargs) -> List[Any]:
        """获取列表范围"""
        try:
            key = self._get_key(key_template, **kwargs)
            values = self.redis.lrange(key, start, end)
            return [self._deserialize_value(v.decode('utf-8')) for v in values]
        except RedisError as e:
            logger.error(f"Redis lrange error: {e}")
            return []
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有键"""
        try:
            full_pattern = f"{self.prefix}{pattern}"
            keys = self.redis.keys(full_pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0

    async def get_test_case(self, case_id: int) -> None:
        return None

    async def set_test_case(self, case_id: int, test_case: Any) -> bool:
        return False

    async def delete_test_case(self, case_id: int) -> bool:
        return self.delete(TestCacheKeys.TEST_CASE_INFO, case_id=case_id)

    async def delete_plan_cases(self, plan_id: int) -> bool:
        return self.delete(TestCacheKeys.TEST_PLAN_CASES, plan_id=plan_id)


class TestCacheService:
    """测试管理缓存服务"""
    
    def __init__(self, cache_manager: TestCacheManager):
        self.cache = cache_manager
    
    # 测试计划缓存操作
    def cache_test_plan_info(self, plan_id: int, plan_data: Dict[str, Any]) -> bool:
        """缓存测试计划信息"""
        return self.cache.set(
            TestCacheKeys.TEST_PLAN_INFO,
            plan_data,
            TestCacheTTL.TEST_PLAN_INFO,
            plan_id=plan_id
        )
    
    def get_test_plan_info(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """获取测试计划信息"""
        return self.cache.get(TestCacheKeys.TEST_PLAN_INFO, plan_id=plan_id)
    
    def cache_test_plan_progress(self, plan_id: int, progress_data: Dict[str, Any]) -> bool:
        """缓存测试计划进度"""
        return self.cache.set(
            TestCacheKeys.TEST_PLAN_PROGRESS,
            progress_data,
            TestCacheTTL.TEST_PLAN_PROGRESS,
            plan_id=plan_id
        )
    
    def get_test_plan_progress(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """获取测试计划进度"""
        return self.cache.get(TestCacheKeys.TEST_PLAN_PROGRESS, plan_id=plan_id)
    
    # 测试用例缓存操作
    def cache_test_case_info(self, case_id: int, case_data: Dict[str, Any]) -> bool:
        """缓存测试用例信息"""
        return self.cache.set(
            TestCacheKeys.TEST_CASE_INFO,
            case_data,
            TestCacheTTL.TEST_CASE_INFO,
            case_id=case_id
        )
    
    def get_test_case_info(self, case_id: int) -> Optional[Dict[str, Any]]:
        """获取测试用例信息"""
        return self.cache.get(TestCacheKeys.TEST_CASE_INFO, case_id=case_id)
    
    # 测试执行缓存操作
    def cache_active_execution(self, user_id: int, execution_data: Dict[str, Any]) -> bool:
        """缓存用户当前执行的测试"""
        return self.cache.set(
            TestCacheKeys.TEST_EXECUTION_ACTIVE,
            execution_data,
            TestCacheTTL.TEST_EXECUTION_ACTIVE,
            user_id=user_id
        )
    
    def get_active_execution(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户当前执行的测试"""
        return self.cache.get(TestCacheKeys.TEST_EXECUTION_ACTIVE, user_id=user_id)
    
    # 缺陷缓存操作
    def cache_defect_info(self, defect_id: int, defect_data: Dict[str, Any]) -> bool:
        """缓存缺陷信息"""
        return self.cache.set(
            TestCacheKeys.DEFECT_INFO,
            defect_data,
            TestCacheTTL.DEFECT_INFO,
            defect_id=defect_id
        )
    
    def get_defect_info(self, defect_id: int) -> Optional[Dict[str, Any]]:
        """获取缺陷信息"""
        return self.cache.get(TestCacheKeys.DEFECT_INFO, defect_id=defect_id)
    
    # 项目统计缓存操作
    def cache_project_test_stats(self, project_id: int, stats_data: Dict[str, Any]) -> bool:
        """缓存项目测试统计"""
        return self.cache.set(
            TestCacheKeys.PROJECT_TEST_STATS,
            stats_data,
            TestCacheTTL.PROJECT_STATS,
            project_id=project_id
        )
    
    def get_project_test_stats(self, project_id: int) -> Optional[Dict[str, Any]]:
        """获取项目测试统计"""
        return self.cache.get(TestCacheKeys.PROJECT_TEST_STATS, project_id=project_id)
    
    # 统计数据缓存操作
    def cache_daily_stats(self, date: str, stats_data: Dict[str, Any]) -> bool:
        """缓存日统计数据"""
        return self.cache.set(
            TestCacheKeys.STATS_TEST_DAILY,
            stats_data,
            TestCacheTTL.STATS_DAILY,
            date=date
        )
    
    def get_daily_stats(self, date: str) -> Optional[Dict[str, Any]]:
        """获取日统计数据"""
        return self.cache.get(TestCacheKeys.STATS_TEST_DAILY, date=date)
    
    # 缓存失效操作
    def invalidate_test_plan_cache(self, plan_id: int) -> None:
        """使测试计划相关缓存失效"""
        self.cache.delete(TestCacheKeys.TEST_PLAN_INFO, plan_id=plan_id)
        self.cache.delete(TestCacheKeys.TEST_PLAN_PROGRESS, plan_id=plan_id)
        self.cache.delete(TestCacheKeys.TEST_PLAN_STATISTICS, plan_id=plan_id)
    
    def invalidate_test_case_cache(self, case_id: int) -> None:
        """使测试用例相关缓存失效"""
        self.cache.delete(TestCacheKeys.TEST_CASE_INFO, case_id=case_id)
        self.cache.delete(TestCacheKeys.TEST_CASE_EXECUTIONS, case_id=case_id)
    
    def invalidate_project_cache(self, project_id: int) -> None:
        """使项目相关缓存失效"""
        self.cache.delete(TestCacheKeys.PROJECT_TEST_STATS, project_id=project_id)
        self.cache.delete(TestCacheKeys.PROJECT_TEST_PLANS, project_id=project_id)
        self.cache.delete(TestCacheKeys.PROJECT_TEST_COVERAGE, project_id=project_id)
    
    # 缓存性能监控
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            info = self.cache.redis.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except RedisError as e:
            logger.error(f"Redis info error: {e}")
            return {}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """计算缓存命中率"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
