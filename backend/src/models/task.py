"""
任务管理模型

用于项目任务管理和会议行动项目跟踪
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from src.models.base import Base


class TaskStatus(PyEnum):
    """任务状态枚举"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class TaskPriority(PyEnum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """任务模型"""
    
    __tablename__ = 'tasks'
    
    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 关联信息
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, index=True)
    meeting_id = Column(BigInteger, ForeignKey('meetings.id'), nullable=True, index=True)  # 来源会议
    assignee_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, index=True)
    creator_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True)
    
    # 任务属性
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    
    # 时间管理
    due_date = Column(DateTime, nullable=True)
    start_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    project = relationship("Project", back_populates="tasks")
    meeting = relationship("Meeting", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'project_id': self.project_id,
            'meeting_id': self.meeting_id,
            'assignee_id': self.assignee_id,
            'creator_id': self.creator_id,
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }