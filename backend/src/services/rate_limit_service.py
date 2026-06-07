"""
速率限制服务

提供高级的速率限制和滥用防护功能，包括：
- 分布式速率限制
- 智能滥用检测
- 动态限制调整
- IP黑名单管理
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Text, JSON, select, and_

from ..models.base import Base
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LimitType(Enum):
    """限制类型"""
    REQUEST = "request"      # 请求频率限制
    BANDWIDTH = "bandwidth"  # 带宽限制
    CONCURRENT = "concurrent" # 并发连接限制
    RESOURCE = "resource"    # 资源使用限制


class ActionType(Enum):
    """处理动作"""
    ALLOW = "allow"          # 允许
    THROTTLE = "throttle"    # 限流
    BLOCK = "block"          # 阻止
    CAPTCHA = "captcha"      # 验证码


@dataclass
class RateLimitRule:
    """速率限制规则"""
    name: str
    limit_type: LimitType
    max_requests: int
    window_seconds: int
    burst_limit: Optional[int] = None
    action: ActionType = ActionType.THROTTLE
    whitelist: Optional[List[str]] = None
    blacklist: Optional[List[str]] = None
    enabled: bool = True


@dataclass
class RateLimitResult:
    """速率限制结果"""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    action: ActionType = ActionType.ALLOW
    reason: Optional[str] = None


class IPBlacklist(Base):
    """IP黑名单模型"""
    __tablename__ = 'ip_blacklist'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, unique=True, comment='IP地址')
    reason = Column(String(200), comment='封禁原因')
    blocked_at = Column(DateTime, default=datetime.utcnow, comment='封禁时间')
    expires_at = Column(DateTime, comment='过期时间')
    is_permanent = Column(Boolean, default=False, comment='是否永久封禁')
    blocked_by = Column(Integer, comment='封禁操作人')
    attack_count = Column(Integer, default=0, comment='攻击次数')
    last_attack_at = Column(DateTime, comment='最后攻击时间')
    details = Column(JSON, comment='详细信息')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'reason': self.reason,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_permanent': self.is_permanent,
            'blocked_by': self.blocked_by,
            'attack_count': self.attack_count,
            'last_attack_at': self.last_attack_at.isoformat() if self.last_attack_at else None,
            'details': self.details
        }


class RateLimitLog(Base):
    """速率限制日志模型"""
    __tablename__ = 'rate_limit_logs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    identifier = Column(String(100), nullable=False, comment='标识符')
    rule_name = Column(String(50), nullable=False, comment='规则名称')
    action = Column(String(20), nullable=False, comment='执行动作')
    request_count = Column(Integer, comment='请求数量')
    window_start = Column(DateTime, comment='窗口开始时间')
    window_end = Column(DateTime, comment='窗口结束时间')
    user_agent = Column(String(500), comment='用户代理')
    endpoint = Column(String(200), comment='请求端点')
    details = Column(JSON, comment='详细信息')
    timestamp = Column(DateTime, default=datetime.utcnow, comment='记录时间')


class AdvancedRateLimitService:
    """高级速率限制服务"""
    
    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
        
        # 内存缓存（当Redis不可用时使用）
        self.memory_cache = defaultdict(deque)
        self.blocked_ips = {}
        
        # 预定义规则
        self.rules = {
            'api_default': RateLimitRule(
                name='api_default',
                limit_type=LimitType.REQUEST,
                max_requests=100,
                window_seconds=60,
                burst_limit=20
            ),
            'auth_login': RateLimitRule(
                name='auth_login',
                limit_type=LimitType.REQUEST,
                max_requests=5,
                window_seconds=300,  # 5分钟
                action=ActionType.BLOCK
            ),
            'password_reset': RateLimitRule(
                name='password_reset',
                limit_type=LimitType.REQUEST,
                max_requests=3,
                window_seconds=3600,  # 1小时
                action=ActionType.BLOCK
            ),
            'file_upload': RateLimitRule(
                name='file_upload',
                limit_type=LimitType.REQUEST,
                max_requests=10,
                window_seconds=60,
                burst_limit=5
            ),
            'project_create': RateLimitRule(
                name='project_create',
                limit_type=LimitType.REQUEST,
                max_requests=20,
                window_seconds=3600,  # 1小时
                action=ActionType.THROTTLE
            ),
            'bulk_operation': RateLimitRule(
                name='bulk_operation',
                limit_type=LimitType.REQUEST,
                max_requests=5,
                window_seconds=60,
                action=ActionType.THROTTLE
            ),
            'report_generation': RateLimitRule(
                name='report_generation',
                limit_type=LimitType.REQUEST,
                max_requests=10,
                window_seconds=300,  # 5分钟
                action=ActionType.THROTTLE
            ),
            'search_query': RateLimitRule(
                name='search_query',
                limit_type=LimitType.REQUEST,
                max_requests=50,
                window_seconds=60,
                burst_limit=10
            )
        }
    
    async def check_rate_limit(
        self,
        identifier: str,
        rule_name: str,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> RateLimitResult:
        """检查速率限制"""
        try:
            # 检查IP黑名单
            if await self._is_ip_blocked(identifier):
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=datetime.utcnow() + timedelta(hours=24),
                    action=ActionType.BLOCK,
                    reason="IP已被封禁"
                )
            
            # 获取规则
            rule = self.rules.get(rule_name)
            if not rule or not rule.enabled:
                return RateLimitResult(
                    allowed=True,
                    remaining=999,
                    reset_time=datetime.utcnow() + timedelta(seconds=60)
                )
            
            # 检查白名单
            if rule.whitelist and identifier in rule.whitelist:
                return RateLimitResult(
                    allowed=True,
                    remaining=999,
                    reset_time=datetime.utcnow() + timedelta(seconds=rule.window_seconds)
                )
            
            # 检查黑名单
            if rule.blacklist and identifier in rule.blacklist:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=datetime.utcnow() + timedelta(seconds=rule.window_seconds),
                    action=ActionType.BLOCK,
                    reason="在黑名单中"
                )
            
            # 执行速率限制检查
            if self.redis:
                result = await self._check_redis_rate_limit(identifier, rule)
            else:
                result = await self._check_memory_rate_limit(identifier, rule)
            
            # 记录日志
            await self._log_rate_limit_check(
                identifier, rule_name, result, user_agent, endpoint, additional_info
            )
            
            # 检测滥用行为
            if not result.allowed:
                await self._detect_abuse(identifier, rule_name, user_agent, endpoint)
            
            return result
            
        except Exception as e:
            logger.error(f"速率限制检查失败: {str(e)}")
            # 出错时允许请求，但记录错误
            return RateLimitResult(
                allowed=True,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=60),
                reason=f"检查失败: {str(e)}"
            )
    
    async def _check_redis_rate_limit(self, identifier: str, rule: RateLimitRule) -> RateLimitResult:
        """使用Redis检查速率限制"""
        key = f"rate_limit:{rule.name}:{identifier}"
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=rule.window_seconds)
        
        # 使用Redis的有序集合实现滑动窗口
        pipe = self.redis.pipeline()
        
        # 清理过期记录
        pipe.zremrangebyscore(key, 0, window_start.timestamp())
        
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        
        # 添加当前请求
        pipe.zadd(key, {str(now.timestamp()): now.timestamp()})
        
        # 设置过期时间
        pipe.expire(key, rule.window_seconds + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # 检查是否超过限制
        if current_count >= rule.max_requests:
            # 检查突发限制
            if rule.burst_limit:
                burst_key = f"burst:{rule.name}:{identifier}"
                burst_count = await self.redis.get(burst_key)
                
                if burst_count is None:
                    await self.redis.setex(burst_key, 60, 1)  # 1分钟突发窗口
                    burst_count = 1
                else:
                    burst_count = int(burst_count)
                    if burst_count < rule.burst_limit:
                        await self.redis.incr(burst_key)
                        return RateLimitResult(
                            allowed=True,
                            remaining=rule.burst_limit - burst_count - 1,
                            reset_time=now + timedelta(seconds=60),
                            action=ActionType.ALLOW,
                            reason="突发限制内"
                        )
            
            # 计算重试时间
            oldest_request_key = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_request_key:
                oldest_time = datetime.fromtimestamp(oldest_request_key[0][1])
                retry_after = int((oldest_time + timedelta(seconds=rule.window_seconds) - now).total_seconds())
            else:
                retry_after = rule.window_seconds
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + timedelta(seconds=retry_after),
                retry_after=retry_after,
                action=rule.action,
                reason="超过速率限制"
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=rule.max_requests - current_count - 1,
            reset_time=now + timedelta(seconds=rule.window_seconds),
            action=ActionType.ALLOW
        )
    
    async def _check_memory_rate_limit(self, identifier: str, rule: RateLimitRule) -> RateLimitResult:
        """使用内存检查速率限制（Redis不可用时的备选方案）"""
        key = f"{rule.name}:{identifier}"
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=rule.window_seconds)
        
        # 获取请求记录
        requests = self.memory_cache[key]
        
        # 清理过期请求
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # 检查是否超过限制
        if len(requests) >= rule.max_requests:
            oldest_time = requests[0]
            retry_after = int((oldest_time + timedelta(seconds=rule.window_seconds) - now).total_seconds())
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=oldest_time + timedelta(seconds=rule.window_seconds),
                retry_after=retry_after,
                action=rule.action,
                reason="超过速率限制"
            )
        
        # 添加当前请求
        requests.append(now)
        
        return RateLimitResult(
            allowed=True,
            remaining=rule.max_requests - len(requests),
            reset_time=now + timedelta(seconds=rule.window_seconds),
            action=ActionType.ALLOW
        )
    
    async def _is_ip_blocked(self, ip_address: str) -> bool:
        """检查IP是否被封禁"""
        query = select(IPBlacklist).where(
            and_(
                IPBlacklist.ip_address == ip_address,
                or_(
                    IPBlacklist.is_permanent == True,
                    IPBlacklist.expires_at > datetime.utcnow()
                )
            )
        )
        
        result = await self.db.execute(query)
        blocked_ip = result.scalar_one_or_none()
        
        return blocked_ip is not None
    
    async def _detect_abuse(
        self,
        identifier: str,
        rule_name: str,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """检测滥用行为"""
        # 统计最近的违规次数
        recent_violations = await self._count_recent_violations(identifier)
        
        # 如果违规次数过多，考虑封禁
        if recent_violations >= 10:  # 10次违规
            await self._block_ip(
                identifier,
                reason=f"频繁违规 ({recent_violations} 次)",
                duration_hours=24,
                details={
                    'rule_name': rule_name,
                    'user_agent': user_agent,
                    'endpoint': endpoint,
                    'violation_count': recent_violations
                }
            )
            
            logger.warning(f"IP {identifier} 因频繁违规被封禁")
    
    async def _count_recent_violations(self, identifier: str) -> int:
        """统计最近的违规次数"""
        since = datetime.utcnow() - timedelta(hours=1)
        
        query = select(func.count(RateLimitLog.id)).where(
            and_(
                RateLimitLog.identifier == identifier,
                RateLimitLog.action.in_(['BLOCK', 'THROTTLE']),
                RateLimitLog.timestamp >= since
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _block_ip(
        self,
        ip_address: str,
        reason: str,
        duration_hours: Optional[int] = None,
        is_permanent: bool = False,
        blocked_by: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> IPBlacklist:
        """封禁IP地址"""
        # 检查是否已存在
        existing_query = select(IPBlacklist).where(IPBlacklist.ip_address == ip_address)
        existing_result = await self.db.execute(existing_query)
        existing_block = existing_result.scalar_one_or_none()
        
        if existing_block:
            # 更新现有记录
            existing_block.reason = reason
            existing_block.attack_count += 1
            existing_block.last_attack_at = datetime.utcnow()
            existing_block.details = details
            
            if duration_hours and not existing_block.is_permanent:
                existing_block.expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            
            if is_permanent:
                existing_block.is_permanent = True
                existing_block.expires_at = None
            
            blocked_ip = existing_block
        else:
            # 创建新记录
            blocked_ip = IPBlacklist(
                ip_address=ip_address,
                reason=reason,
                blocked_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=duration_hours) if duration_hours else None,
                is_permanent=is_permanent,
                blocked_by=blocked_by,
                attack_count=1,
                last_attack_at=datetime.utcnow(),
                details=details
            )
            self.db.add(blocked_ip)
        
        await self.db.commit()
        return blocked_ip
    
    async def _log_rate_limit_check(
        self,
        identifier: str,
        rule_name: str,
        result: RateLimitResult,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        """记录速率限制检查日志"""
        # 只记录被限制的请求，避免日志过多
        if not result.allowed:
            log_entry = RateLimitLog(
                identifier=identifier,
                rule_name=rule_name,
                action=result.action.value,
                request_count=0,  # 这里可以从结果中获取
                window_start=datetime.utcnow() - timedelta(seconds=60),
                window_end=datetime.utcnow(),
                user_agent=user_agent,
                endpoint=endpoint,
                details={
                    'remaining': result.remaining,
                    'retry_after': result.retry_after,
                    'reason': result.reason,
                    'additional_info': additional_info
                }
            )
            
            self.db.add(log_entry)
            await self.db.commit()
    
    async def get_blocked_ips(
        self,
        limit: int = 100,
        offset: int = 0,
        include_expired: bool = False
    ) -> List[IPBlacklist]:
        """获取被封禁的IP列表"""
        query = select(IPBlacklist)
        
        if not include_expired:
            query = query.where(
                or_(
                    IPBlacklist.is_permanent == True,
                    IPBlacklist.expires_at > datetime.utcnow()
                )
            )
        
        query = query.order_by(IPBlacklist.blocked_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def unblock_ip(self, ip_address: str) -> bool:
        """解封IP地址"""
        query = select(IPBlacklist).where(IPBlacklist.ip_address == ip_address)
        result = await self.db.execute(query)
        blocked_ip = result.scalar_one_or_none()
        
        if blocked_ip:
            await self.db.delete(blocked_ip)
            await self.db.commit()
            logger.info(f"IP {ip_address} 已解封")
            return True
        
        return False
    
    async def add_rule(self, rule: RateLimitRule):
        """添加速率限制规则"""
        self.rules[rule.name] = rule
        logger.info(f"添加速率限制规则: {rule.name}")
    
    async def remove_rule(self, rule_name: str) -> bool:
        """移除速率限制规则"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"移除速率限制规则: {rule_name}")
            return True
        return False
    
    async def get_rate_limit_stats(self) -> Dict[str, Any]:
        """获取速率限制统计信息"""
        # 最近24小时的统计
        since = datetime.utcnow() - timedelta(hours=24)
        
        # 总限制次数
        total_query = select(func.count(RateLimitLog.id)).where(
            RateLimitLog.timestamp >= since
        )
        total_result = await self.db.execute(total_query)
        total_limits = total_result.scalar() or 0
        
        # 按规则统计
        rule_query = select(
            RateLimitLog.rule_name,
            func.count(RateLimitLog.id).label('count')
        ).where(
            RateLimitLog.timestamp >= since
        ).group_by(RateLimitLog.rule_name)
        
        rule_result = await self.db.execute(rule_query)
        rule_stats = {row.rule_name: row.count for row in rule_result}
        
        # 被封禁的IP数量
        blocked_query = select(func.count(IPBlacklist.id)).where(
            or_(
                IPBlacklist.is_permanent == True,
                IPBlacklist.expires_at > datetime.utcnow()
            )
        )
        blocked_result = await self.db.execute(blocked_query)
        blocked_ips = blocked_result.scalar() or 0
        
        return {
            'total_limits_24h': total_limits,
            'rule_statistics': rule_stats,
            'blocked_ips': blocked_ips,
            'active_rules': len(self.rules),
            'rules': {name: rule.enabled for name, rule in self.rules.items()}
        }