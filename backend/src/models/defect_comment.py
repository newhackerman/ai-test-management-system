"""
缺陷评论数据模型

本模块定义了缺陷评论相关的数据库模型
"""
from sqlalchemy import BigInteger, Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base

class DefectComment(Base):
    """缺陷评论模型"""
    __tablename__ = "defect_comments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    defect_id = Column(BigInteger, ForeignKey("defects.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    defect = relationship("Defect", back_populates="comments")
    user = relationship("User")
    
    def __repr__(self):
        return f"<DefectComment(id={self.id}, defect_id={self.defect_id}, user_id={self.user_id})>"
