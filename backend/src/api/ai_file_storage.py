"""
AI助手文件存储API接口
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from datetime import datetime
import hashlib
import aiofiles

from ..core.database import get_async_session
from ..services.auth import get_current_user
from ..services.ai_file_storage_service import AIFileStorageService
from ..models.ai_file_storage import FileCategory, FileType, FileStatus, AIFileShare, AIFileStorage
from ..models.user import User
from ..schemas.ai_file_storage import (
    FileUploadResponse, FileInfoResponse, FileListResponse, 
    FileShareResponse, StorageStatsResponse, FileShareRequest
)
from ..utils.logger import logger

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(..., description="上传的文件"),
    category: FileCategory = Form(..., description="文件分类"),
    session_id: Optional[int] = Form(None, description="关联会话ID"),
    message_id: Optional[int] = Form(None, description="关联消息ID"),
    template_id: Optional[int] = Form(None, description="关联模板ID"),
    description: Optional[str] = Form(None, description="文件描述"),
    tags: Optional[str] = Form(None, description="文件标签"),
    is_temporary: bool = Form(False, description="是否临时文件"),
    expires_hours: Optional[int] = Form(None, description="过期小时数"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """上传文件"""
    try:
        service = AIFileStorageService(db)
        file_record = await service.upload_file(
            file=file,
            user_id=current_user.id,
            category=category,
            session_id=session_id,
            message_id=message_id,
            template_id=template_id,
            description=description,
            tags=tags,
            is_temporary=is_temporary,
            expires_hours=expires_hours
        )
        
        return FileUploadResponse(
            id=file_record.id,
            original_filename=file_record.original_filename,
            file_url=file_record.file_url,
            file_type=file_record.file_type,
            file_size=file_record.file_size,
            mime_type=file_record.mime_type,
            created_at=file_record.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload file error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败"
        )


@router.get("/stats", response_model=StorageStatsResponse, summary="获取存储统计")
async def get_storage_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取存储统计信息"""
    service = AIFileStorageService(db)
    stats = await service.get_storage_stats(current_user.id)
    
    return StorageStatsResponse(
        total_files=stats["total_files"],
        total_size=stats["total_size"],
        category_stats=stats["category_stats"],
        type_stats=stats["type_stats"]
    )


