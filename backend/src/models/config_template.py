"""
配置模板模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, BigInteger, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
import enum
from .base import BaseModel


class TemplateType(enum.Enum):
    """模板类型枚举"""
    SYSTEM = "SYSTEM"       # 系统模板
    USER = "USER"           # 用户模板
    PROJECT = "PROJECT"     # 项目配置


class TemplateCategory(enum.Enum):
    """模板分类枚举"""
    DATABASE = "DATABASE"           # 数据库配置
    CACHE = "CACHE"                # 缓存配置
    SECURITY = "SECURITY"          # 安全配置
    API = "API"                    # API配置
    MONITORING = "MONITORING"      # 监控配置
    BUSINESS = "BUSINESS"          # 业务配置
    NOTIFICATION = "NOTIFICATION"  # 通知配置
    OTHER = "OTHER"               # 其他


class ConfigTemplate(BaseModel):
    """配置模板表"""
    __tablename__ = 'sys_config_template'
    
    template_name = Column(String(100), nullable=False, comment='模板名称')
    template_code = Column(String(50), nullable=False, unique=True, comment='模板代码')
    description = Column(Text, comment='模板描述')
    
    # 模板分类
    template_type = Column(SQLEnum(TemplateType), default=TemplateType.USER, comment='模板类型')
    category = Column(SQLEnum(TemplateCategory), default=TemplateCategory.OTHER, comment='模板分类')
    
    # 模板内容
    template_config = Column(JSON, nullable=False, comment='模板配置内容')
    
    # 示例配置内容：
    # {
    #   "configs": [
    #     {
    #       "config_key": "database.host",
    #       "config_type": "STRING",
    #       "default_value": "localhost",
    #       "description": "数据库主机地址",
    #       "validation_rule": {"regex": "^[a-zA-Z0-9.-]+$"},
    #       "is_required": true
    #     }
    #   ],
    #   "groups": [
    #     {
    #       "group_name": "数据库配置",
    #       "group_code": "database",
    #       "description": "数据库相关配置"
    #     }
    #   ]
    # }
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment='使用次数')
    
    # 模板标签
    tags = Column(JSON, comment='模板标签')
    
    # 版本信息
    version = Column(String(20), default='1.0.0', comment='模板版本')
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    is_public = Column(Boolean, default=False, nullable=False, comment='是否公开')
    
    def __repr__(self):
        return f"<ConfigTemplate(name={self.template_name}, code={self.template_code}, type={self.template_type})>"


print("✅ 配置模板模型已创建完成")
