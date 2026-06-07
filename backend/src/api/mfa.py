"""
多因素认证API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List

from ..core.database import get_async_db
from ..services.mfa_service import MFAService
from ..utils.auth import get_current_active_user
from ..models.user import User

router = APIRouter(prefix="/api/v1/auth/mfa", tags=["多因素认证"])

class MFASetupRequest(BaseModel):
    """MFA设置请求"""
    pass

class MFAEnableRequest(BaseModel):
    """MFA启用请求"""
    secret: str = Field(..., description="MFA密钥")
    token: str = Field(..., pattern=r'^\d{6}$', description="6位验证码")

class MFADisableRequest(BaseModel):
    """MFA禁用请求"""
    password: str = Field(..., description="用户密码")
    token_or_backup: str = Field(..., description="6位验证码或8位备用代码")

class MFAVerifyRequest(BaseModel):
    """MFA验证请求"""
    token: str = Field(..., description="6位验证码或8位备用代码")

class RegenerateBackupCodesRequest(BaseModel):
    """重新生成备用代码请求"""
    password: str = Field(..., description="用户密码")
    token: str = Field(..., pattern=r'^\d{6}$', description="6位验证码")

class MFASetupResponse(BaseModel):
    """MFA设置响应"""
    secret: str
    qr_code: str
    backup_codes: List[str]
    setup_complete: bool

class MFAStatusResponse(BaseModel):
    """MFA状态响应"""
    enabled: bool
    backup_codes_count: int

@router.get("/status", response_model=MFAStatusResponse, summary="获取MFA状态")
async def get_mfa_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取当前用户的MFA状态"""
    import json
    
    backup_codes_count = 0
    if current_user.mfa_backup_codes:
        try:
            backup_codes = json.loads(current_user.mfa_backup_codes)
            backup_codes_count = len(backup_codes)
        except (json.JSONDecodeError, TypeError):
            backup_codes_count = 0
    
    return {
        "enabled": current_user.mfa_enabled,
        "backup_codes_count": backup_codes_count
    }

@router.post("/setup", response_model=MFASetupResponse, summary="设置MFA")
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """为当前用户设置MFA"""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA已启用")
    
    mfa_service = MFAService(db)
    
    try:
        result = await mfa_service.setup_mfa(current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/enable", summary="启用MFA")
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """启用MFA"""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA已启用")
    
    mfa_service = MFAService(db)
    
    try:
        result = await mfa_service.enable_mfa(
            current_user.id,
            request.secret,
            request.token
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/disable", summary="禁用MFA")
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """禁用MFA"""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA未启用")
    
    mfa_service = MFAService(db)
    
    try:
        result = await mfa_service.disable_mfa(
            current_user.id,
            request.password,
            request.token_or_backup
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify", summary="验证MFA令牌")
async def verify_mfa_token(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """验证MFA令牌"""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA未启用")
    
    mfa_service = MFAService(db)
    
    is_valid = await mfa_service.verify_mfa_token(current_user.id, request.token)
    
    return {
        "success": is_valid,
        "message": "验证成功" if is_valid else "验证失败"
    }

@router.post("/backup-codes/regenerate", summary="重新生成备用代码")
async def regenerate_backup_codes(
    request: RegenerateBackupCodesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """重新生成备用代码"""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA未启用")
    
    mfa_service = MFAService(db)
    
    try:
        backup_codes = await mfa_service.regenerate_backup_codes(
            current_user.id,
            request.password,
            request.token
        )
        return {
            "success": True,
            "message": "备用代码已重新生成",
            "backup_codes": backup_codes
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/backup-codes/count", summary="获取备用代码剩余数量")
async def get_backup_codes_count(
    current_user: User = Depends(get_current_active_user)
):
    """获取备用代码剩余数量"""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA未启用")
    
    import json
    backup_codes_count = 0
    
    if current_user.mfa_backup_codes:
        try:
            backup_codes = json.loads(current_user.mfa_backup_codes)
            backup_codes_count = len(backup_codes)
        except (json.JSONDecodeError, TypeError):
            backup_codes_count = 0
    
    return {
        "count": backup_codes_count,
        "warning": backup_codes_count <= 2
    }