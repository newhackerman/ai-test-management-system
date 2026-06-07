"""
AI助手权限管理API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import get_current_user
from ...services.ai_permission_service import AIPermissionService
from ...decorators.ai_permission import ai_permission_required

router = APIRouter()


class AIPermissionResponse(BaseModel):
    """AI权限响应模型"""
    user_id: int
    permissions: Dict[str, Any]
    summary: Dict[str, Any]


class AIPermissionStatsResponse(BaseModel):
    """AI权限统计响应模型"""
    permission_stats: Dict[str, Any]
    summary: Dict[str, Any]


class PermissionCheckRequest(BaseModel):
    """权限检查请求模型"""
    operation: str
    model_provider: Optional[str] = None
    session_id: Optional[int] = None
    template_id: Optional[int] = None


class PermissionCheckResponse(BaseModel):
    """权限检查响应模型"""
    has_permission: bool
    message: str
    operation: str


@router.post("/initialize", summary="初始化AI权限")
@ai_permission_required("admin_config")
async def initialize_ai_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    初始化AI助手相关权限
    
    只有系统管理员可以执行此操作
    """
    try:
        ai_permission_service = AIPermissionService(db)
        result = await ai_permission_service.initialize_ai_permissions()
        
        return {
            "success": True,
            "message": "AI权限初始化成功",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI权限初始化失败: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=AIPermissionResponse, summary="获取用户AI权限")
@ai_permission_required("admin_monitor")
async def get_user_ai_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取指定用户的AI相关权限
    
    只有管理员或用户本人可以查看
    """
    # 检查是否查看自己的权限
    if user_id != current_user['id']:
        # 需要管理员权限
        ai_permission_service = AIPermissionService(db)
        has_admin_permission, _ = await ai_permission_service.check_user_ai_permission(
            current_user['id'], "ai_admin_monitor"
        )
        if not has_admin_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限查看他人的AI权限信息"
            )
    
    try:
        ai_permission_service = AIPermissionService(db)
        permissions = await ai_permission_service.get_user_ai_permissions(user_id)
        
        return AIPermissionResponse(**permissions)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户AI权限失败: {str(e)}"
        )


@router.get("/me", response_model=AIPermissionResponse, summary="获取当前用户AI权限")
async def get_my_ai_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户的AI相关权限
    """
    try:
        ai_permission_service = AIPermissionService(db)
        permissions = await ai_permission_service.get_user_ai_permissions(current_user['id'])
        
        return AIPermissionResponse(**permissions)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取AI权限失败: {str(e)}"
        )


@router.post("/check", response_model=PermissionCheckResponse, summary="检查AI操作权限")
async def check_ai_permission(
    request: PermissionCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    检查用户是否有执行指定AI操作的权限
    """
    try:
        ai_permission_service = AIPermissionService(db)
        
        # 根据操作类型进行权限检查
        if request.operation == "chat":
            has_permission, message = await ai_permission_service.check_ai_chat_permission(
                current_user['id'], advanced=False
            )
        elif request.operation == "chat_advanced":
            has_permission, message = await ai_permission_service.check_ai_chat_permission(
                current_user['id'], advanced=True
            )
        elif request.operation == "model_use" and request.model_provider:
            has_permission, message = await ai_permission_service.check_ai_model_permission(
                current_user['id'], request.model_provider
            )
        elif request.operation.startswith("session_"):
            action = request.operation.replace("session_", "")
            has_permission, message = await ai_permission_service.check_ai_session_permission(
                current_user['id'], action, request.session_id
            )
        elif request.operation.startswith("template_"):
            action = request.operation.replace("template_", "")
            has_permission, message = await ai_permission_service.check_ai_template_permission(
                current_user['id'], action, request.template_id
            )
        else:
            has_permission, message = await ai_permission_service.check_user_ai_permission(
                current_user['id'], request.operation
            )
        
        return PermissionCheckResponse(
            has_permission=has_permission,
            message=message,
            operation=request.operation
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"权限检查失败: {str(e)}"
        )


@router.get("/stats", response_model=AIPermissionStatsResponse, summary="获取AI权限统计")
@ai_permission_required("admin_monitor")
async def get_ai_permission_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取AI权限使用统计信息
    
    只有管理员可以查看
    """
    try:
        ai_permission_service = AIPermissionService(db)
        stats = await ai_permission_service.get_ai_permission_usage_stats()
        
        return AIPermissionStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取AI权限统计失败: {str(e)}"
        )


