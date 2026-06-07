"""
会议管理API模块

本模块提供在线会议相关的REST API接口，包括：
- 会议基础CRUD操作
- 会议参与者管理
- 会议加入和控制
- WebRTC信令处理
- 屏幕共享和协作
- 录制管理
- AI分析和纪要
- 项目集成管理
"""
from fastapi import APIRouter
from .meeting_routes import router as meeting_router
from .participant_routes import router as participant_router
from .meeting_control_routes import router as control_router
from .webrtc_routes import router as webrtc_router
from .collaboration_routes import router as collaboration_router
from .recording_routes import router as recording_router
from .ai_analysis_routes import router as ai_analysis_router
from .project_integration_routes import router as project_integration_router

# 创建会议管理主路由
meetings_router = APIRouter()

# 注册子路由
meetings_router.include_router(meeting_router, prefix="", tags=["会议管理"])
meetings_router.include_router(participant_router, prefix="/{meeting_id}/participants", tags=["参与者管理"])
meetings_router.include_router(control_router, prefix="", tags=["会议控制"])
meetings_router.include_router(webrtc_router, prefix="/{meeting_id}/webrtc", tags=["WebRTC信令"])
meetings_router.include_router(collaboration_router, prefix="/{meeting_id}", tags=["协作功能"])
meetings_router.include_router(recording_router, prefix="/recordings", tags=["录制管理"])
meetings_router.include_router(ai_analysis_router, prefix="/{meeting_id}", tags=["AI分析"])
meetings_router.include_router(project_integration_router, tags=["项目集成"])

# 导出主路由
router = meetings_router