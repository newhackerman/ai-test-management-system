"""
需求管理WebSocket API端点
提供需求相关的实时通信接口
"""
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ...core.auth import get_current_user
from ...core.dependencies import get_db
from ...services.requirement_websocket_service import requirement_websocket_service
from ...services.websocket_service import websocket_service
from ...services.requirement_service import RequirementService
from ...services.user_service import UserService
from ...models.user import User


logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.websocket("/ws/requirements/{user_id}")
async def requirement_websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    需求管理WebSocket连接端点
    
    Args:
        websocket: WebSocket连接
        user_id: 用户ID
        token: 认证令牌（可选）
        session_id: 会话ID（可选）
    """
    try:
        # TODO: 在生产环境中应该验证token
        # 这里暂时跳过认证验证，实际使用时需要添加
        
        # 用户上线
        user_service = UserService()
        user = await user_service.get_by_id(user_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return
        
        await requirement_websocket_service.user_online(user_id, user.username)
        
        # 处理WebSocket连接
        await websocket_service.handle_websocket(websocket, user_id, session_id)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # 用户下线
        await requirement_websocket_service.user_offline(user_id)


@router.get("/ws/requirements/stats")
async def get_websocket_stats(current_user: User = Depends(get_current_user)):
    """
    获取WebSocket统计信息
    
    Returns:
        Dict: 统计信息
    """
    try:
        # 检查权限（只有管理员可以查看统计信息）
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view WebSocket statistics"
            )
        
        # 获取基础WebSocket统计
        base_stats = websocket_service.connection_manager.get_stats()
        
        # 获取需求相关统计
        requirement_stats = requirement_websocket_service.get_stats()
        
        return {
            "base_stats": base_stats,
            "requirement_stats": requirement_stats,
            "timestamp": "2024-01-01T00:00:00Z"  # 使用当前时间
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket statistics"
        )


@router.get("/ws/requirements/online-users")
async def get_online_users(current_user: User = Depends(get_current_user)):
    """
    获取在线用户列表
    
    Returns:
        List: 在线用户列表
    """
    try:
        online_users = requirement_websocket_service.get_online_users()
        
        # 过滤敏感信息，只返回必要的用户信息
        filtered_users = []
        for user_status in online_users:
            filtered_users.append({
                "user_id": user_status.user_id,
                "username": user_status.username,
                "status": user_status.status,
                "last_activity": user_status.last_activity.isoformat(),
                "current_requirement": user_status.current_requirement,
                "current_action": user_status.current_action
            })
        
        return {
            "online_users": filtered_users,
            "total_count": len(filtered_users)
        }
        
    except Exception as e:
        logger.error(f"Error getting online users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get online users"
        )


@router.get("/ws/requirements/{requirement_id}/watchers")
async def get_requirement_watchers(
    requirement_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    获取需求监听者列表
    
    Args:
        requirement_id: 需求ID
        
    Returns:
        List: 监听者用户ID列表
    """
    try:
        # 验证需求存在性和访问权限
        requirement_service = RequirementService()
        requirement = await requirement_service.get_by_id(requirement_id)
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        # TODO: 检查用户是否有访问该需求的权限
        
        watchers = requirement_websocket_service.get_requirement_watchers(requirement_id)
        
        return {
            "requirement_id": requirement_id,
            "watchers": watchers,
            "watcher_count": len(watchers)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting requirement watchers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get requirement watchers"
        )


@router.get("/ws/requirements/{requirement_id}/discussion/participants")
async def get_discussion_participants(
    requirement_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    获取需求讨论参与者列表
    
    Args:
        requirement_id: 需求ID
        
    Returns:
        List: 参与者用户ID列表
    """
    try:
        # 验证需求存在性和访问权限
        requirement_service = RequirementService()
        requirement = await requirement_service.get_by_id(requirement_id)
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        # TODO: 检查用户是否有访问该需求的权限
        
        participants = requirement_websocket_service.get_discussion_participants(requirement_id)
        
        return {
            "requirement_id": requirement_id,
            "participants": participants,
            "participant_count": len(participants)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting discussion participants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get discussion participants"
        )


@router.post("/ws/requirements/{requirement_id}/watch")
async def watch_requirement(
    requirement_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    开始监听需求
    
    Args:
        requirement_id: 需求ID
    """
    try:
        # 验证需求存在性和访问权限
        requirement_service = RequirementService()
        requirement = await requirement_service.get_by_id(requirement_id)
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        # TODO: 检查用户是否有访问该需求的权限
        
        await requirement_websocket_service.watch_requirement(current_user.id, requirement_id)
        
        return {
            "message": "Successfully started watching requirement",
            "requirement_id": requirement_id,
            "user_id": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error watching requirement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to watch requirement"
        )


@router.delete("/ws/requirements/{requirement_id}/watch")
async def unwatch_requirement(
    requirement_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    停止监听需求
    
    Args:
        requirement_id: 需求ID
    """
    try:
        await requirement_websocket_service.unwatch_requirement(current_user.id, requirement_id)
        
        return {
            "message": "Successfully stopped watching requirement",
            "requirement_id": requirement_id,
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error unwatching requirement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unwatch requirement"
        )


@router.post("/ws/requirements/{requirement_id}/discussion/join")
async def join_requirement_discussion(
    requirement_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    加入需求讨论
    
    Args:
        requirement_id: 需求ID
    """
    try:
        # 验证需求存在性和访问权限
        requirement_service = RequirementService()
        requirement = await requirement_service.get_by_id(requirement_id)
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found"
            )
        
        # TODO: 检查用户是否有访问该需求的权限
        
        await requirement_websocket_service.join_discussion(current_user.id, requirement_id)
        
        return {
            "message": "Successfully joined requirement discussion",
            "requirement_id": requirement_id,
            "user_id": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining discussion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join discussion"
        )


@router.post("/ws/requirements/{requirement_id}/discussion/leave")
async def leave_requirement_discussion(
    requirement_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    离开需求讨论
    
    Args:
        requirement_id: 需求ID
    """
    try:
        await requirement_websocket_service.leave_discussion(current_user.id, requirement_id)
        
        return {
            "message": "Successfully left requirement discussion",
            "requirement_id": requirement_id,
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error leaving discussion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave discussion"
        )


@router.post("/ws/projects/{project_id}/watch")
async def watch_project(
    project_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    开始监听项目
    
    Args:
        project_id: 项目ID
    """
    try:
        # TODO: 验证项目存在性和访问权限
        
        await requirement_websocket_service.watch_project(current_user.id, project_id)
        
        return {
            "message": "Successfully started watching project",
            "project_id": project_id,
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error watching project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to watch project"
        )


@router.delete("/ws/projects/{project_id}/watch")
async def unwatch_project(
    project_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    停止监听项目
    
    Args:
        project_id: 项目ID
    """
    try:
        await requirement_websocket_service.unwatch_project(current_user.id, project_id)
        
        return {
            "message": "Successfully stopped watching project",
            "project_id": project_id,
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error unwatching project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unwatch project"
        )