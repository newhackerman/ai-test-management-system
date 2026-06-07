"""
需求协作讨论服务

提供需求协作讨论的核心业务逻辑，包括：
- 实时讨论系统
- 异步评论和通知
- 讨论归档和知识管理
- 协作功能支持
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc

from ..models.requirement import Requirement
from ..repositories.requirement_repository import RequirementRepository
from ..services.audit_service import AuditService
from ..services.requirement_notification_service import RequirementNotificationService
from ..services.websocket_service import WebSocketService
from ..core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError

logger = logging.getLogger(__name__)


class RequirementDiscussion:
    """需求讨论模型"""
    
    def __init__(self, id: int, requirement_id: int, topic: str, description: str,
                 creator_id: int, participants: List[int], status: str,
                 created_at: datetime, updated_at: datetime):
        self.id = id
        self.requirement_id = requirement_id
        self.topic = topic
        self.description = description
        self.creator_id = creator_id
        self.participants = participants
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'topic': self.topic,
            'description': self.description,
            'creator_id': self.creator_id,
            'participants': self.participants,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DiscussionMessage:
    """讨论消息模型"""
    
    def __init__(self, id: int, discussion_id: int, sender_id: int, message_type: str,
                 content: str, attachments: List[Dict], reply_to_id: Optional[int],
                 created_at: datetime, updated_at: datetime):
        self.id = id
        self.discussion_id = discussion_id
        self.sender_id = sender_id
        self.message_type = message_type
        self.content = content
        self.attachments = attachments
        self.reply_to_id = reply_to_id
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'discussion_id': self.discussion_id,
            'sender_id': self.sender_id,
            'message_type': self.message_type,
            'content': self.content,
            'attachments': self.attachments,
            'reply_to_id': self.reply_to_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RequirementDiscussionService:
    """需求协作讨论服务"""
    
    def __init__(self, db: AsyncSession,
                 audit_service: Optional[AuditService] = None,
                 notification_service: Optional[RequirementNotificationService] = None,
                 websocket_service: Optional[WebSocketService] = None):
        self.db = db
        self.requirement_repo = RequirementRepository(db)
        self.audit_service = audit_service
        self.notification_service = notification_service
        self.websocket_service = websocket_service
        
        # 模拟数据存储（实际应该使用数据库表）
        self._discussions: Dict[int, RequirementDiscussion] = {}
        self._messages: Dict[int, List[DiscussionMessage]] = {}
        self._next_discussion_id = 1
        self._next_message_id = 1
    
    async def create_discussion(self, discussion_data: Dict[str, Any], creator_id: int) -> RequirementDiscussion:
        """
        创建需求讨论
        
        Args:
            discussion_data: 讨论数据
            creator_id: 创建人ID
            
        Returns:
            创建的讨论对象
        """
        try:
            # 1. 验证讨论数据
            await self._validate_discussion_data(discussion_data)
            
            # 2. 检查需求存在性
            requirement = await self.requirement_repo.get_by_id(discussion_data['requirement_id'])
            if not requirement:
                raise NotFoundError(f"需求不存在: {discussion_data['requirement_id']}")
            
            # 3. 创建讨论对象
            discussion = RequirementDiscussion(
                id=self._next_discussion_id,
                requirement_id=discussion_data['requirement_id'],
                topic=discussion_data['topic'],
                description=discussion_data.get('description', ''),
                creator_id=creator_id,
                participants=discussion_data.get('participants', [creator_id]),
                status='active',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 4. 保存讨论
            self._discussions[self._next_discussion_id] = discussion
            self._messages[self._next_discussion_id] = []
            self._next_discussion_id += 1
            
            # 5. 发送创建通知
            if self.notification_service:
                await self._send_discussion_created_notifications(discussion)
            
            # 6. 实时通知参与者
            if self.websocket_service:
                await self._broadcast_discussion_event(discussion, 'discussion_created', creator_id)
            
            # 7. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=creator_id,
                    operation="CREATE_DISCUSSION",
                    resource_type="requirement_discussion",
                    resource_id=discussion.id,
                    details={
                        "requirement_id": discussion.requirement_id,
                        "topic": discussion.topic,
                        "participants": discussion.participants
                    }
                )
            
            logger.info(f"需求讨论创建成功: {discussion.id} for requirement {discussion.requirement_id}")
            return discussion
            
        except Exception as e:
            logger.error(f"创建需求讨论失败: {str(e)}")
            raise BusinessLogicError(f"创建需求讨论失败: {str(e)}")
    
    async def send_message(self, message_data: Dict[str, Any], sender_id: int) -> DiscussionMessage:
        """
        发送讨论消息
        
        Args:
            message_data: 消息数据
            sender_id: 发送人ID
            
        Returns:
            发送的消息对象
        """
        try:
            # 1. 验证消息数据
            await self._validate_message_data(message_data)
            
            # 2. 检查讨论存在性和权限
            discussion = await self._get_discussion_by_id(message_data['discussion_id'])
            if not await self._has_discussion_permission(discussion, sender_id):
                raise PermissionError("没有参与讨论的权限")
            
            # 3. 创建消息对象
            message = DiscussionMessage(
                id=self._next_message_id,
                discussion_id=message_data['discussion_id'],
                sender_id=sender_id,
                message_type=message_data.get('message_type', 'text'),
                content=message_data['content'],
                attachments=message_data.get('attachments', []),
                reply_to_id=message_data.get('reply_to_id'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 4. 保存消息
            if discussion.id not in self._messages:
                self._messages[discussion.id] = []
            self._messages[discussion.id].append(message)
            self._next_message_id += 1
            
            # 5. 更新讨论时间
            discussion.updated_at = datetime.utcnow()
            
            # 6. 实时广播消息
            if self.websocket_service:
                await self._broadcast_message(discussion, message)
            
            # 7. 发送异步通知
            if self.notification_service:
                await self._send_message_notifications(discussion, message)
            
            # 8. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=sender_id,
                    operation="SEND_DISCUSSION_MESSAGE",
                    resource_type="discussion_message",
                    resource_id=message.id,
                    details={
                        "discussion_id": message.discussion_id,
                        "message_type": message.message_type,
                        "reply_to_id": message.reply_to_id
                    }
                )
            
            logger.info(f"讨论消息发送成功: {message.id} in discussion {discussion.id}")
            return message
            
        except Exception as e:
            logger.error(f"发送讨论消息失败: {str(e)}")
            raise BusinessLogicError(f"发送讨论消息失败: {str(e)}")
    
    async def add_participant(self, discussion_id: int, participant_id: int, added_by: int) -> RequirementDiscussion:
        """
        添加讨论参与者
        
        Args:
            discussion_id: 讨论ID
            participant_id: 参与者ID
            added_by: 添加人ID
            
        Returns:
            更新后的讨论对象
        """
        try:
            # 1. 获取讨论
            discussion = await self._get_discussion_by_id(discussion_id)
            
            # 2. 验证权限
            if not await self._has_manage_permission(discussion, added_by):
                raise PermissionError("没有管理讨论的权限")
            
            # 3. 检查参与者是否已存在
            if participant_id in discussion.participants:
                raise BusinessLogicError("用户已经是讨论参与者")
            
            # 4. 添加参与者
            discussion.participants.append(participant_id)
            discussion.updated_at = datetime.utcnow()
            
            # 5. 发送加入通知
            if self.notification_service:
                await self.notification_service.send_discussion_invitation(
                    participant_id, discussion
                )
            
            # 6. 实时通知
            if self.websocket_service:
                await self._broadcast_discussion_event(
                    discussion, 'participant_added', added_by,
                    {'participant_id': participant_id}
                )
            
            # 7. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=added_by,
                    operation="ADD_DISCUSSION_PARTICIPANT",
                    resource_type="requirement_discussion",
                    resource_id=discussion_id,
                    details={
                        "participant_id": participant_id,
                        "requirement_id": discussion.requirement_id
                    }
                )
            
            logger.info(f"讨论参与者添加成功: {participant_id} to discussion {discussion_id}")
            return discussion
            
        except Exception as e:
            logger.error(f"添加讨论参与者失败: {str(e)}")
            raise BusinessLogicError(f"添加讨论参与者失败: {str(e)}")
    
    async def remove_participant(self, discussion_id: int, participant_id: int, removed_by: int) -> RequirementDiscussion:
        """
        移除讨论参与者
        
        Args:
            discussion_id: 讨论ID
            participant_id: 参与者ID
            removed_by: 移除人ID
            
        Returns:
            更新后的讨论对象
        """
        try:
            # 1. 获取讨论
            discussion = await self._get_discussion_by_id(discussion_id)
            
            # 2. 验证权限
            if not await self._has_manage_permission(discussion, removed_by):
                raise PermissionError("没有管理讨论的权限")
            
            # 3. 检查参与者存在性
            if participant_id not in discussion.participants:
                raise BusinessLogicError("用户不是讨论参与者")
            
            # 4. 不能移除创建者
            if participant_id == discussion.creator_id:
                raise BusinessLogicError("不能移除讨论创建者")
            
            # 5. 移除参与者
            discussion.participants.remove(participant_id)
            discussion.updated_at = datetime.utcnow()
            
            # 6. 发送移除通知
            if self.notification_service:
                await self.notification_service.send_discussion_removal(
                    participant_id, discussion
                )
            
            # 7. 实时通知
            if self.websocket_service:
                await self._broadcast_discussion_event(
                    discussion, 'participant_removed', removed_by,
                    {'participant_id': participant_id}
                )
            
            # 8. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=removed_by,
                    operation="REMOVE_DISCUSSION_PARTICIPANT",
                    resource_type="requirement_discussion",
                    resource_id=discussion_id,
                    details={
                        "participant_id": participant_id,
                        "requirement_id": discussion.requirement_id
                    }
                )
            
            logger.info(f"讨论参与者移除成功: {participant_id} from discussion {discussion_id}")
            return discussion
            
        except Exception as e:
            logger.error(f"移除讨论参与者失败: {str(e)}")
            raise BusinessLogicError(f"移除讨论参与者失败: {str(e)}")
    
    async def close_discussion(self, discussion_id: int, summary: str, closed_by: int) -> RequirementDiscussion:
        """
        关闭讨论
        
        Args:
            discussion_id: 讨论ID
            summary: 讨论总结
            closed_by: 关闭人ID
            
        Returns:
            关闭的讨论对象
        """
        try:
            # 1. 获取讨论
            discussion = await self._get_discussion_by_id(discussion_id)
            
            # 2. 验证权限
            if not await self._has_manage_permission(discussion, closed_by):
                raise PermissionError("没有关闭讨论的权限")
            
            if discussion.status == 'closed':
                raise BusinessLogicError("讨论已经关闭")
            
            # 3. 关闭讨论
            discussion.status = 'closed'
            discussion.updated_at = datetime.utcnow()
            
            # 4. 创建总结消息
            summary_message = DiscussionMessage(
                id=self._next_message_id,
                discussion_id=discussion_id,
                sender_id=closed_by,
                message_type='summary',
                content=summary,
                attachments=[],
                reply_to_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            if discussion.id not in self._messages:
                self._messages[discussion.id] = []
            self._messages[discussion.id].append(summary_message)
            self._next_message_id += 1
            
            # 5. 归档讨论到知识库
            await self._archive_discussion_to_knowledge_base(discussion, summary)
            
            # 6. 发送关闭通知
            if self.notification_service:
                await self._send_discussion_closed_notifications(discussion, summary)
            
            # 7. 实时通知
            if self.websocket_service:
                await self._broadcast_discussion_event(
                    discussion, 'discussion_closed', closed_by,
                    {'summary': summary}
                )
            
            # 8. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=closed_by,
                    operation="CLOSE_DISCUSSION",
                    resource_type="requirement_discussion",
                    resource_id=discussion_id,
                    details={
                        "requirement_id": discussion.requirement_id,
                        "summary": summary
                    }
                )
            
            logger.info(f"讨论关闭成功: {discussion_id}")
            return discussion
            
        except Exception as e:
            logger.error(f"关闭讨论失败: {str(e)}")
            raise BusinessLogicError(f"关闭讨论失败: {str(e)}")
    
    async def get_discussion_by_id(self, discussion_id: int) -> Optional[RequirementDiscussion]:
        """根据ID获取讨论"""
        return self._discussions.get(discussion_id)
    
    async def get_discussions_by_requirement(self, requirement_id: int) -> List[RequirementDiscussion]:
        """获取需求的所有讨论"""
        return [
            discussion for discussion in self._discussions.values()
            if discussion.requirement_id == requirement_id
        ]
    
    async def get_user_discussions(self, user_id: int, status: Optional[str] = None) -> List[RequirementDiscussion]:
        """获取用户参与的讨论"""
        discussions = [
            discussion for discussion in self._discussions.values()
            if user_id in discussion.participants
        ]
        
        if status:
            discussions = [d for d in discussions if d.status == status]
        
        return sorted(discussions, key=lambda x: x.updated_at, reverse=True)
    
    async def get_discussion_messages(self, discussion_id: int, skip: int = 0, limit: int = 50) -> List[DiscussionMessage]:
        """获取讨论消息列表"""
        messages = self._messages.get(discussion_id, [])
        return messages[skip:skip + limit]
    
    async def search_discussions(self, search_params: Dict[str, Any]) -> List[RequirementDiscussion]:
        """搜索讨论"""
        discussions = list(self._discussions.values())
        
        # 按需求ID筛选
        if 'requirement_id' in search_params:
            discussions = [
                d for d in discussions 
                if d.requirement_id == search_params['requirement_id']
            ]
        
        # 按状态筛选
        if 'status' in search_params:
            discussions = [
                d for d in discussions 
                if d.status == search_params['status']
            ]
        
        # 按关键词搜索
        if 'keyword' in search_params:
            keyword = search_params['keyword'].lower()
            discussions = [
                d for d in discussions
                if keyword in d.topic.lower() or keyword in d.description.lower()
            ]
        
        return sorted(discussions, key=lambda x: x.updated_at, reverse=True)
    
    async def get_discussion_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取讨论统计信息"""
        discussions = list(self._discussions.values())
        
        # 如果指定项目，需要通过需求过滤
        if project_id:
            # 这里需要查询需求来过滤，简化处理
            pass
        
        total_discussions = len(discussions)
        active_discussions = len([d for d in discussions if d.status == 'active'])
        closed_discussions = len([d for d in discussions if d.status == 'closed'])
        
        total_messages = sum(len(messages) for messages in self._messages.values())
        
        return {
            "total_discussions": total_discussions,
            "active_discussions": active_discussions,
            "closed_discussions": closed_discussions,
            "total_messages": total_messages,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # 私有方法
    
    async def _get_discussion_by_id(self, discussion_id: int) -> RequirementDiscussion:
        """根据ID获取讨论"""
        discussion = self._discussions.get(discussion_id)
        if not discussion:
            raise NotFoundError(f"讨论不存在: {discussion_id}")
        return discussion
    
    async def _validate_discussion_data(self, discussion_data: Dict[str, Any]):
        """验证讨论数据"""
        required_fields = ['requirement_id', 'topic']
        
        for field in required_fields:
            if field not in discussion_data or not discussion_data[field]:
                raise ValidationError(f"必填字段缺失: {field}")
        
        # 验证主题长度
        if len(discussion_data['topic']) < 3:
            raise ValidationError("讨论主题至少需要3个字符")
        
        if len(discussion_data['topic']) > 200:
            raise ValidationError("讨论主题不能超过200个字符")
    
    async def _validate_message_data(self, message_data: Dict[str, Any]):
        """验证消息数据"""
        required_fields = ['discussion_id', 'content']
        
        for field in required_fields:
            if field not in message_data or not message_data[field]:
                raise ValidationError(f"必填字段缺失: {field}")
        
        # 验证消息内容
        if len(message_data['content'].strip()) == 0:
            raise ValidationError("消息内容不能为空")
        
        if len(message_data['content']) > 5000:
            raise ValidationError("消息内容不能超过5000个字符")
        
        # 验证消息类型
        valid_types = ['text', 'image', 'file', 'code', 'summary']
        if 'message_type' in message_data:
            if message_data['message_type'] not in valid_types:
                raise ValidationError(f"无效的消息类型: {message_data['message_type']}")
    
    async def _has_discussion_permission(self, discussion: RequirementDiscussion, user_id: int) -> bool:
        """检查是否有讨论权限"""
        return user_id in discussion.participants
    
    async def _has_manage_permission(self, discussion: RequirementDiscussion, user_id: int) -> bool:
        """检查是否有管理权限"""
        # 创建者和需求负责人可以管理讨论
        if user_id == discussion.creator_id:
            return True
        
        # 检查是否是需求负责人
        requirement = await self.requirement_repo.get_by_id(discussion.requirement_id)
        if requirement and user_id == requirement.assignee_id:
            return True
        
        return False
    
    async def _broadcast_message(self, discussion: RequirementDiscussion, message: DiscussionMessage):
        """实时广播消息"""
        if not self.websocket_service:
            return
        
        try:
            # 向所有参与者广播消息
            for participant_id in discussion.participants:
                if participant_id != message.sender_id:  # 不向发送者广播
                    await self.websocket_service.send_to_user(
                        participant_id,
                        {
                            "type": "discussion_message",
                            "discussion_id": discussion.id,
                            "message": message.to_dict()
                        }
                    )
                    
        except Exception as e:
            logger.error(f"广播讨论消息失败: {str(e)}")
    
    async def _broadcast_discussion_event(self, discussion: RequirementDiscussion, 
                                        event_type: str, user_id: int, 
                                        extra_data: Optional[Dict] = None):
        """广播讨论事件"""
        if not self.websocket_service:
            return
        
        try:
            event_data = {
                "type": event_type,
                "discussion": discussion.to_dict(),
                "user_id": user_id
            }
            
            if extra_data:
                event_data.update(extra_data)
            
            # 向所有参与者广播事件
            for participant_id in discussion.participants:
                await self.websocket_service.send_to_user(participant_id, event_data)
                
        except Exception as e:
            logger.error(f"广播讨论事件失败: {str(e)}")
    
    async def _send_discussion_created_notifications(self, discussion: RequirementDiscussion):
        """发送讨论创建通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知所有参与者（除了创建者）
            for participant_id in discussion.participants:
                if participant_id != discussion.creator_id:
                    await self.notification_service.send_discussion_invitation(
                        participant_id, discussion
                    )
                    
        except Exception as e:
            logger.error(f"发送讨论创建通知失败: {str(e)}")
    
    async def _send_message_notifications(self, discussion: RequirementDiscussion, 
                                        message: DiscussionMessage):
        """发送消息通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知所有参与者（除了发送者）
            for participant_id in discussion.participants:
                if participant_id != message.sender_id:
                    await self.notification_service.send_discussion_message(
                        participant_id, discussion, message
                    )
                    
        except Exception as e:
            logger.error(f"发送消息通知失败: {str(e)}")
    
    async def _send_discussion_closed_notifications(self, discussion: RequirementDiscussion, 
                                                  summary: str):
        """发送讨论关闭通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知所有参与者
            for participant_id in discussion.participants:
                await self.notification_service.send_discussion_closed(
                    participant_id, discussion, summary
                )
                
        except Exception as e:
            logger.error(f"发送讨论关闭通知失败: {str(e)}")
    
    async def _archive_discussion_to_knowledge_base(self, discussion: RequirementDiscussion, 
                                                  summary: str):
        """将讨论归档到知识库"""
        try:
            # 获取讨论的所有消息
            messages = self._messages.get(discussion.id, [])
            
            # 构建知识条目
            knowledge_entry = {
                "type": "requirement_discussion",
                "requirement_id": discussion.requirement_id,
                "topic": discussion.topic,
                "description": discussion.description,
                "summary": summary,
                "participants": discussion.participants,
                "message_count": len(messages),
                "created_at": discussion.created_at.isoformat(),
                "closed_at": discussion.updated_at.isoformat(),
                "messages": [message.to_dict() for message in messages]
            }
            
            # 这里应该保存到知识库系统
            # 暂时记录日志
            logger.info(f"讨论归档到知识库: {discussion.id}")
            
            # 提取关键信息和决策
            await self._extract_discussion_insights(discussion, messages, summary)
            
        except Exception as e:
            logger.error(f"归档讨论到知识库失败: {str(e)}")
    
    async def _extract_discussion_insights(self, discussion: RequirementDiscussion,
                                         messages: List[DiscussionMessage], summary: str):
        """提取讨论洞察和决策"""
        try:
            # 分析讨论内容，提取关键决策和洞察
            insights = {
                "discussion_id": discussion.id,
                "requirement_id": discussion.requirement_id,
                "key_decisions": [],
                "action_items": [],
                "concerns_raised": [],
                "solutions_proposed": [],
                "participants_engagement": {}
            }
            
            # 简单的关键词分析
            decision_keywords = ["决定", "确定", "同意", "批准", "采用"]
            action_keywords = ["需要", "应该", "必须", "计划", "安排"]
            concern_keywords = ["担心", "问题", "风险", "困难", "挑战"]
            solution_keywords = ["建议", "方案", "解决", "改进", "优化"]
            
            for message in messages:
                content = message.content.lower()
                
                # 检测决策
                if any(keyword in content for keyword in decision_keywords):
                    insights["key_decisions"].append({
                        "message_id": message.id,
                        "sender_id": message.sender_id,
                        "content": message.content[:200],
                        "timestamp": message.created_at.isoformat()
                    })
                
                # 检测行动项
                if any(keyword in content for keyword in action_keywords):
                    insights["action_items"].append({
                        "message_id": message.id,
                        "sender_id": message.sender_id,
                        "content": message.content[:200],
                        "timestamp": message.created_at.isoformat()
                    })
                
                # 统计参与度
                sender_id = message.sender_id
                if sender_id not in insights["participants_engagement"]:
                    insights["participants_engagement"][sender_id] = 0
                insights["participants_engagement"][sender_id] += 1
            
            # 保存洞察到知识库
            logger.info(f"讨论洞察提取完成: {discussion.id}")
            
        except Exception as e:
            logger.error(f"提取讨论洞察失败: {str(e)}")