@router.get("/{file_id}", response_model=FileInfoResponse, summary="获取文件信息")
async def get_file_info(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取文件信息"""
    service = AIFileStorageService(db)
    file_record = await service.get_file(file_id, current_user.id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或无权限访问"
        )
    
    return FileInfoResponse(
        id=file_record.id,
        original_filename=file_record.original_filename,
        stored_filename=file_record.stored_filename,
        file_url=file_record.file_url,
        file_type=file_record.file_type,
        file_category=file_record.file_category,
        mime_type=file_record.mime_type,
        file_size=file_record.file_size,
        file_hash=file_record.file_hash,
        description=file_record.description,
        tags=file_record.tags,
        status=file_record.status,
        is_public=file_record.is_public,
        is_temporary=file_record.is_temporary,
        access_count=file_record.access_count,
        download_count=file_record.download_count,
        expires_at=file_record.expires_at,
        created_at=file_record.created_at,
        updated_at=file_record.updated_at
    )


@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """下载文件"""
    try:
        service = AIFileStorageService(db)
        file_path, original_filename, mime_type = await service.download_file(
            file_id, current_user.id
        )
        
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type=mime_type,
            headers={"Content-Disposition": f"attachment; filename={original_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download file error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件下载失败"
        )


@router.get("/{file_id}/preview", summary="预览文件")
async def preview_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """预览文件"""
    try:
        service = AIFileStorageService(db)
        file_path, original_filename, mime_type = await service.download_file(
            file_id, current_user.id
        )
        
        # 对于图片和文本文件，支持在线预览
        if mime_type.startswith(('image/', 'text/', 'application/json')):
            return FileResponse(
                path=file_path,
                media_type=mime_type,
                headers={"Content-Disposition": f"inline; filename={original_filename}"}
            )
        else:
            # 其他文件类型直接下载
            return FileResponse(
                path=file_path,
                filename=original_filename,
                media_type=mime_type,
                headers={"Content-Disposition": f"attachment; filename={original_filename}"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview file error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件预览失败"
        )


@router.delete("/{file_id}", summary="删除文件")
async def delete_file(
    file_id: int,
    permanent: bool = Query(False, description="是否永久删除"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """删除文件"""
    service = AIFileStorageService(db)
    success = await service.delete_file(file_id, current_user.id, permanent)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或无权限删除"
        )
    
    return {"message": "文件删除成功"}


@router.get("/", response_model=FileListResponse, summary="获取文件列表")
async def list_files(
    category: Optional[FileCategory] = Query(None, description="文件分类"),
    file_type: Optional[FileType] = Query(None, description="文件类型"),
    session_id: Optional[int] = Query(None, description="会话ID"),
    message_id: Optional[int] = Query(None, description="消息ID"),
    template_id: Optional[int] = Query(None, description="模板ID"),
    include_public: bool = Query(True, description="是否包含公开文件"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取文件列表"""
    service = AIFileStorageService(db)
    files, total = await service.list_files(
        user_id=current_user.id,
        category=category,
        file_type=file_type,
        session_id=session_id,
        message_id=message_id,
        template_id=template_id,
        include_public=include_public,
        page=page,
        size=size
    )
    
    file_list = [
        FileInfoResponse(
            id=file.id,
            original_filename=file.original_filename,
            stored_filename=file.stored_filename,
            file_url=file.file_url,
            file_type=file.file_type,
            file_category=file.file_category,
            mime_type=file.mime_type,
            file_size=file.file_size,
            file_hash=file.file_hash,
            description=file.description,
            tags=file.tags,
            status=file.status,
            is_public=file.is_public,
            is_temporary=file.is_temporary,
            access_count=file.access_count,
            download_count=file.download_count,
            expires_at=file.expires_at,
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        for file in files
    ]
    
    return FileListResponse(
        files=file_list,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.post("/{file_id}/share", response_model=FileShareResponse, summary="创建文件分享链接")
async def create_share_link(
    file_id: int,
    share_request: FileShareRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """创建文件分享链接"""
    try:
        service = AIFileStorageService(db)
        share_record = await service.create_share_link(
            file_id=file_id,
            user_id=current_user.id,
            expires_hours=share_request.expires_hours,
            password=share_request.password,
            can_download=share_request.can_download,
            can_preview=share_request.can_preview,
            max_downloads=share_request.max_downloads,
            max_views=share_request.max_views
        )
        
        return FileShareResponse(
            id=share_record.id,
            share_token=share_record.share_token,
            share_url=share_record.share_url,
            can_download=share_record.can_download,
            can_preview=share_record.can_preview,
            max_downloads=share_record.max_downloads,
            max_views=share_record.max_views,
            download_count=share_record.download_count,
            view_count=share_record.view_count,
            expires_at=share_record.expires_at,
            created_at=share_record.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create share link error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建分享链接失败"
        )


@router.get("/share/{share_token}", summary="通过分享链接访问文件")
async def access_shared_file(
    share_token: str,
    action: str = Query("preview", description="操作类型: preview/download"),
    password: Optional[str] = Query(None, description="分享密码"),
    request: Request = None,
    db: AsyncSession = Depends(get_async_session)
):
    """通过分享链接访问文件（无需登录）

    按顺序校验：分享存在且启用、未过期、密码正确、操作被允许、
    次数未达上限；然后按 action 返回文件元数据（preview）或文件流
    （download），并更新浏览/下载计数与访问日志。
    """
    if action not in ("preview", "download"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="操作类型仅支持 preview 或 download"
        )
    try:
        result = await db.execute(
            select(AIFileShare).where(AIFileShare.share_token == share_token)
        )
        share = result.scalar_one_or_none()
        if not share or not share.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分享链接不存在或已失效"
            )
        if share.expires_at and share.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="分享链接已过期"
            )
        if share.share_password:
            if not password or hashlib.sha256(password.encode()).hexdigest() != share.share_password:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="分享密码错误"
                )
        if action == "download":
            if not share.can_download:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="该分享不允许下载"
                )
            if share.max_downloads is not None and share.download_count >= share.max_downloads:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="下载次数已达上限"
                )
        else:
            if not share.can_preview:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="该分享不允许预览"
                )
            if share.max_views is not None and share.view_count >= share.max_views:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="查看次数已达上限"
                )

        file_result = await db.execute(
            select(AIFileStorage).where(AIFileStorage.id == share.file_id)
        )
        file_record = file_result.scalar_one_or_none()
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        file_path = Path(file_record.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )

        service = AIFileStorageService(db)
        ip_address = request.client.host if request is not None and request.client else None
        if action == "download":
            share.download_count += 1
            share.last_accessed_at = datetime.utcnow()
            await db.commit()
            await service._update_download_stats(file_record.id)
            await service._log_file_access(
                file_record.id, None, "download",
                bytes_transferred=file_record.file_size,
                ip_address=ip_address, share_id=share.id
            )
            return FileResponse(
                path=file_path,
                filename=file_record.original_filename,
                media_type=file_record.mime_type,
                headers={"Content-Disposition": f"attachment; filename={file_record.original_filename}"}
            )

        share.view_count += 1
        share.last_accessed_at = datetime.utcnow()
        await db.commit()
        await service._update_access_stats(file_record.id)
        await service._log_file_access(
            file_record.id, None, "view", ip_address=ip_address, share_id=share.id
        )
        return {
            "file": {
                "id": file_record.id,
                "original_filename": file_record.original_filename,
                "mime_type": file_record.mime_type,
                "file_size": file_record.file_size,
                "file_type": file_record.file_type.value if hasattr(file_record.file_type, "value") else file_record.file_type,
                "created_at": file_record.created_at.isoformat() if file_record.created_at else None,
            },
            "share": {
                "can_download": share.can_download,
                "can_preview": share.can_preview,
                "expires_at": share.expires_at.isoformat() if share.expires_at else None,
                "download_count": share.download_count,
                "view_count": share.view_count,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Access shared file error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="访问分享文件失败"
        )


@router.post("/cleanup", summary="清理过期文件")
async def cleanup_expired_files(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """清理过期文件（管理员功能）"""
    # 仅超级管理员可以清理：JWT 里不含 is_superuser，必须查库判断
    admin_result = await db.execute(
        select(User.is_superuser).where(User.id == current_user.id)
    )
    if not admin_result.scalar():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可以清理过期文件"
        )
    service = AIFileStorageService(db)
    cleaned_count = await service.cleanup_expired_files()
    
    return {
        "message": f"清理完成，共清理 {cleaned_count} 个过期文件",
        "cleaned_count": cleaned_count
    }


# 批量操作接口

@router.post("/batch/upload", summary="批量上传文件")
async def batch_upload_files(
    files: List[UploadFile] = File(..., description="上传的文件列表"),
    category: FileCategory = Form(..., description="文件分类"),
    session_id: Optional[int] = Form(None, description="关联会话ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """批量上传文件"""
    service = AIFileStorageService(db)
    results = []
    
    for file in files:
        try:
            file_record = await service.upload_file(
                file=file,
                user_id=current_user.id,
                category=category,
                session_id=session_id
            )
            results.append({
                "filename": file.filename,
                "success": True,
                "file_id": file_record.id,
                "file_url": file_record.file_url
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}


@router.delete("/batch", summary="批量删除文件")
async def batch_delete_files(
    file_ids: List[int],
    permanent: bool = Query(False, description="是否永久删除"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """批量删除文件"""
    service = AIFileStorageService(db)
    results = []
    
    for file_id in file_ids:
        success = await service.delete_file(file_id, current_user.id, permanent)
        results.append({
            "file_id": file_id,
            "success": success
        })
    
    return {"results": results}