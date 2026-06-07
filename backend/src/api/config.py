"""
配置管理 API 路由
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from fastapi.security import HTTPBearer

from ..models.config import Environment, ConfigType, PermissionAction
from ..models.user import User
from ..schemas.config import (
    ConfigCreateRequest, ConfigUpdateRequest, ConfigResponse, ConfigListResponse,
    ConfigSearchRequest, ConfigGroupCreateRequest, ConfigGroupUpdateRequest, ConfigGroupResponse,
    ConfigHistoryResponse, ConfigAuditCreateRequest, ConfigAuditResponse,
    ConfigBatchUpdateRequest, ConfigExportRequest, ConfigImportRequest,
    ConfigValidationRequest, ConfigValidationResponse, ApiResponse
)
from ..services.config import config_service
from ..services.environment import environment_service
from ..services.config_permission import config_permission_service
from ..core.database import get_db
from ..models.config import ConfigGroup
from ..decorators.permission import get_current_user

router = APIRouter()
security = HTTPBearer()


# === 配置管理接口 ===

@router.get("/configs", response_model=ApiResponse[ConfigListResponse])
async def get_configs(
    environment: Environment = Query(default=Environment.PROD, description="环境"),
    group_id: Optional[int] = Query(default=None, description="分组ID"),
    page: int = Query(default=1, ge=1, description="页码"),
    size: int = Query(default=20, ge=1, le=100, description="页大小"),
    search: Optional[str] = Query(default=None, description="搜索关键词"),
    config_type: Optional[ConfigType] = Query(default=None, description="配置类型"),
    is_core: Optional[bool] = Query(default=None, description="是否核心配置"),
    current_user: User = Depends(get_current_user)
):
    """获取配置列表"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, "*", environment, PermissionAction.READ
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问该环境的配置"
            )
        
        result = await config_service.get_configs(
            environment=environment,
            group_id=group_id,
            page=page,
            size=size,
            search=search,
            config_type=config_type,
            is_core=is_core
        )
        
        return ApiResponse(success=True, data=result, message="获取配置列表成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置列表失败: {str(e)}"
        )


@router.get("/configs/{config_key}", response_model=ApiResponse[ConfigResponse])
async def get_config(
    config_key: str = Path(..., description="配置键"),
    environment: Environment = Query(default=Environment.PROD, description="环境"),
    decrypt: bool = Query(default=True, description="是否解密"),
    current_user: User = Depends(get_current_user)
):
    """获取单个配置"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, config_key, environment, PermissionAction.READ
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问该配置"
            )
        
        config_data = await config_service.get_config(config_key, environment, decrypt)
        
        if not config_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="配置不存在"
            )
        
        return ApiResponse(success=True, data=config_data, message="获取配置成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


@router.post("/configs", response_model=ApiResponse[ConfigResponse])
async def create_config(
    config_data: ConfigCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """创建配置"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, config_data.config_key, config_data.environment, PermissionAction.WRITE
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限创建配置"
            )
        
        success, error_msg, result = await config_service.create_config(
            config_data, current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data=result, message="创建配置成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建配置失败: {str(e)}"
        )


@router.put("/configs/{config_key}", response_model=ApiResponse[ConfigResponse])
async def update_config(
    config_key: str = Path(..., description="配置键"),
    config_data: ConfigUpdateRequest = ...,
    environment: Environment = Query(default=Environment.PROD, description="环境"),
    current_user: User = Depends(get_current_user)
):
    """更新配置"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, config_key, environment, PermissionAction.WRITE
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限更新该配置"
            )
        
        success, error_msg, result = await config_service.update_config(
            config_key, config_data, current_user.id, environment
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data=result, message="更新配置成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新配置失败: {str(e)}"
        )


@router.delete("/configs/{config_key}", response_model=ApiResponse[dict])
async def delete_config(
    config_key: str = Path(..., description="配置键"),
    environment: Environment = Query(default=Environment.PROD, description="环境"),
    hard_delete: bool = Query(default=False, description="是否硬删除"),
    current_user: User = Depends(get_current_user)
):
    """删除配置"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, config_key, environment, PermissionAction.DELETE
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除该配置"
            )
        
        success, error_msg = await config_service.delete_config(
            config_key, current_user.id, environment, hard_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data={}, message="删除配置成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除配置失败: {str(e)}"
        )


