"""
需求管理WebSocket实时通信服务
支持需求状态更新、协作讨论、变更通知等实时功能
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from enum import Enum

from pydantic import BaseModel, Field

from .websocket_service import websocket_service, WSMessage, WSMessageType
from ..models.requirement import Requirement, RequirementStatus
from ..models.requirement import RequirementReview
from ..models.requirement import RequirementChangeRequest


logger = logging.getLogger(__name__)


class RequirementWSMessageType(str, Enum):
    """需求管理WebSocket消息类型"""
    # 需求状态相关
    REQUIREMENT_STATUS_CHANGED = "requirement_status_changed"
    REQUIREMENT_CREATED = "requirement_created"
    REQUIREMENT_UPDATED = "requirement_updated"
    REQUIREMENT_DELETED = "requirement_deleted"
    
    # 需求评审相关
    REVIEW_STARTED = "review_started"
    REVIEW_COMMENT_ADDED = "review_comment_added"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_ASSIGNED = "review_assigned"
    
    # 需求变更相关
    CHANGE_REQUEST_CREATED = "change_request_created"
    CHANGE_REQUEST_APPROVED = "change_request_approved"
    CHANGE_REQUEST_REJECTED = "change_request_rejected"
    CHANGE_REQUEST_IMPLEMENTED = "change_request_implemented"
    
    # 协作讨论相关
    DISCUSSION_MESSAGE = "discussion_message"
    USER_TYPING = "user_typing"
    USER_JOINED_DISCUSSION = "user_joined_discussion"
    USER_LEFT_DISCUSSION = "user_left_discussion"
    
    # 在线状态相关
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    USER_STATUS_UPDATE = "user_status_update"
    
    # 通知相关
    NOTIFICATION = "notification"
    REMINDER = "reminder"
    ALERT = "alert"


class RequirementWSMessage(BaseModel):
    """需求管理WebSocket消息"""
    type: RequirementWSMessageType = Field(..., description="消息类型")
    requirement_id: Optional[int] = Field(None, description="需求ID")
    project_id: Optional[int] = Field(None, description="项目ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    data: Any = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class OnlineUserStatus(BaseModel):
    """在线用户状态"""
    user_id: int
    username: str
    status: str  # online, away, busy, offline
    last_activity: datetime
    current_requirement: Optional[int] = None
    current_action: Optional[str] = None  # viewing, editing, reviewing


class RequirementWebSocketService:
    """需求管理WebSocket服务"""
    
    def __init__(self):
        self.online_users: Dict[int, OnlineUserStatus] = {}
        self.requirement_watchers: Dict[int, Set[int]] = {}  # requirement_id -> user_ids
        self.project_watchers: Dict[int, Set[int]] = {}  # project_id -> user_ids
        self.discussion_rooms: Dict[int, Set[int]] = {}  # requirement_id -> user_ids
        
        # 注册消息处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册WebSocket消息处理器"""
        # 注册需求相关的消息处理器
        websocket_service.register_handler(
            RequirementWSMessageType.USER_TYPING, 
            self._handle_user_typing
        )
        websocket_service.register_handler(
            RequirementWSMessageType.USER_JOINED_DISCUSSION, 
            self._handle_user_joined_discussion
        )
        websocket_service.register_handler(
            RequirementWSMessageType.USER_LEFT_DISCUSSION, 
            self._handle_user_left_discussion
        )
    
    async def user_online(self, user_id: int, username: str):
        """用户上线"""
        try:
            # 更新在线状态
            self.online_users[user_id] = OnlineUserStatus(
                user_id=user_id,
                username=username,
                status="online",
                last_activity=datetime.utcnow()
            )
            
            # 通知相关用户
            await self._broadcast_user_status_update(user_id, "online")
            
            logger.info(f"User {user_id} ({username}) is now online")
            
        except Exception as e:
            logger.error(f"Error handling user online: {e}")
    
    async def user_offline(self, user_id: int):
        """用户下线"""
        try:
            if user_id in self.online_users:
                username = self.online_users[user_id].username
                del self.online_users[user_id]
                
                # 从所有监听中移除
                for watchers in self.requirement_watchers.values():
                    watchers.discard(user_id)
                for watchers in self.project_watchers.values():
                    watchers.discard(user_id)
                for room_users in self.discussion_rooms.values():
                    room_users.discard(user_id)
                
                # 通知相关用户
                await self._broadcast_user_status_update(user_id, "offline")
                
                logger.info(f"User {user_id} ({username}) is now offline")
                
        except Exception as e:
            logger.error(f"Error handling user offline: {e}")
    
    async def update_user_activity(self, user_id: int, requirement_id: Optional[int] = None, action: Optional[str] = None):
        """更新用户活动状态"""
        try:
            if user_id in self.online_users:
                user_status = self.online_users[user_id]
                user_status.last_activity = datetime.utcnow()
                user_status.current_requirement = requirement_id
                user_status.current_action = action
                
                # 通知相关用户
                await self._broadcast_user_status_update(user_id, "activity_update")
                
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
    
    async def watch_requirement(self, user_id: int, requirement_id: int):
        """用户开始监听需求"""
        try:
            if requirement_id not in self.requirement_watchers:
                self.requirement_watchers[requirement_id] = set()
            
            self.requirement_watchers[requirement_id].add(user_id)
            
            # 更新用户活动状态
            await self.update_user_activity(user_id, requirement_id, "watching")
            
            logger.debug(f"User {user_id} is now watching requirement {requirement_id}")
            
        except Exception as e:
            logger.error(f"Error adding requirement watcher: {e}")
    
    async def unwatch_requirement(self, user_id: int, requirement_id: int):
        """用户停止监听需求"""
        try:
            if requirement_id in self.requirement_watchers:
                self.requirement_watchers[requirement_id].discard(user_id)
                if not self.requirement_watchers[requirement_id]:
                    del self.requirement_watchers[requirement_id]
            
            logger.debug(f"User {user_id} stopped watching requirement {requirement_id}")
            
        except Exception as e:
            logger.error(f"Error removing requirement watcher: {e}")
    
    async def watch_project(self, user_id: int, project_id: int):
        """用户开始监听项目"""
        try:
            if project_id not in self.project_watchers:
                self.project_watchers[project_id] = set()
            
            self.project_watchers[project_id].add(user_id)
            
            logger.debug(f"User {user_id} is now watching project {project_id}")
            
        except Exception as e:
            logger.error(f"Error adding project watcher: {e}")
    
    async def unwatch_project(self, user_id: int, project_id: int):
        """用户停止监听项目"""
        try:
            if project_id in self.project_watchers:
                self.project_watchers[project_id].discard(user_id)
                if not self.project_watchers[project_id]:
                    del self.project_watchers[project_id]
            
            logger.debug(f"User {user_id} stopped watching project {project_id}")
            
        except Exception as e:
            logger.error(f"Error removing project watcher: {e}")
    
    async def join_discussion(self, user_id: int, requirement_id: int):
        """用户加入需求讨论"""
        try:
            if requirement_id not in self.discussion_rooms:
                self.discussion_rooms[requirement_id] = set()
            
            self.discussion_rooms[requirement_id].add(user_id)
            
            # 通知其他讨论参与者
            await self._notify_discussion_participants(
                requirement_id,
                RequirementWSMessageType.USER_JOINED_DISCUSSION,
                {"user_id": user_id},
                exclude_user=user_id
            )
            
            # 更新用户活动状态
            await self.update_user_activity(user_id, requirement_id, "discussing")
            
            logger.debug(f"User {user_id} joined discussion for requirement {requirement_id}")
            
        except Exception as e:
            logger.error(f"Error joining discussion: {e}")
    
    async def leave_discussion(self, user_id: int, requirement_id: int):
        """用户离开需求讨论"""
        try:
            if requirement_id in self.discussion_rooms:
                self.discussion_rooms[requirement_id].discard(user_id)
                if not self.discussion_rooms[requirement_id]:
                    del self.discussion_rooms[requirement_id]
                
                # 通知其他讨论参与者
                await self._notify_discussion_participants(
                    requirement_id,
                    RequirementWSMessageType.USER_LEFT_DISCUSSION,
                    {"user_id": user_id},
                    exclude_user=user_id
                )
            
            logger.debug(f"User {user_id} left discussion for requirement {requirement_id}")
            
        except Exception as e:
            logger.error(f"Error leaving discussion: {e}")
    
    async def send_requirement_status_update(self, requirement: Requirement, old_status: str, new_status: str, changed_by: int):
        """发送需求状态更新通知"""
        try:
            message_data = {
                "requirement_id": requirement.id,
                "requirement_code": requirement.requirement_code,
                "title": requirement.title,
                "old_status": old_status,
                "new_status": new_status,
                "changed_by": changed_by,
                "project_id": requirement.project_id
            }
            
            # 发送给需求监听者
            await self._notify_requirement_watchers(
                requirement.id,
                RequirementWSMessageType.REQUIREMENT_STATUS_CHANGED,
                message_data
            )
            
            # 发送给项目监听者
            await self._notify_project_watchers(
                requirement.project_id,
                RequirementWSMessageType.REQUIREMENT_STATUS_CHANGED,
                message_data
            )
            
            logger.info(f"Sent requirement status update for {requirement.requirement_code}: {old_status} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Error sending requirement status update: {e}")
    
    async def send_requirement_created(self, requirement: Requirement, created_by: int):
        """发送需求创建通知"""
        try:
            message_data = {
                "requirement_id": requirement.id,
                "requirement_code": requirement.requirement_code,
                "title": requirement.title,
                "status": requirement.status.value,
                "priority": requirement.priority.value,
                "created_by": created_by,
                "project_id": requirement.project_id
            }
            
            # 发送给项目监听者
            await self._notify_project_watchers(
                requirement.project_id,
                RequirementWSMessageType.REQUIREMENT_CREATED,
                message_data
            )
            
            logger.info(f"Sent requirement created notification for {requirement.requirement_code}")
            
        except Exception as e:
            logger.error(f"Error sending requirement created notification: {e}")
    
    async def send_requirement_updated(self, requirement: Requirement, updated_by: int, changes: Dict[str, Any]):
        """发送需求更新通知"""
        try:
            message_data = {
                "requirement_id": requirement.id,
                "requirement_code": requirement.requirement_code,
                "title": requirement.title,
                "updated_by": updated_by,
                "changes": changes,
                "project_id": requirement.project_id
            }
            
            # 发送给需求监听者
            await self._notify_requirement_watchers(
                requirement.id,
                RequirementWSMessageType.REQUIREMENT_UPDATED,
                message_data
            )
            
            # 发送给项目监听者
            await self._notify_project_watchers(
                requirement.project_id,
                RequirementWSMessageType.REQUIREMENT_UPDATED,
                message_data
            )
            
            logger.info(f"Sent requirement updated notification for {requirement.requirement_code}")
            
        except Exception as e:
            logger.error(f"Error sending requirement updated notification: {e}")
    
    async def send_review_notification(self, review: RequirementReview, event_type: RequirementWSMessageType, additional_data: Optional[Dict] = None):
        """发送评审相关通知"""
        try:
            message_data = {
                "review_id": review.id,
                "requirement_id": review.requirement_id,
                "review_type": review.review_type.value,
                "review_status": review.review_status.value,
                "moderator_id": review.moderator_id,
                "reviewers": review.reviewers,
                **(additional_data or {})
            }
            
            # 发送给需求监听者
            await self._notify_requirement_watchers(
                review.requirement_id,
                event_type,
                message_data
            )
            
            # 发送给评审参与者
            all_participants = set([review.moderator_id] + (review.reviewers or []))
            for user_id in all_participants:
                await websocket_service.connection_manager.send_to_user(
                    user_id,
                    WSMessage(
                        type=event_type,
                        data=message_data,
                        timestamp=datetime.utcnow().isoformat()
                    )
                )
            
            logger.info(f"Sent review notification: {event_type} for review {review.id}")
            
        except Exception as e:
            logger.error(f"Error sending review notification: {e}")
    
    async def send_change_request_notification(self, change_request: RequirementChangeRequest, event_type: RequirementWSMessageType, additional_data: Optional[Dict] = None):
        """发送变更请求通知"""
        try:
            message_data = {
                "change_request_id": change_request.id,
                "change_request_code": change_request.change_request_code,
                "requirement_id": change_request.requirement_id,
                "title": change_request.title,
                "change_type": change_request.change_type.value,
                "status": change_request.status.value,
                "priority": change_request.priority.value,
                "requestor_id": change_request.requestor_id,
                "approver_id": change_request.approver_id,
                **(additional_data or {})
            }
            
            # 发送给需求监听者
            await self._notify_requirement_watchers(
                change_request.requirement_id,
                event_type,
                message_data
            )
            
            # 发送给相关人员
            relevant_users = set([change_request.requestor_id])
            if change_request.approver_id:
                relevant_users.add(change_request.approver_id)
            if change_request.implementer_id:
                relevant_users.add(change_request.implementer_id)
            
            for user_id in relevant_users:
                await websocket_service.connection_manager.send_to_user(
                    user_id,
                    WSMessage(
                        type=event_type,
                        data=message_data,
                        timestamp=datetime.utcnow().isoformat()
                    )
                )
            
            logger.info(f"Sent change request notification: {event_type} for {change_request.change_request_code}")
            
        except Exception as e:
            logger.error(f"Error sending change request notification: {e}")
    
    async def send_discussion_message(self, requirement_id: int, user_id: int, message: str, message_type: str = "text"):
        """发送讨论消息"""
        try:
            message_data = {
                "requirement_id": requirement_id,
                "user_id": user_id,
                "message": message,
                "message_type": message_type
            }
            
            # 发送给讨论参与者
            await self._notify_discussion_participants(
                requirement_id,
                RequirementWSMessageType.DISCUSSION_MESSAGE,
                message_data,
                exclude_user=user_id
            )
            
            logger.debug(f"Sent discussion message for requirement {requirement_id}")
            
        except Exception as e:
            logger.error(f"Error sending discussion message: {e}")
    
    async def send_typing_indicator(self, requirement_id: int, user_id: int, is_typing: bool):
        """发送打字指示器"""
        try:
            message_data = {
                "requirement_id": requirement_id,
                "user_id": user_id,
                "is_typing": is_typing
            }
            
            # 发送给讨论参与者
            await self._notify_discussion_participants(
                requirement_id,
                RequirementWSMessageType.USER_TYPING,
                message_data,
                exclude_user=user_id
            )
            
        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
    
    async def _notify_requirement_watchers(self, requirement_id: int, message_type: RequirementWSMessageType, data: Dict[str, Any]):
        """通知需求监听者"""
        if requirement_id not in self.requirement_watchers:
            return
        
        message = WSMessage(
            type=message_type,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        for user_id in self.requirement_watchers[requirement_id]:
            await websocket_service.connection_manager.send_to_user(user_id, message)
    
    async def _notify_project_watchers(self, project_id: int, message_type: RequirementWSMessageType, data: Dict[str, Any]):
        """通知项目监听者"""
        if project_id not in self.project_watchers:
            return
        
        message = WSMessage(
            type=message_type,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        for user_id in self.project_watchers[project_id]:
            await websocket_service.connection_manager.send_to_user(user_id, message)
    
    async def _notify_discussion_participants(self, requirement_id: int, message_type: RequirementWSMessageType, data: Dict[str, Any], exclude_user: Optional[int] = None):
        """通知讨论参与者"""
        if requirement_id not in self.discussion_rooms:
            return
        
        message = WSMessage(
            type=message_type,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        for user_id in self.discussion_rooms[requirement_id]:
            if exclude_user and user_id == exclude_user:
                continue
            await websocket_service.connection_manager.send_to_user(user_id, message)
    
    async def _broadcast_user_status_update(self, user_id: int, status: str):
        """广播用户状态更新"""
        try:
            user_status = self.online_users.get(user_id)
            if not user_status and status != "offline":
                return
            
            message_data = {
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if user_status:
                message_data.update({
                    "username": user_status.username,
                    "last_activity": user_status.last_activity.isoformat(),
                    "current_requirement": user_status.current_requirement,
                    "current_action": user_status.current_action
                })
            
            # 广播给所有在线用户
            message = WSMessage(
                type=RequirementWSMessageType.USER_STATUS_UPDATE,
                data=message_data,
                timestamp=datetime.utcnow().isoformat()
            )
            
            await websocket_service.connection_manager.broadcast(message)
            
        except Exception as e:
            logger.error(f"Error broadcasting user status update: {e}")
    
    async def _handle_user_typing(self, websocket, message):
        """处理用户打字消息"""
        try:
            connection_info = websocket_service.connection_manager.connection_info.get(websocket)
            if not connection_info:
                return
            
            requirement_id = message.data.get("requirement_id")
            is_typing = message.data.get("is_typing", True)
            
            if requirement_id:
                await self.send_typing_indicator(requirement_id, connection_info.user_id, is_typing)
                
        except Exception as e:
            logger.error(f"Error handling user typing: {e}")
    
    async def _handle_user_joined_discussion(self, websocket, message):
        """处理用户加入讨论消息"""
        try:
            connection_info = websocket_service.connection_manager.connection_info.get(websocket)
            if not connection_info:
                return
            
            requirement_id = message.data.get("requirement_id")
            if requirement_id:
                await self.join_discussion(connection_info.user_id, requirement_id)
                
        except Exception as e:
            logger.error(f"Error handling user joined discussion: {e}")
    
    async def _handle_user_left_discussion(self, websocket, message):
        """处理用户离开讨论消息"""
        try:
            connection_info = websocket_service.connection_manager.connection_info.get(websocket)
            if not connection_info:
                return
            
            requirement_id = message.data.get("requirement_id")
            if requirement_id:
                await self.leave_discussion(connection_info.user_id, requirement_id)
                
        except Exception as e:
            logger.error(f"Error handling user left discussion: {e}")
    
    def get_online_users(self) -> List[OnlineUserStatus]:
        """获取在线用户列表"""
        return list(self.online_users.values())
    
    def get_requirement_watchers(self, requirement_id: int) -> List[int]:
        """获取需求监听者列表"""
        return list(self.requirement_watchers.get(requirement_id, set()))
    
    def get_discussion_participants(self, requirement_id: int) -> List[int]:
        """获取讨论参与者列表"""
        return list(self.discussion_rooms.get(requirement_id, set()))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "online_users_count": len(self.online_users),
            "watched_requirements_count": len(self.requirement_watchers),
            "watched_projects_count": len(self.project_watchers),
            "active_discussions_count": len(self.discussion_rooms),
            "total_watchers": sum(len(watchers) for watchers in self.requirement_watchers.values()),
            "total_discussion_participants": sum(len(participants) for participants in self.discussion_rooms.values())
        }


# 全局需求WebSocket服务实例
requirement_websocket_service = RequirementWebSocketService()