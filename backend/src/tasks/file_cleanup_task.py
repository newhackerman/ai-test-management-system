"""
文件清理定时任务
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..core.database import get_async_session
from ..models.ai_file_storage import AIFileStorage, FileStatus
from ..core.file_storage_config import file_storage_settings
from ..utils.logger import logger


class FileCleanupTask:
    """文件清理任务"""
    
    def __init__(self):
        self.logger = logger
    
    async def cleanup_expired_files(self) -> int:
        """清理过期文件"""
        cleaned_count = 0
        
        try:
            async with get_async_session() as db:
                # 查询过期文件
                now = datetime.utcnow()
                query = select(AIFileStorage).where(
                    and_(
                        AIFileStorage.expires_at <= now,
                        AIFileStorage.status != FileStatus.DELETED
                    )
                )
                
                result = await db.execute(query)
                expired_files = result.scalars().all()
                
                for file_record in expired_files:
                    try:
                        # 删除物理文件
                        file_path = Path(file_record.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            self.logger.info(f"Deleted expired file: {file_path}")
                        
                        # 更新数据库记录
                        file_record.status = FileStatus.DELETED
                        file_record.deleted_at = now
                        
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to delete expired file {file_record.id}: {e}")
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired files: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired files")
        
        return cleaned_count
    
    async def cleanup_temporary_files(self) -> int:
        """清理临时文件"""
        cleaned_count = 0
        
        try:
            async with get_async_session() as db:
                # 查询超过保留期的临时文件
                retention_hours = file_storage_settings.TEMP_FILE_RETENTION_HOURS
                cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)
                
                query = select(AIFileStorage).where(
                    and_(
                        AIFileStorage.is_temporary == True,
                        AIFileStorage.created_at <= cutoff_time,
                        AIFileStorage.status != FileStatus.DELETED
                    )
                )
                
                result = await db.execute(query)
                temp_files = result.scalars().all()
                
                for file_record in temp_files:
                    try:
                        # 删除物理文件
                        file_path = Path(file_record.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            self.logger.info(f"Deleted temporary file: {file_path}")
                        
                        # 更新数据库记录
                        file_record.status = FileStatus.DELETED
                        file_record.deleted_at = datetime.utcnow()
                        
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to delete temporary file {file_record.id}: {e}")
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup temporary files: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} temporary files")
        
        return cleaned_count
    
    async def cleanup_deleted_files(self) -> int:
        """清理已标记删除的文件"""
        cleaned_count = 0
        
        try:
            async with get_async_session() as db:
                # 查询超过保留期的已删除文件
                retention_days = file_storage_settings.DELETED_FILE_RETENTION_DAYS
                cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
                
                query = select(AIFileStorage).where(
                    and_(
                        AIFileStorage.status == FileStatus.DELETED,
                        AIFileStorage.deleted_at <= cutoff_time
                    )
                )
                
                result = await db.execute(query)
                deleted_files = result.scalars().all()
                
                for file_record in deleted_files:
                    try:
                        # 删除物理文件（如果还存在）
                        file_path = Path(file_record.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            self.logger.info(f"Permanently deleted file: {file_path}")
                        
                        # 从数据库中删除记录
                        await db.delete(file_record)
                        
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to permanently delete file {file_record.id}: {e}")
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup deleted files: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Permanently deleted {cleaned_count} files")
        
        return cleaned_count
    
    async def cleanup_orphaned_files(self) -> int:
        """清理孤立文件（数据库中不存在但物理文件存在）"""
        cleaned_count = 0
        
        try:
            storage_root = Path(file_storage_settings.STORAGE_ROOT)
            if not storage_root.exists():
                return 0
            
            async with get_async_session() as db:
                # 获取所有数据库中的文件路径
                query = select(AIFileStorage.file_path).where(
                    AIFileStorage.status != FileStatus.DELETED
                )
                result = await db.execute(query)
                db_file_paths = {row[0] for row in result.fetchall()}
                
                # 遍历存储目录中的所有文件
                for file_path in storage_root.rglob('*'):
                    if file_path.is_file():
                        file_path_str = str(file_path)
                        
                        # 如果文件不在数据库中，则为孤立文件
                        if file_path_str not in db_file_paths:
                            try:
                                # 检查文件是否是最近创建的（避免删除正在上传的文件）
                                file_age = datetime.utcnow().timestamp() - file_path.stat().st_ctime
                                if file_age > 3600:  # 1小时以上的文件
                                    file_path.unlink()
                                    self.logger.info(f"Deleted orphaned file: {file_path}")
                                    cleaned_count += 1
                            except Exception as e:
                                self.logger.error(f"Failed to delete orphaned file {file_path}: {e}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup orphaned files: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} orphaned files")
        
        return cleaned_count
    
    async def cleanup_empty_directories(self) -> int:
        """清理空目录"""
        cleaned_count = 0
        
        try:
            storage_root = Path(file_storage_settings.STORAGE_ROOT)
            if not storage_root.exists():
                return 0
            
            # 从最深层开始清理空目录
            for dir_path in sorted(storage_root.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and dir_path != storage_root:
                    try:
                        # 检查目录是否为空
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            self.logger.info(f"Deleted empty directory: {dir_path}")
                            cleaned_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to delete empty directory {dir_path}: {e}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup empty directories: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} empty directories")
        
        return cleaned_count
    
    async def run_full_cleanup(self) -> dict:
        """运行完整的清理任务"""
        self.logger.info("Starting file cleanup task...")
        
        results = {
            'expired_files': 0,
            'temporary_files': 0,
            'deleted_files': 0,
            'orphaned_files': 0,
            'empty_directories': 0,
            'total_cleaned': 0,
            'start_time': datetime.utcnow(),
            'end_time': None,
            'duration': None
        }
        
        try:
            # 清理过期文件
            results['expired_files'] = await self.cleanup_expired_files()
            
            # 清理临时文件
            results['temporary_files'] = await self.cleanup_temporary_files()
            
            # 清理已删除文件
            results['deleted_files'] = await self.cleanup_deleted_files()
            
            # 清理孤立文件
            results['orphaned_files'] = await self.cleanup_orphaned_files()
            
            # 清理空目录
            results['empty_directories'] = await self.cleanup_empty_directories()
            
            # 计算总数
            results['total_cleaned'] = (
                results['expired_files'] + 
                results['temporary_files'] + 
                results['deleted_files'] + 
                results['orphaned_files'] + 
                results['empty_directories']
            )
            
        except Exception as e:
            self.logger.error(f"File cleanup task failed: {e}")
        
        finally:
            results['end_time'] = datetime.utcnow()
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
            
            self.logger.info(
                f"File cleanup task completed. "
                f"Total cleaned: {results['total_cleaned']} items, "
                f"Duration: {results['duration']:.2f}s"
            )
        
        return results


# 全局清理任务实例
file_cleanup_task = FileCleanupTask()


async def run_scheduled_cleanup():
    """运行定时清理任务"""
    if file_storage_settings.AUTO_CLEANUP_ENABLED:
        return await file_cleanup_task.run_full_cleanup()
    else:
        logger.info("File cleanup is disabled")
        return None