@router.post("/configs/batch-update", response_model=ApiResponse[dict])
async def batch_update_configs(
    updates: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
):
    """批量更新配置"""
    try:
        # 这里可以添加批量权限检查
        
        success, message, result = await config_service.batch_update_configs(
            updates, current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return ApiResponse(success=True, data=result, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新配置失败: {str(e)}"
        )


# === 环境管理接口 ===

@router.get("/environments", response_model=ApiResponse[List[dict]])
async def get_environments(
    current_user: User = Depends(get_current_user)
):
    """获取环境列表"""
    try:
        environments = await environment_service.get_environments()
        return ApiResponse(success=True, data=environments, message="获取环境列表成功")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取环境列表失败: {str(e)}"
        )


@router.get("/environments/compare", response_model=ApiResponse[dict])
async def compare_environments_static(
    env1: Environment = Query(..., description="鐜1"),
    env2: Environment = Query(..., description="鐜2"),
    current_user: User = Depends(get_current_user)
):
    """姣旇緝鐜閰嶇疆宸紓"""
    try:
        has_env1_permission = await config_permission_service.check_config_permission(
            current_user.id, "*", env1, PermissionAction.READ
        )
        has_env2_permission = await config_permission_service.check_config_permission(
            current_user.id, "*", env2, PermissionAction.READ
        )

        if not has_env1_permission or not has_env2_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="鏃犳潈闄愭瘮杈冪幆澧冮厤缃?"
            )

        comparison = await environment_service.compare_environments(env1, env2)
        return ApiResponse(success=True, data=comparison, message="鐜姣旇緝瀹屾垚")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"鐜姣旇緝澶辫触: {str(e)}"
        )


@router.get("/environments/{env_code}", response_model=ApiResponse[dict])
async def get_environment(
    env_code: str = Path(..., description="环境代码"),
    current_user: User = Depends(get_current_user)
):
    """获取环境信息"""
    try:
        environment = await environment_service.get_environment(env_code)
        
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="环境不存在"
            )
        
        return ApiResponse(success=True, data=environment, message="获取环境信息成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取环境信息失败: {str(e)}"
        )


