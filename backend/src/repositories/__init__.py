"""
仓储层模块

本模块实现了仓储模式，提供数据访问抽象层，包括：
- 基础仓储接口和实现
- 需求管理仓储
- 其他业务实体仓储
"""

from .base_repository import BaseRepository, IBaseRepository
from .requirement_repository import RequirementRepository, IRequirementRepository

__all__ = [
    "BaseRepository",
    "IBaseRepository", 
    "RequirementRepository",
    "IRequirementRepository"
]