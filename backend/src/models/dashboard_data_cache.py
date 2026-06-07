"""
仪表板数据缓存模型

实现DashboardDataCache SQLAlchemy模型，支持数据缓存和性能优化
"""

from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON, Integer, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Dict, List, Any, Optional
import hashlib
import json

Base = declarative_base()

class CacheDataType(PyEnum):
    """缓存数据类型枚举"""
    PROJECT_OVERVIEW = "PROJECT_OVERVIEW"  # 项目概览数据
    REQUIREMENT_METRICS = "REQUIREMENT_METRICS"  # 需求指标数据
    TEST_METRICS = "TEST_METRICS"  # 测试指标数据
    SYSTEM_METRICS = "SYSTEM_METRICS"  # 系统指标数据
    USER_ACTIVITY = "USER_ACTIVITY"  # 用户活动数据
    TEAM_PERFORMANCE = "TEAM_PERFORMANCE"  # 团队绩效数据
    CHART_DATA = "CHART_DATA"  # 图表数据
    WIDGET_DATA = "WIDGET_DATA"  # 组件数据
    AGGREGATED_DATA = "AGGREGATED_DATA"  # 聚合数据
    REAL_TIME_DATA = "REAL_TIME_DATA"  # 实时数据

class CacheStatus(PyEnum):
    """缓存状态枚举"""
    ACTIVE = "ACTIVE"  # 活跃状态
    EXPIRED = "EXPIRED"  # 已过期
    INVALID = "INVALID"  # 无效状态
    REFRESHING = "REFRESHING"  # 刷新中