@router.post("/environments/sync", response_model=ApiResponse[dict])
async def sync_environments(
    source_env: Environment = Query(..., description="源环境"),
    target_env: Environment = Query(..., description="目标环境"),
    config_keys: Optional[List[str]] = Query(default=None, description="配置键列表"),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """环境间配置同步"""
    try:
        # 检查权限
        has_source_permission = await config_permission_service.check_config_permission(
            current_user.id, "*", source_env, PermissionAction.READ
        )
        has_target_permission = await config_permission_service.check_config_permission(
            current_user.id, "*", target_env, PermissionAction.WRITE
        )
        
        if not has_source_permission or not has_target_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限进行环境同步"
            )
        
        success, message, result = await environment_service.sync_configs_between_environments(
            source_env, target_env, config_keys, current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return ApiResponse(success=True, data=result, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"环境同步失败: {str(e)}"
        )


@router.get("/environments/{environment}/statistics", response_model=ApiResponse[dict])
async def get_environment_statistics(
    environment: Environment = Path(..., description="环境"),
    current_user: User = Depends(get_current_user)
):
    """获取环境配置统计"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, "*", environment, PermissionAction.READ
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限查看环境统计"
            )
        
        stats = await environment_service.get_environment_statistics(environment)
        
        return ApiResponse(success=True, data=stats, message="获取环境统计成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取环境统计失败: {str(e)}"
        )


# === 权限管理接口 ===

@router.get("/permissions/check", response_model=ApiResponse[dict])
async def check_config_permission(
    config_key: str = Query(..., description="配置键"),
    environment: Environment = Query(..., description="环境"),
    action: PermissionAction = Query(..., description="操作"),
    current_user: User = Depends(get_current_user)
):
    """检查配置权限"""
    try:
        has_permission = await config_permission_service.check_config_permission(
            current_user.id, config_key, environment, action
        )
        
        return ApiResponse(
            success=True, 
            data={"has_permission": has_permission}, 
            message="权限检查完成"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"权限检查失败: {str(e)}"
        )


@router.post("/permissions/batch-check", response_model=ApiResponse[dict])
async def batch_check_config_permission(
    config_keys: List[str] = Query(..., description="配置键列表"),
    environment: Environment = Query(..., description="环境"),
    action: PermissionAction = Query(..., description="操作"),
    current_user: User = Depends(get_current_user)
):
    """批量检查配置权限"""
    try:
        results = await config_permission_service.check_batch_config_permission(
            current_user.id, config_keys, environment, action
        )
        
        return ApiResponse(success=True, data=results, message="批量权限检查完成")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量权限检查失败: {str(e)}"
        )


@router.get("/permissions/my", response_model=ApiResponse[List[dict]])
async def get_my_config_permissions(
    current_user: User = Depends(get_current_user)
):
    """获取我的配置权限"""
    try:
        permissions = await config_permission_service.get_user_config_permissions(
            current_user.id
        )
        
        return ApiResponse(success=True, data=permissions, message="获取权限列表成功")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取权限列表失败: {str(e)}"
        )


@router.post("/permissions/grant", response_model=ApiResponse[dict])
async def grant_config_permission(
    target_user_id: int = Query(..., description="目标用户ID"),
    permission_data: Dict[str, Any] = ...,
    current_user: User = Depends(get_current_user)
):
    """授予配置权限"""
    try:
        success, error_msg, result = await config_permission_service.grant_config_permission(
            current_user.id, target_user_id, permission_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data=result, message="授予权限成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"授予权限失败: {str(e)}"
        )


@router.delete("/permissions/{permission_id}", response_model=ApiResponse[dict])
async def revoke_config_permission(
    permission_id: int = Path(..., description="权限ID"),
    current_user: User = Depends(get_current_user)
):
    """撤销配置权限"""
    try:
        success, error_msg = await config_permission_service.revoke_config_permission(
            current_user.id, permission_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data={}, message="撤销权限成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"撤销权限失败: {str(e)}"
        )


@router.get("/permissions/statistics", response_model=ApiResponse[dict])
async def get_permission_statistics(
    environment: Optional[Environment] = Query(default=None, description="环境过滤"),
    current_user: User = Depends(get_current_user)
):
    """获取权限统计"""
    try:
        # 检查是否有权限管理权限
        has_permission = await config_permission_service.check_permission_management_access(
            current_user.id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限查看权限统计"
            )
        
        stats = await config_permission_service.get_permission_statistics(environment)
        
        return ApiResponse(success=True, data=stats, message="获取权限统计成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取权限统计失败: {str(e)}"
        )


# === 配置分组管理接口 ===

@router.get("/groups", response_model=ApiResponse[List[dict]])
async def get_config_groups(
    current_user: User = Depends(get_current_user)
):
    """获取配置分组列表"""
    try:
        db = next(get_db())
        try:
            groups = db.query(ConfigGroup).filter(
                ConfigGroup.is_enabled.is_(True)
            ).order_by(ConfigGroup.sort_order.asc()).all()
            
            group_list = [{
                "id": group.id,
                "group_name": group.group_name,
                "group_code": group.group_code,
                "parent_id": group.parent_id,
                "level": group.level,
                "path": group.path,
                "sort_order": group.sort_order,
                "description": group.description,
                "icon": group.icon,
                "color": group.color,
                "is_system": group.is_system,
                "is_enabled": group.is_enabled,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None,
                "created_by": group.created_by,
                "updated_by": group.updated_by
            } for group in groups]
            
            return ApiResponse(success=True, data=group_list, message="获取分组列表成功")
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分组列表失败: {str(e)}"
        )


@router.post("/groups", response_model=ApiResponse[dict])
async def create_config_group(
    group_data: dict,
    current_user: User = Depends(get_current_user)
):
    """创建配置分组"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_permission_management_access(
            current_user.id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限管理配置分组"
            )
        
        db = next(get_db())
        try:
            # 检查分组代码是否已存在
            existing = db.query(ConfigGroup).filter(
                ConfigGroup.group_code == group_data["group_code"]
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="分组代码已存在"
                )
            
            # 创建分组
            group = ConfigGroup(
                group_name=group_data["group_name"],
                group_code=group_data["group_code"],
                parent_id=group_data.get("parent_id", 0),
                level=group_data.get("level", 1),
                path=group_data.get("path"),
                sort_order=group_data.get("sort_order", 0),
                description=group_data.get("description"),
                icon=group_data.get("icon"),
                color=group_data.get("color"),
                is_system=group_data.get("is_system", False),
                is_enabled=group_data.get("is_enabled", True),
                created_by=current_user.id,
                updated_by=current_user.id
            )
            
            db.add(group)
            db.commit()
            db.refresh(group)
            
            group_dict = {
                "id": group.id,
                "group_name": group.group_name,
                "group_code": group.group_code,
                "parent_id": group.parent_id,
                "level": group.level,
                "sort_order": group.sort_order,
                "description": group.description,
                "icon": group.icon,
                "color": group.color,
                "is_system": group.is_system,
                "is_enabled": group.is_enabled,
                "created_at": group.created_at.isoformat() if group.created_at else None
            }
            
            return ApiResponse(success=True, data=group_dict, message="创建分组成功")
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建分组失败: {str(e)}"
        )


