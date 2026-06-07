"""
用户个人资料API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import os
import uuid
from PIL import Image
import io

from ..core.database import get_async_db
from ..services.user import UserService
from ..services.auth import AuthService
from ..utils.auth import get_current_active_user
from ..models.user import User
from ..schemas.user import UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/api/v1/users", tags=["用户个人资料"])

@router.get("/profile", response_model=UserProfileResponse, summary="获取个人资料")
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取当前用户的个人资料"""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user.id)
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
        "phone": user.phone,
        "avatar": user.avatar,
        "bio": user.bio,
        "gender": user.gender.value if user.gender else None,
        "birthday": user.birthday,
        "location": user.location,
        "website": user.website,
        "language": user.language,
        "timezone": user.timezone,
        "theme": user.theme,
        "email_notifications": user.email_notifications,
        "sms_notifications": user.sms_notifications,
        "push_notifications": user.push_notifications,
        "is_email_verified": user.is_email_verified,
        "is_phone_verified": user.is_phone_verified,
        "mfa_enabled": user.mfa_enabled,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }

@router.put("/profile", response_model=UserProfileResponse, summary="更新个人资料")
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """更新当前用户的个人资料"""
    user_service = UserService(db)
    
    # 构建更新数据
    update_data = {}
    if profile_data.nickname is not None:
        update_data["nickname"] = profile_data.nickname
    if profile_data.phone is not None:
        update_data["phone"] = profile_data.phone
    if profile_data.bio is not None:
        update_data["bio"] = profile_data.bio
    if profile_data.gender is not None:
        update_data["gender"] = profile_data.gender
    if profile_data.birthday is not None:
        update_data["birthday"] = profile_data.birthday
    if profile_data.location is not None:
        update_data["location"] = profile_data.location
    if profile_data.website is not None:
        update_data["website"] = profile_data.website
    if profile_data.language is not None:
        update_data["language"] = profile_data.language
    if profile_data.timezone is not None:
        update_data["timezone"] = profile_data.timezone
    if profile_data.theme is not None:
        update_data["theme"] = profile_data.theme
    if profile_data.email_notifications is not None:
        update_data["email_notifications"] = profile_data.email_notifications
    if profile_data.sms_notifications is not None:
        update_data["sms_notifications"] = profile_data.sms_notifications
    if profile_data.push_notifications is not None:
        update_data["push_notifications"] = profile_data.push_notifications
    
    try:
        updated_user = await user_service.update_user(current_user.id, update_data)
        return await get_user_profile(updated_user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/profile/avatar", summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """上传用户头像"""
    # 检查文件类型
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只能上传图片文件")
    
    # 检查文件大小 (5MB)
    if file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像文件不能超过5MB")
    
    try:
        # 读取图片
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # 调整图片大小
        if image.size[0] > 300 or image.size[1] > 300:
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        # 转换为RGB
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # 生成唯一文件名
        file_extension = 'jpg'
        filename = f"{uuid.uuid4()}.{file_extension}"
        
        # 创建上传目录
        upload_dir = "uploads/avatars"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_dir, filename)
        image.save(file_path, 'JPEG', quality=85)
        
        # 更新用户头像路径
        user_service = UserService(db)
        avatar_url = f"/static/avatars/{filename}"
        await user_service.update_user(current_user.id, {"avatar": avatar_url})
        
        return {
            "success": True,
            "message": "头像上传成功",
            "avatar_url": avatar_url
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"头像上传失败: {str(e)}")

@router.delete("/profile/avatar", summary="删除用户头像")
async def delete_avatar(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """删除用户头像，恢复为默认头像"""
    user_service = UserService(db)
    
    # 删除头像文件
    if current_user.avatar and current_user.avatar.startswith('/static/avatars/'):
        file_path = f"uploads/avatars/{os.path.basename(current_user.avatar)}"
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # 更新数据库
    default_avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={current_user.username}"
    await user_service.update_user(current_user.id, {"avatar": default_avatar})
    
    return {
        "success": True,
        "message": "头像已删除，恢复为默认头像",
        "avatar_url": default_avatar
    }

@router.get("/profile/security", summary="获取用户安全设置")
async def get_security_settings(
    current_user: User = Depends(get_current_active_user)
):
    """获取用户安全相关设置"""
    return {
        "mfa_enabled": current_user.mfa_enabled,
        "email_verified": current_user.is_email_verified,
        "phone_verified": current_user.is_phone_verified,
        "last_login_at": current_user.last_login_at,
        "last_login_ip": current_user.last_login_ip,
        "password_updated_at": current_user.password_updated_at,
        "failed_login_attempts": current_user.failed_login_attempts,
        "locked_until": current_user.locked_until
    }