"""
核心模块 - 包含配置、数据库连接、Redis连接等核心功能
"""
from .config import settings
from .database import get_db, Base
from .redis import redis_service, RedisService

__all__ = ["settings", "get_db", "Base", "redis_service", "RedisService"]