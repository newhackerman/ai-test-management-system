"""
会议与AI助手模块集成服务

提供会议与AI系统的集成功能，包括：
- AI摘要生成
- 会议效果分析
- 智能建议生成
- AI服务统一管理
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.meeting import Meeting, MeetingMinutes, MeetingAnalytics
from .ai_assistant_service import AIAssistantService
from .meeting_ai_service import MeetingAIService
from ..core.exceptions import ValidationError, ServiceError


class MeetingAIIntegrationService:
    """会议AI集成服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.ai_assistant_service = AIAssistantService()
        self.meeting_ai_service = MeetingAIService(db_session)
    
    async def generate_meeting_summary(
        self,
        meeting_id: int,
        transcript_text: str
    ) -> Dict[str, Any]:
        """生成会议摘要"""
        # 获取会议信息
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()
        
        if not meeting:
            raise ValidationError("会议不存在")
        
        # 构建AI提示词
        prompt = f"""
        请分析以下会议转录内容，生成结构化摘要：
        
        会议标题：{meeting.title}
        会议类型：{meeting.meeting_type}
        会议时间：{meeting.scheduled_start_time}
        
        转录内容：
        {transcript_text}
        
        请提取以下信息：
        1. 会议摘要（200字以内）
        2. 关键讨论点（3-5个要点）
        3. 重要决策（列出所有决策）
        4. 行动项目（包含负责人和截止时间）
        
        请以JSON格式返回结果。
        """
        
        try:
            # 调用AI服务生成摘要
            ai_response = await self.ai_assistant_service.generate_response(
                prompt=prompt,
                context={'meeting_id': meeting_id, 'type': 'summary'}
            )
            
            # 保存摘要到数据库
            await self._save_meeting_summary(meeting_id, ai_response)
            
            return ai_response
            
        except Exception as e:
            raise ServiceError(f"AI摘要生成失败: {str(e)}")
    
    async def analyze_meeting_effectiveness(
        self,
        meeting_id: int
    ) -> Dict[str, Any]:
        """分析会议效果"""
        # 获取会议信息和参与者数据
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()
        
        if not meeting:
            raise ValidationError("会议不存在")
        
        try:
            # 调用会议AI服务进行分析
            analysis_result = await self.meeting_ai_service.analyze_meeting_effectiveness(
                meeting_id=meeting_id
            )
            
            # 保存分析结果
            await self._save_meeting_analysis(meeting_id, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            raise ServiceError(f"会议效果分析失败: {str(e)}")
    
    async def generate_improvement_suggestions(
        self,
        meeting_id: int,
        analysis_data: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        prompt = f"""
        基于以下会议分析数据，生成具体的改进建议：
        
        整体评分：{analysis_data.get('overall_score', 0)}
        参与度评分：{analysis_data.get('participation_score', 0)}
        效率评分：{analysis_data.get('efficiency_score', 0)}
        互动评分：{analysis_data.get('engagement_score', 0)}
        
        请生成3-5个具体的改进建议，每个建议应该：
        1. 针对具体问题
        2. 提供可操作的解决方案
        3. 简洁明了（每个建议不超过50字）
        
        以JSON数组格式返回建议列表。
        """
        
        try:
            ai_response = await self.ai_assistant_service.generate_response(
                prompt=prompt,
                context={'meeting_id': meeting_id, 'type': 'suggestions'}
            )
            
            suggestions = ai_response.get('suggestions', [])
            return suggestions
            
        except Exception as e:
            raise ServiceError(f"改进建议生成失败: {str(e)}")
    
    async def generate_meeting_minutes(
        self,
        meeting_id: int,
        transcript_text: str,
        template_type: str = 'standard'
    ) -> Dict[str, Any]:
        """生成会议纪要"""
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()
        
        if not meeting:
            raise ValidationError("会议不存在")
        
        # 根据模板类型构建提示词
        template_prompts = {
            'standard': '标准会议纪要格式',
            'project': '项目会议纪要格式',
            'standup': '站会纪要格式',
            'review': '评审会议纪要格式'
        }
        
        template_prompt = template_prompts.get(template_type, '标准会议纪要格式')
        
        prompt = f"""
        请根据以下会议信息生成{template_prompt}的会议纪要：
        
        会议标题：{meeting.title}
        会议时间：{meeting.scheduled_start_time}
        会议类型：{meeting.meeting_type}
        
        转录内容：
        {transcript_text}
        
        请生成包含以下部分的结构化纪要：
        1. 会议基本信息
        2. 参会人员
        3. 会议议程
        4. 讨论内容
        5. 决策事项
        6. 行动计划
        7. 下次会议安排
        
        以JSON格式返回结构化数据。
        """
        
        try:
            ai_response = await self.ai_assistant_service.generate_response(
                prompt=prompt,
                context={'meeting_id': meeting_id, 'type': 'minutes'}
            )
            
            # 保存纪要到数据库
            await self._save_meeting_minutes(meeting_id, ai_response, template_type)
            
            return ai_response
            
        except Exception as e:
            raise ServiceError(f"会议纪要生成失败: {str(e)}")
    
    async def _save_meeting_summary(
        self,
        meeting_id: int,
        summary_data: Dict[str, Any]
    ) -> None:
        """保存会议摘要"""
        # 这里应该保存到MeetingMinutes表或专门的摘要表
        # 简化实现，实际应该根据数据模型设计
        pass
    
    async def _save_meeting_analysis(
        self,
        meeting_id: int,
        analysis_data: Dict[str, Any]
    ) -> None:
        """保存会议分析结果"""
        analytics = MeetingAnalytics(
            meeting_id=meeting_id,
            overall_score=analysis_data.get('overall_score', 0),
            participation_score=analysis_data.get('participation_score', 0),
            efficiency_score=analysis_data.get('efficiency_score', 0),
            engagement_score=analysis_data.get('engagement_score', 0),
            analysis_data=analysis_data,
            created_at=datetime.now()
        )
        
        self.db_session.add(analytics)
        await self.db_session.flush()
    
    async def _save_meeting_minutes(
        self,
        meeting_id: int,
        minutes_data: Dict[str, Any],
        template_type: str
    ) -> None:
        """保存会议纪要"""
        minutes = MeetingMinutes(
            meeting_id=meeting_id,
            content=minutes_data,
            template_type=template_type,
            generated_by='ai',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.db_session.add(minutes)
        await self.db_session.flush()
    
    async def get_meeting_ai_insights(
        self,
        meeting_id: int
    ) -> Dict[str, Any]:
        """获取会议AI洞察"""
        # 获取所有AI分析结果
        analytics_query = select(MeetingAnalytics).where(
            MeetingAnalytics.meeting_id == meeting_id
        )
        analytics_result = await self.db_session.execute(analytics_query)
        analytics = analytics_result.scalar_one_or_none()
        
        minutes_query = select(MeetingMinutes).where(
            MeetingMinutes.meeting_id == meeting_id
        )
        minutes_result = await self.db_session.execute(minutes_query)
        minutes = minutes_result.scalar_one_or_none()
        
        insights = {
            'has_analysis': analytics is not None,
            'has_minutes': minutes is not None,
            'analysis_data': analytics.analysis_data if analytics else None,
            'minutes_content': minutes.content if minutes else None,
            'overall_score': analytics.overall_score if analytics else None
        }
        
        return insights