@router.get("/available-models", summary="获取用户可用的AI模型")
async def get_available_ai_models(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户可以使用的AI模型列表
    """
    try:
        ai_permission_service = AIPermissionService(db)
        
        # 检查各种模型权限
        models = []
        
        # GPT-4 模型
        has_gpt4, _ = await ai_permission_service.check_ai_model_permission(
            current_user['id'], "openai"
        )
        if has_gpt4:
            models.extend([
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "name": "GPT-4",
                    "description": "最强大的AI模型，适合复杂分析和代码生成",
                    "cost_level": "high"
                },
                {
                    "provider": "openai", 
                    "model": "gpt-3.5-turbo",
                    "name": "GPT-3.5 Turbo",
                    "description": "平衡性能和成本的AI模型",
                    "cost_level": "medium"
                }
            ])
        
        # Claude 模型
        has_claude, _ = await ai_permission_service.check_ai_model_permission(
            current_user['id'], "anthropic"
        )
        if has_claude:
            models.extend([
                {
                    "provider": "anthropic",
                    "model": "claude-3-opus",
                    "name": "Claude-3 Opus",
                    "description": "擅长长文本处理和深度分析",
                    "cost_level": "high"
                },
                {
                    "provider": "anthropic",
                    "model": "claude-3-sonnet",
                    "name": "Claude-3 Sonnet",
                    "description": "平衡型AI模型，适合多种任务",
                    "cost_level": "medium"
                }
            ])
        
        # 中文AI模型
        has_chinese, _ = await ai_permission_service.check_ai_model_permission(
            current_user['id'], "baidu_wenxin"
        )
        if has_chinese:
            models.extend([
                {
                    "provider": "baidu_wenxin",
                    "model": "wenxin-4.0",
                    "name": "文心一言 4.0",
                    "description": "百度的中文AI模型，擅长中文理解",
                    "cost_level": "medium"
                },
                {
                    "provider": "aliyun_tongyi",
                    "model": "qwen-max",
                    "name": "通义千问 Max",
                    "description": "阿里云的中文AI模型",
                    "cost_level": "medium"
                }
            ])
        
        return {
            "success": True,
            "models": models,
            "total_count": len(models)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用模型失败: {str(e)}"
        )


@router.get("/features", summary="获取用户可用的AI功能")
async def get_available_ai_features(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户可以使用的AI功能列表
    """
    try:
        ai_permission_service = AIPermissionService(db)
        
        features = []
        
        # 基础对话功能
        has_basic_chat, _ = await ai_permission_service.check_ai_chat_permission(
            current_user['id'], advanced=False
        )
        if has_basic_chat:
            features.append({
                "code": "basic_chat",
                "name": "基础AI对话",
                "description": "与AI进行基础对话交流",
                "category": "chat"
            })
        
        # 高级对话功能
        has_advanced_chat, _ = await ai_permission_service.check_ai_chat_permission(
            current_user['id'], advanced=True
        )
        if has_advanced_chat:
            features.append({
                "code": "advanced_chat",
                "name": "高级AI对话",
                "description": "使用高级AI功能和模型",
                "category": "chat"
            })
        
        # 智能建议功能
        has_suggestion, _ = await ai_permission_service.check_user_ai_permission(
            current_user['id'], "ai_suggestion_generate"
        )
        if has_suggestion:
            features.append({
                "code": "suggestion_generate",
                "name": "智能建议生成",
                "description": "生成项目优化和改进建议",
                "category": "analysis"
            })
        
        # 高级分析功能
        has_analysis, _ = await ai_permission_service.check_user_ai_permission(
            current_user['id'], "ai_analysis_advanced"
        )
        if has_analysis:
            features.append({
                "code": "advanced_analysis",
                "name": "高级分析功能",
                "description": "深度分析项目数据和趋势",
                "category": "analysis"
            })
        
        # 文件上传功能
        has_file_upload, _ = await ai_permission_service.check_user_ai_permission(
            current_user['id'], "ai_file_upload"
        )
        if has_file_upload:
            features.append({
                "code": "file_upload",
                "name": "文件上传分析",
                "description": "上传文件让AI进行分析",
                "category": "file"
            })
        
        # 模板管理功能
        has_template_create, _ = await ai_permission_service.check_user_ai_permission(
            current_user['id'], "ai_template_create"
        )
        if has_template_create:
            features.append({
                "code": "template_management",
                "name": "提示词模板管理",
                "description": "创建和管理提示词模板",
                "category": "template"
            })
        
        return {
            "success": True,
            "features": features,
            "total_count": len(features),
            "categories": list(set(f["category"] for f in features))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用功能失败: {str(e)}"
        )