"""
录制处理后台任务

本模块实现录制文件的后台处理任务，包括：
- 录制文件转码和压缩
- 音频转录处理
- 缩略图生成
- 文件存储管理
- 清理过期录制
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..core.database import get_async_session, get_async_session_ctx
from ..models.meeting import MeetingRecording, RecordingStatus
from ..services.recording_service import RecordingService
from ..utils.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RecordingProcessingTask:
    """录制处理后台任务"""
    
    def __init__(self):
        self.logger = logger
        self.redis_client = RedisClient()
    
    async def process_pending_recordings(self) -> int:
        """处理待处理的录制"""
        processed_count = 0
        
        try:
            async with get_async_session_ctx() as db:
                recording_service = RecordingService(db, self.redis_client)
                
                # 查询待处理的录制
                query = select(MeetingRecording).where(
                    MeetingRecording.recording_status == RecordingStatus.PROCESSING
                ).order_by(MeetingRecording.created_at)
                
                result = await db.execute(query)
                recordings = result.scalars().all()
                
                for recording in recordings:
                    try:
                        self.logger.info(f"Processing recording: {recording.id}")
                        await recording_service.process_recording(recording.id)
                        processed_count += 1
                        
                        # 避免同时处理太多录制，添加延迟
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process recording {recording.id}: {e}")
                        
                        # 更新录制状态为失败
                        recording.recording_status = RecordingStatus.FAILED
                        await db.commit()
                
                self.logger.info(f"Processed {processed_count} recordings")
                return processed_count
                
        except Exception as e:
            self.logger.error(f"Error in process_pending_recordings: {e}")
            return 0
    
    async def cleanup_failed_recordings(self) -> int:
        """清理失败的录制"""
        cleaned_count = 0
        
        try:
            async with get_async_session_ctx() as db:
                # 查询超过24小时的失败录制
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                query = select(MeetingRecording).where(
                    and_(
                        MeetingRecording.recording_status == RecordingStatus.FAILED,
                        MeetingRecording.updated_at < cutoff_time
                    )
                )
                
                result = await db.execute(query)
                failed_recordings = result.scalars().all()
                
                for recording in failed_recordings:
                    try:
                        # 删除文件
                        if recording.file_path and Path(recording.file_path).exists():
                            Path(recording.file_path).unlink()
                        
                        # 更新状态为已删除
                        recording.recording_status = RecordingStatus.DELETED
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to cleanup recording {recording.id}: {e}")
                
                await db.commit()
                self.logger.info(f"Cleaned up {cleaned_count} failed recordings")
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Error in cleanup_failed_recordings: {e}")
            return 0
    
    async def cleanup_expired_recordings(self) -> int:
        """清理过期的录制"""
        cleaned_count = 0
        
        try:
            async with get_async_session_ctx() as db:
                # 查询超过保留期的录制（默认90天）
                retention_days = 90  # 可以从配置中读取
                cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
                
                query = select(MeetingRecording).where(
                    and_(
                        MeetingRecording.recording_status == RecordingStatus.COMPLETED,
                        MeetingRecording.created_at < cutoff_time
                    )
                )
                
                result = await db.execute(query)
                expired_recordings = result.scalars().all()
                
                for recording in expired_recordings:
                    try:
                        # 删除文件
                        if recording.file_path and Path(recording.file_path).exists():
                            Path(recording.file_path).unlink()
                        
                        # 删除相关文件
                        base_path = recording.file_path.rsplit('.', 1)[0] if recording.file_path else ""
                        related_files = [
                            f"{base_path}_thumbnail.jpg",
                            f"{base_path}_processed.mp4"
                        ]
                        
                        for file_path in related_files:
                            if Path(file_path).exists():
                                Path(file_path).unlink()
                        
                        # 更新状态为已删除
                        recording.recording_status = RecordingStatus.DELETED
                        cleaned_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to cleanup expired recording {recording.id}: {e}")
                
                await db.commit()
                self.logger.info(f"Cleaned up {cleaned_count} expired recordings")
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Error in cleanup_expired_recordings: {e}")
            return 0
    
    async def monitor_recording_processes(self) -> int:
        """监控录制进程状态"""
        monitored_count = 0
        
        try:
            async with get_async_session_ctx() as db:
                # 查询正在录制的记录
                query = select(MeetingRecording).where(
                    MeetingRecording.recording_status == RecordingStatus.RECORDING
                )
                
                result = await db.execute(query)
                active_recordings = result.scalars().all()
                
                for recording in active_recordings:
                    try:
                        # 检查录制是否超时（超过6小时认为异常）
                        if recording.start_time:
                            duration = datetime.utcnow() - recording.start_time
                            if duration > timedelta(hours=6):
                                self.logger.warning(f"Recording {recording.id} has been running for {duration}")
                                
                                # 标记为失败
                                recording.recording_status = RecordingStatus.FAILED
                                recording.end_time = datetime.utcnow()
                        
                        monitored_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to monitor recording {recording.id}: {e}")
                
                await db.commit()
                return monitored_count
                
        except Exception as e:
            self.logger.error(f"Error in monitor_recording_processes: {e}")
            return 0
    
    async def generate_recording_statistics(self) -> Dict[str, int]:
        """生成录制统计信息"""
        try:
            async with get_async_session_ctx() as db:
                # 统计各状态的录制数量
                stats = {}
                
                for status in RecordingStatus:
                    query = select(func.count(MeetingRecording.id)).where(
                        MeetingRecording.recording_status == status
                    )
                    result = await db.execute(query)
                    count = result.scalar()
                    stats[status.value] = count
                
                # 统计今日新增录制
                today = datetime.utcnow().date()
                query = select(func.count(MeetingRecording.id)).where(
                    func.date(MeetingRecording.created_at) == today
                )
                result = await db.execute(query)
                stats['today_new'] = result.scalar()
                
                # 统计总存储大小
                query = select(func.sum(MeetingRecording.file_size)).where(
                    MeetingRecording.recording_status == RecordingStatus.COMPLETED
                )
                result = await db.execute(query)
                total_size = result.scalar() or 0
                stats['total_storage_bytes'] = total_size
                
                # 缓存统计信息
                await self.redis_client.set(
                    "recording_statistics",
                    json.dumps(stats),
                    ex=3600  # 1小时过期
                )
                
                self.logger.info(f"Generated recording statistics: {stats}")
                return stats
                
        except Exception as e:
            self.logger.error(f"Error in generate_recording_statistics: {e}")
            return {}
    
    async def run_maintenance_tasks(self):
        """运行所有维护任务"""
        self.logger.info("Starting recording maintenance tasks")
        
        try:
            # 处理待处理的录制
            processed = await self.process_pending_recordings()
            
            # 清理失败的录制
            cleaned_failed = await self.cleanup_failed_recordings()
            
            # 清理过期的录制
            cleaned_expired = await self.cleanup_expired_recordings()
            
            # 监控录制进程
            monitored = await self.monitor_recording_processes()
            
            # 生成统计信息
            stats = await self.generate_recording_statistics()
            
            self.logger.info(
                f"Maintenance tasks completed: "
                f"processed={processed}, "
                f"cleaned_failed={cleaned_failed}, "
                f"cleaned_expired={cleaned_expired}, "
                f"monitored={monitored}"
            )
            
        except Exception as e:
            self.logger.error(f"Error in run_maintenance_tasks: {e}")


# 创建任务实例
recording_task = RecordingProcessingTask()


# 定时任务函数
async def process_recordings_task():
    """处理录制的定时任务"""
    await recording_task.process_pending_recordings()


async def cleanup_recordings_task():
    """清理录制的定时任务"""
    await recording_task.cleanup_failed_recordings()
    await recording_task.cleanup_expired_recordings()


async def monitor_recordings_task():
    """监控录制的定时任务"""
    await recording_task.monitor_recording_processes()


async def recording_maintenance_task():
    """录制维护任务"""
    await recording_task.run_maintenance_tasks()


# 导出任务函数
__all__ = [
    'RecordingProcessingTask',
    'recording_task',
    'process_recordings_task',
    'cleanup_recordings_task',
    'monitor_recordings_task',
    'recording_maintenance_task'
]