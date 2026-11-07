"""
AI助手文件存储服务
"""
import os
import hashlib
import uuid
import json
import aiofiles
import mimetypes
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, BinaryIO
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.ai_file_storage import (
    AIFileStorage, AIFileShare, AIFileAccessLog,
    FileType, FileCategory, StorageProvider, FileStatus
)
from ..core.config import settings
from ..utils.logger import logger


class AIFileStorageService:
    """AI文件存储服务"""
    
    # 文件类型映射
    FILE_TYPE_MAPPING = {
        'image/jpeg': FileType.IMAGE,
        'image/png': FileType.IMAGE,
        'image/gif': FileType.IMAGE,
        'image/webp': FileType.IMAGE,
        'image/svg+xml': FileType.IMAGE,
        'application/pdf': FileType.DOCUMENT,
        'application/msword': FileType.DOCUMENT,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType.DOCUMENT,
        'application/vnd.ms-excel': FileType.DOCUMENT,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileType.DOCUMENT,
        'text/plain': FileType.DOCUMENT,
        'text/markdown': FileType.DOCUMENT,
        'text/csv': FileType.DATA,
        'application/json': FileType.DATA,
        'application/xml': FileType.DATA,
        'audio/mpeg': FileType.AUDIO,
        'audio/wav': FileType.AUDIO,
        'audio/ogg': FileType.AUDIO,
        'video/mp4': FileType.VIDEO,
        'video/avi': FileType.VIDEO,
        'video/mov': FileType.VIDEO,
        'application/zip': FileType.ARCHIVE,
        'application/x-rar-compressed': FileType.ARCHIVE,
        'application/x-7z-compressed': FileType.ARCHIVE,
        'text/x-python': FileType.CODE,
        'text/javascript': FileType.CODE,
        'text/html': FileType.CODE,
        'text/css': FileType.CODE,
    }
    
    # 允许的文件类型
    ALLOWED_MIME_TYPES = {
        FileCategory.CHAT_ATTACHMENT: [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/markdown',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv', 'application/json'
        ],
        FileCategory.PROMPT_TEMPLATE: [
            'text/plain', 'text/markdown', 'application/json', 'text/yaml'
        ],
        FileCategory.EXPORT_DATA: [
            'application/json', 'text/csv', 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/pdf', 'text/plain'
        ],
        FileCategory.USER_UPLOAD: [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/markdown',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv', 'application/json', 'application/zip'
        ]
    }
    
    # 文件大小限制 (字节)
    MAX_FILE_SIZES = {
        FileCategory.CHAT_ATTACHMENT: 50 * 1024 * 1024,  # 50MB
        FileCategory.PROMPT_TEMPLATE: 1 * 1024 * 1024,   # 1MB
        FileCategory.EXPORT_DATA: 100 * 1024 * 1024,     # 100MB
        FileCategory.USER_UPLOAD: 50 * 1024 * 1024,      # 50MB
        FileCategory.AI_GENERATED: 10 * 1024 * 1024,     # 10MB
        FileCategory.TEMP_FILE: 20 * 1024 * 1024,        # 20MB
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_root = Path(settings.UPLOAD_DIR)
        self.storage_root.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self,
        file: UploadFile,
        user_id: int,
        category: FileCategory,
        session_id: Optional[int] = None,
        message_id: Optional[int] = None,
        template_id: Optional[int] = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        is_temporary: bool = False,
        expires_hours: Optional[int] = None
    ) -> AIFileStorage:
        """
        上传文件
        
        Args:
            file: 上传的文件
            user_id: 用户ID
            category: 文件分类
            session_id: 会话ID
            message_id: 消息ID
            template_id: 模板ID
            description: 文件描述
            tags: 文件标签
            is_temporary: 是否临时文件
            expires_hours: 过期小时数
            
        Returns:
            文件存储记录
        """
        try:
            # 验证文件
            await self._validate_file(file, category)
            
            # 读取文件内容
            content = await file.read()
            file_size = len(content)
            
            # 计算文件哈希
            file_hash = hashlib.sha256(content).hexdigest()
            
            # 检查是否已存在相同文件
            existing_file = await self._find_existing_file(file_hash, user_id)
            if existing_file and not is_temporary:
                logger.info(f"File already exists: {file_hash}")
                return existing_file
            
            # 生成存储文件名和路径
            stored_filename = self._generate_filename(file.filename, file_hash)
            file_path = self._get_file_path(category, stored_filename)
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # 生成文件URL
            file_url = self._generate_file_url(category, stored_filename)
            
            # 确定文件类型
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
            file_type = self.FILE_TYPE_MAPPING.get(mime_type, FileType.OTHER)
            
            # 设置过期时间
            expires_at = None
            if expires_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            elif is_temporary:
                expires_at = datetime.utcnow() + timedelta(hours=24)  # 临时文件24小时过期
            
            # 创建数据库记录
            file_record = AIFileStorage(
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=str(file_path),
                file_url=file_url,
                file_type=file_type,
                file_category=category,
                mime_type=mime_type,
                file_size=file_size,
                file_hash=file_hash,
                storage_provider=StorageProvider.LOCAL,
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                template_id=template_id,
                description=description,
                tags=tags,
                status=FileStatus.ACTIVE,
                is_temporary=is_temporary,
                expires_at=expires_at
            )
            
            self.db.add(file_record)
            await self.db.commit()
            await self.db.refresh(file_record)
            
            # 记录访问日志
            await self._log_file_access(
                file_record.id, user_id, 'upload', 
                success=True, bytes_transferred=file_size
            )
            
            logger.info(f"File uploaded successfully: {file_record.id}")
            return file_record
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to upload file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件上传失败: {str(e)}"
            )
    
    async def get_file(self, file_id: int, user_id: Optional[int] = None) -> Optional[AIFileStorage]:
        """
        获取文件信息
        
        Args:
            file_id: 文件ID
            user_id: 用户ID (用于权限检查)
            
        Returns:
            文件记录
        """
        query = select(AIFileStorage).where(
            and_(
                AIFileStorage.id == file_id,
                AIFileStorage.status != FileStatus.DELETED
            )
        )
        
        # 如果指定了用户ID，检查权限
        if user_id:
            query = query.where(
                or_(
                    AIFileStorage.user_id == user_id,
                    AIFileStorage.is_public == True
                )
            )
        
        result = await self.db.execute(query)
        file_record = result.scalar_one_or_none()
        
        if file_record:
            # 更新访问统计
            await self._update_access_stats(file_record.id)
            
            # 记录访问日志
            await self._log_file_access(file_record.id, user_id, 'view')
        
        return file_record
    
    async def download_file(self, file_id: int, user_id: Optional[int] = None) -> Tuple[Path, str, str]:
        """
        下载文件
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
            
        Returns:
            (文件路径, 原始文件名, MIME类型)
        """
        file_record = await self.get_file(file_id, user_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权限访问"
            )
        
        file_path = Path(file_record.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 更新下载统计
        await self._update_download_stats(file_record.id)
        
        # 记录访问日志
        await self._log_file_access(
            file_record.id, user_id, 'download',
            bytes_transferred=file_record.file_size
        )
        
        return file_path, file_record.original_filename, file_record.mime_type
    
    async def delete_file(self, file_id: int, user_id: int, permanent: bool = False) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
            permanent: 是否永久删除
            
        Returns:
            是否删除成功
        """
        try:
            # 获取文件记录
            query = select(AIFileStorage).where(
                and_(
                    AIFileStorage.id == file_id,
                    AIFileStorage.user_id == user_id,
                    AIFileStorage.status != FileStatus.DELETED
                )
            )
            result = await self.db.execute(query)
            file_record = result.scalar_one_or_none()
            
            if not file_record:
                return False
            
            if permanent:
                # 永久删除：先记删除日志（文件行还在，访问日志的外键才成立），
                # 再删该文件的访问日志（它们外键引用分享行），然后删分享行
                # （分享行外键引用文件行），最后删物理文件与数据库记录
                await self._log_file_access(file_record.id, user_id, 'delete')
                await self.db.execute(
                    delete(AIFileAccessLog).where(AIFileAccessLog.file_id == file_id)
                )
                await self.db.execute(
                    delete(AIFileShare).where(AIFileShare.file_id == file_id)
                )
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    file_path.unlink()

                await self.db.delete(file_record)
                await self.db.commit()
                logger.info(f"File deleted: {file_id}, permanent: {permanent}")
                return True
            else:
                # 软删除：只更新状态
                file_record.status = FileStatus.DELETED
                file_record.deleted_at = datetime.utcnow()

            await self.db.commit()

            # 记录访问日志
            await self._log_file_access(file_record.id, user_id, 'delete')

            logger.info(f"File deleted: {file_id}, permanent: {permanent}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete file {file_id}: {str(e)}")
            return False
    
    async def list_files(
        self,
        user_id: Optional[int] = None,
        category: Optional[FileCategory] = None,
        file_type: Optional[FileType] = None,
        session_id: Optional[int] = None,
        message_id: Optional[int] = None,
        template_id: Optional[int] = None,
        include_public: bool = True,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[AIFileStorage], int]:
        """
        获取文件列表
        
        Args:
            user_id: 用户ID
            category: 文件分类
            file_type: 文件类型
            session_id: 会话ID
            message_id: 消息ID
            template_id: 模板ID
            include_public: 是否包含公开文件
            page: 页码
            size: 每页大小
            
        Returns:
            (文件列表, 总数)
        """
        # 构建查询条件
        conditions = [AIFileStorage.status != FileStatus.DELETED]
        
        if user_id:
            if include_public:
                conditions.append(
                    or_(
                        AIFileStorage.user_id == user_id,
                        AIFileStorage.is_public == True
                    )
                )
            else:
                conditions.append(AIFileStorage.user_id == user_id)
        
        if category:
            conditions.append(AIFileStorage.file_category == category)
        
        if file_type:
            conditions.append(AIFileStorage.file_type == file_type)
        
        if session_id:
            conditions.append(AIFileStorage.session_id == session_id)
        
        if message_id:
            conditions.append(AIFileStorage.message_id == message_id)
        
        if template_id:
            conditions.append(AIFileStorage.template_id == template_id)
        
        # 查询总数
        count_query = select(func.count(AIFileStorage.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        # 查询文件列表
        query = (
            select(AIFileStorage)
            .where(and_(*conditions))
            .order_by(AIFileStorage.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        
        result = await self.db.execute(query)
        files = result.scalars().all()
        
        return list(files), total
    
    async def create_share_link(
        self,
        file_id: int,
        user_id: int,
        expires_hours: Optional[int] = None,
        password: Optional[str] = None,
        can_download: bool = True,
        can_preview: bool = True,
        max_downloads: Optional[int] = None,
        max_views: Optional[int] = None
    ) -> AIFileShare:
        """
        创建文件分享链接
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
            expires_hours: 过期小时数
            password: 分享密码
            can_download: 允许下载
            can_preview: 允许预览
            max_downloads: 最大下载次数
            max_views: 最大查看次数
            
        Returns:
            分享记录
        """
        # 检查文件权限
        file_record = await self.get_file(file_id, user_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权限访问"
            )
        
        # 生成分享令牌
        share_token = uuid.uuid4().hex
        share_url = f"/api/v1/ai/files/share/{share_token}"
        
        # 设置过期时间
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        # 创建分享记录
        share_record = AIFileShare(
            file_id=file_id,
            user_id=user_id,
            share_token=share_token,
            share_url=share_url,
            # 分享密码只存 SHA256 摘要，不存明文
            share_password=hashlib.sha256(password.encode()).hexdigest() if password else None,
            can_download=can_download,
            can_preview=can_preview,
            max_downloads=max_downloads,
            max_views=max_views,
            expires_at=expires_at
        )
        
        self.db.add(share_record)
        await self.db.commit()
        await self.db.refresh(share_record)
        
        return share_record
    
    async def cleanup_expired_files(self) -> int:
        """
        清理过期文件
        
        Returns:
            清理的文件数量
        """
        try:
            # 查询过期文件
            query = select(AIFileStorage).where(
                and_(
                    AIFileStorage.expires_at <= datetime.utcnow(),
                    AIFileStorage.status != FileStatus.DELETED
                )
            )
            result = await self.db.execute(query)
            expired_files = result.scalars().all()
            
            cleaned_count = 0
            for file_record in expired_files:
                # 删除物理文件
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    file_path.unlink()
                
                # 更新状态
                file_record.status = FileStatus.DELETED
                file_record.deleted_at = datetime.utcnow()
                cleaned_count += 1
            
            await self.db.commit()
            
            logger.info(f"Cleaned up {cleaned_count} expired files")
            return cleaned_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cleanup expired files: {str(e)}")
            return 0
    
    async def get_storage_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Args:
            user_id: 用户ID (可选)
            
        Returns:
            存储统计信息
        """
        conditions = [AIFileStorage.status != FileStatus.DELETED]
        if user_id:
            conditions.append(AIFileStorage.user_id == user_id)
        
        # 总文件数和大小
        query = select(
            func.count(AIFileStorage.id).label('total_files'),
            func.sum(AIFileStorage.file_size).label('total_size')
        ).where(and_(*conditions))
        result = await self.db.execute(query)
        stats = result.first()
        
        # 按分类统计
        category_query = select(
            AIFileStorage.file_category,
            func.count(AIFileStorage.id).label('count'),
            func.sum(AIFileStorage.file_size).label('size')
        ).where(and_(*conditions)).group_by(AIFileStorage.file_category)
        category_result = await self.db.execute(category_query)
        category_stats = {row.file_category: {'count': row.count, 'size': row.size or 0} 
                         for row in category_result}
        
        # 按类型统计
        type_query = select(
            AIFileStorage.file_type,
            func.count(AIFileStorage.id).label('count'),
            func.sum(AIFileStorage.file_size).label('size')
        ).where(and_(*conditions)).group_by(AIFileStorage.file_type)
        type_result = await self.db.execute(type_query)
        type_stats = {row.file_type: {'count': row.count, 'size': row.size or 0} 
                     for row in type_result}
        
        return {
            'total_files': stats.total_files or 0,
            'total_size': stats.total_size or 0,
            'category_stats': category_stats,
            'type_stats': type_stats
        }
    
    # 私有方法
    
    async def _validate_file(self, file: UploadFile, category: FileCategory):
        """验证文件"""
        # 检查文件大小
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # 重置文件指针
        
        max_size = self.MAX_FILE_SIZES.get(category, settings.MAX_FILE_SIZE)
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制 ({max_size / 1024 / 1024:.1f}MB)"
            )
        
        # 检查文件类型
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        allowed_types = self.ALLOWED_MIME_TYPES.get(category, [])
        
        if allowed_types and mime_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {mime_type}"
            )
    
    async def _find_existing_file(self, file_hash: str, user_id: int) -> Optional[AIFileStorage]:
        """查找已存在的文件"""
        query = select(AIFileStorage).where(
            and_(
                AIFileStorage.file_hash == file_hash,
                AIFileStorage.user_id == user_id,
                AIFileStorage.status == FileStatus.ACTIVE
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    def _generate_filename(self, original_filename: str, file_hash: str) -> str:
        """生成存储文件名"""
        ext = Path(original_filename).suffix if original_filename else ''
        return f"{file_hash[:16]}_{uuid.uuid4().hex[:8]}{ext}"
    
    def _get_file_path(self, category: FileCategory, filename: str) -> Path:
        """获取文件存储路径"""
        # 按分类和日期组织文件夹
        date_folder = datetime.now().strftime("%Y/%m")
        return self.storage_root / category.value.lower() / date_folder / filename
    
    def _generate_file_url(self, category: FileCategory, filename: str) -> str:
        """生成文件访问URL"""
        date_folder = datetime.now().strftime("%Y/%m")
        return f"/api/v1/ai/files/{category.value.lower()}/{date_folder}/{filename}"
    
    async def _update_access_stats(self, file_id: int):
        """更新访问统计"""
        query = (
            update(AIFileStorage)
            .where(AIFileStorage.id == file_id)
            .values(
                access_count=AIFileStorage.access_count + 1,
                last_accessed_at=datetime.utcnow()
            )
        )
        await self.db.execute(query)
        await self.db.commit()
    
    async def _update_download_stats(self, file_id: int):
        """更新下载统计"""
        query = (
            update(AIFileStorage)
            .where(AIFileStorage.id == file_id)
            .values(download_count=AIFileStorage.download_count + 1)
        )
        await self.db.execute(query)
        await self.db.commit()
    
    async def _log_file_access(
        self,
        file_id: int,
        user_id: Optional[int],
        action: str,
        success: bool = True,
        error_message: Optional[str] = None,
        bytes_transferred: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        share_id: Optional[int] = None
    ):
        """记录文件访问日志"""
        try:
            log_record = AIFileAccessLog(
                file_id=file_id,
                user_id=user_id,
                share_id=share_id,
                action=action,
                success=success,
                error_message=error_message,
                bytes_transferred=bytes_transferred,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(log_record)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log file access: {str(e)}")