@router.put("/groups/{group_id}", response_model=ApiResponse[dict])
async def update_config_group(
    group_id: int = Path(..., description="分组ID"),
    group_data: dict = ...,
    current_user: User = Depends(get_current_user)
):
    """更新配置分组"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_permission_management_access(
            current_user.id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限管理配置分组"
            )
        
        db = next(get_db())
        try:
            group = db.query(ConfigGroup).filter(
                ConfigGroup.id == group_id
            ).first()
            
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="分组不存在"
                )
            
            # 更新字段
            if "group_name" in group_data:
                group.group_name = group_data["group_name"]
            if "description" in group_data:
                group.description = group_data["description"]
            if "icon" in group_data:
                group.icon = group_data["icon"]
            if "color" in group_data:
                group.color = group_data["color"]
            if "sort_order" in group_data:
                group.sort_order = group_data["sort_order"]
            if "is_enabled" in group_data:
                group.is_enabled = group_data["is_enabled"]
            
            group.updated_by = current_user.id
            
            db.commit()
            db.refresh(group)
            
            group_dict = {
                "id": group.id,
                "group_name": group.group_name,
                "group_code": group.group_code,
                "description": group.description,
                "icon": group.icon,
                "color": group.color,
                "sort_order": group.sort_order,
                "is_enabled": group.is_enabled,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            }
            
            return ApiResponse(success=True, data=group_dict, message="更新分组成功")
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新分组失败: {str(e)}"
        )


@router.delete("/groups/{group_id}", response_model=ApiResponse[dict])
async def delete_config_group(
    group_id: int = Path(..., description="分组ID"),
    current_user: User = Depends(get_current_user)
):
    """删除配置分组"""
    try:
        # 检查权限
        has_permission = await config_permission_service.check_permission_management_access(
            current_user.id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限管理配置分组"
            )
        
        db = next(get_db())
        try:
            group = db.query(ConfigGroup).filter(
                ConfigGroup.id == group_id
            ).first()
            
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="分组不存在"
                )
            
            if group.is_system:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="系统分组不允许删除"
                )
            
            # ConfigGroup has no deleted_at column; disabling is the supported soft-delete state.
            group.is_enabled = False
            group.updated_by = current_user.id
            
            db.commit()
            
            return ApiResponse(success=True, data={}, message="删除分组成功")
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除分组失败: {str(e)}"
        )