class DashboardDataCache(Base):
    """
    仪表板数据缓存表
    
    存储仪表板组件的数据缓存，提升查询性能
    """
    __tablename__ = 'dashboard_data_cache'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='缓存ID')
    cache_key = Column(String(255), unique=True, nullable=False, comment='缓存键')
    data_type = Column(Enum(CacheDataType), nullable=False, comment='数据类型')
    
    # 数据内容
    data_content = Column(JSON, nullable=False, comment='数据内容JSON')
    data_size = Column(Integer, default=0, comment='数据大小(字节)')
    data_hash = Column(String(64), comment='数据哈希值')
    
    # 关联信息
    project_id = Column(BigInteger, ForeignKey('projects.id', ondelete='CASCADE'), comment='关联项目ID')
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), comment='关联用户ID')
    widget_type = Column(String(50), comment='组件类型')
    
    # 缓存策略
    ttl_seconds = Column(Integer, default=300, comment='生存时间(秒)')
    expires_at = Column(DateTime, nullable=False, comment='过期时间')
    refresh_interval = Column(Integer, default=60, comment='刷新间隔(秒)')
    
    # 缓存状态
    status = Column(Enum(CacheStatus), default=CacheStatus.ACTIVE, comment='缓存状态')
    hit_count = Column(Integer, default=0, comment='命中次数')
    last_hit_at = Column(DateTime, comment='最后命中时间')
    
    # 性能指标
    generation_time_ms = Column(Integer, comment='生成耗时(毫秒)')
    compression_ratio = Column(Integer, comment='压缩比例')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_data_type', 'data_type'),
        Index('idx_project_id', 'project_id'),
        Index('idx_user_id', 'user_id'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_status', 'status'),
        Index('idx_widget_type', 'widget_type'),
        Index('idx_project_type', 'project_id', 'data_type'),
        Index('idx_user_type', 'user_id', 'data_type'),
        {'comment': '仪表板数据缓存表'}
    )
    
    def __repr__(self):
        return f"<DashboardDataCache(id={self.id}, key='{self.cache_key}', type='{self.data_type.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'cache_key': self.cache_key,
            'data_type': self.data_type.value if self.data_type else None,
            'data_content': self.data_content,
            'data_size': self.data_size,
            'data_hash': self.data_hash,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'widget_type': self.widget_type,
            'ttl_seconds': self.ttl_seconds,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'refresh_interval': self.refresh_interval,
            'status': self.status.value if self.status else None,
            'hit_count': self.hit_count,
            'last_hit_at': self.last_hit_at.isoformat() if self.last_hit_at else None,
            'generation_time_ms': self.generation_time_ms,
            'compression_ratio': self.compression_ratio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def generate_cache_key(
        cls, 
        data_type: CacheDataType, 
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        widget_type: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成缓存键"""
        key_parts = [data_type.value]
        
        if project_id:
            key_parts.append(f"project:{project_id}")
        
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        if widget_type:
            key_parts.append(f"widget:{widget_type}")
        
        # 添加额外参数
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")
        
        cache_key = ":".join(key_parts)
        
        # 如果键太长，使用哈希
        if len(cache_key) > 200:
            cache_key = f"{data_type.value}:{hashlib.md5(cache_key.encode()).hexdigest()}"
        
        return cache_key
    
    @classmethod
    def create_cache_entry(
        cls,
        data_type: CacheDataType,
        data_content: Dict[str, Any],
        ttl_seconds: int = 300,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        widget_type: Optional[str] = None,
        **kwargs
    ) -> 'DashboardDataCache':
        """创建缓存条目"""
        cache_key = cls.generate_cache_key(
            data_type, project_id, user_id, widget_type, **kwargs
        )
        
        # 计算数据哈希和大小
        data_json = json.dumps(data_content, sort_keys=True, ensure_ascii=False)
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()
        data_size = len(data_json.encode('utf-8'))
        
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        return cls(
            cache_key=cache_key,
            data_type=data_type,
            data_content=data_content,
            data_size=data_size,
            data_hash=data_hash,
            project_id=project_id,
            user_id=user_id,
            widget_type=widget_type,
            ttl_seconds=ttl_seconds,
            expires_at=expires_at,
            status=CacheStatus.ACTIVE
        )
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查缓存是否有效"""
        return (self.status == CacheStatus.ACTIVE and 
                not self.is_expired() and 
                self.data_content is not None)
    
    def hit(self):
        """记录缓存命中"""
        self.hit_count += 1
        self.last_hit_at = datetime.utcnow()
    
    def refresh(self, new_data: Dict[str, Any], generation_time_ms: Optional[int] = None):
        """刷新缓存数据"""
        # 计算新数据的哈希和大小
        data_json = json.dumps(new_data, sort_keys=True, ensure_ascii=False)
        new_hash = hashlib.sha256(data_json.encode()).hexdigest()
        new_size = len(data_json.encode('utf-8'))
        
        # 检查数据是否有变化
        if new_hash != self.data_hash:
            self.data_content = new_data
            self.data_hash = new_hash
            self.data_size = new_size
            self.updated_at = datetime.utcnow()
        
        # 更新过期时间
        self.expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        self.status = CacheStatus.ACTIVE
        
        if generation_time_ms:
            self.generation_time_ms = generation_time_ms
    
    def invalidate(self):
        """使缓存失效"""
        self.status = CacheStatus.INVALID
        self.updated_at = datetime.utcnow()
    
    def extend_ttl(self, additional_seconds: int):
        """延长缓存生存时间"""
        self.expires_at = self.expires_at + timedelta(seconds=additional_seconds)
        self.ttl_seconds += additional_seconds
    
    def get_cache_efficiency(self) -> Dict[str, Any]:
        """获取缓存效率统计"""
        age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        
        return {
            'hit_count': self.hit_count,
            'age_seconds': age_seconds,
            'hit_rate_per_hour': (self.hit_count / (age_seconds / 3600)) if age_seconds > 0 else 0,
            'data_size_kb': self.data_size / 1024 if self.data_size else 0,
            'generation_time_ms': self.generation_time_ms,
            'compression_ratio': self.compression_ratio,
            'is_expired': self.is_expired(),
            'is_valid': self.is_valid()
        }


class CacheStatistics(Base):
    """
    缓存统计表
    
    记录缓存性能和使用统计
    """
    __tablename__ = 'cache_statistics'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='统计ID')
    date = Column(DateTime, nullable=False, comment='统计日期')
    data_type = Column(Enum(CacheDataType), comment='数据类型')
    
    # 统计指标
    total_requests = Column(Integer, default=0, comment='总请求数')
    cache_hits = Column(Integer, default=0, comment='缓存命中数')
    cache_misses = Column(Integer, default=0, comment='缓存未命中数')
    hit_rate = Column(Integer, default=0, comment='命中率(百分比)')
    
    # 性能指标
    avg_response_time_ms = Column(Integer, comment='平均响应时间(毫秒)')
    total_data_size_mb = Column(Integer, comment='总数据大小(MB)')
    cache_count = Column(Integer, default=0, comment='缓存条目数')
    
    # 清理统计
    expired_count = Column(Integer, default=0, comment='过期清理数')
    invalid_count = Column(Integer, default=0, comment='无效清理数')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_date', 'date'),
        Index('idx_data_type', 'data_type'),
        Index('idx_date_type', 'date', 'data_type'),
        {'comment': '缓存统计表'}
    )
    
    def __repr__(self):
        return f"<CacheStatistics(id={self.id}, date='{self.date}', type='{self.data_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'data_type': self.data_type.value if self.data_type else None,
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.hit_rate,
            'avg_response_time_ms': self.avg_response_time_ms,
            'total_data_size_mb': self.total_data_size_mb,
            'cache_count': self.cache_count,
            'expired_count': self.expired_count,
            'invalid_count': self.invalid_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def calculate_hit_rate(self):
        """计算命中率"""
        if self.total_requests > 0:
            self.hit_rate = int((self.cache_hits / self.total_requests) * 100)
        else:
            self.hit_rate = 0
    
    @classmethod
    def create_daily_stats(cls, date: datetime, data_type: Optional[CacheDataType] = None) -> 'CacheStatistics':
        """创建日统计记录"""
        return cls(
            date=date.replace(hour=0, minute=0, second=0, microsecond=0),
            data_type=data_type,
            total_requests=0,
            cache_hits=0,
            cache_misses=0,
            hit_rate=0
        )