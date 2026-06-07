"""
会议分析数据模型

存储AI分析生成的会议效果评估数据
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class MeetingAnalytics(Base):
    """会议分析数据模型"""
    
    __tablename__ = 'meeting_analytics'
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey('meetings.id'), nullable=False, unique=True, index=True)
    
    # 评分数据
    overall_score = Column(Float, nullable=True)  # 总体评分 (0-10)
    participation_score = Column(Float, nullable=True)  # 参与度评分 (0-10)
    efficiency_score = Column(Float, nullable=True)  # 效率评分 (0-10)
    engagement_score = Column(Float, nullable=True)  # 互动评分 (0-10)
    
    # 详细分析数据
    analysis_data = Column(JSON, nullable=True)  # 完整的分析结果
    
    # 改进建议
    suggestions = Column(JSON, nullable=True)  # AI生成的改进建议
    
    # 元数据
    analysis_version = Column(String(20), nullable=True, default='1.0')  # 分析算法版本
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="analytics")
    
    def __repr__(self):
        return f"<MeetingAnalytics(id={self.id}, meeting_id={self.meeting_id}, overall_score={self.overall_score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'overall_score': self.overall_score,
            'participation_score': self.participation_score,
            'efficiency_score': self.efficiency_score,
            'engagement_score': self.engagement_score,
            'analysis_data': self.analysis_data,
            'suggestions': self.suggestions,
            'analysis_version': self.analysis_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_score_summary(self) -> Dict[str, Any]:
        """获取评分摘要"""
        return {
            'overall_score': self.overall_score,
            'participation_score': self.participation_score,
            'efficiency_score': self.efficiency_score,
            'engagement_score': self.engagement_score,
            'average_score': self.calculate_average_score()
        }
    
    def calculate_average_score(self) -> Optional[float]:
        """计算平均评分"""
        scores = [
            self.overall_score,
            self.participation_score,
            self.efficiency_score,
            self.engagement_score
        ]
        
        valid_scores = [score for score in scores if score is not None]
        
        if not valid_scores:
            return None
        
        return round(sum(valid_scores) / len(valid_scores), 2)
    
    def get_performance_level(self) -> str:
        """获取表现等级"""
        avg_score = self.calculate_average_score()
        
        if avg_score is None:
            return 'unknown'
        elif avg_score >= 8.0:
            return 'excellent'
        elif avg_score >= 6.0:
            return 'good'
        elif avg_score >= 4.0:
            return 'fair'
        else:
            return 'poor'
    
    def update_scores(
        self,
        overall_score: Optional[float] = None,
        participation_score: Optional[float] = None,
        efficiency_score: Optional[float] = None,
        engagement_score: Optional[float] = None
    ) -> None:
        """更新评分"""
        if overall_score is not None:
            self.overall_score = overall_score
        if participation_score is not None:
            self.participation_score = participation_score
        if efficiency_score is not None:
            self.efficiency_score = efficiency_score
        if engagement_score is not None:
            self.engagement_score = engagement_score
        
        self.updated_at = datetime.now()
    
    def add_suggestion(self, suggestion: str, category: str = 'general') -> None:
        """添加改进建议"""
        if self.suggestions is None:
            self.suggestions = []
        
        self.suggestions.append({
            'text': suggestion,
            'category': category,
            'timestamp': datetime.now().isoformat()
        })
        
        self.updated_at = datetime.now()